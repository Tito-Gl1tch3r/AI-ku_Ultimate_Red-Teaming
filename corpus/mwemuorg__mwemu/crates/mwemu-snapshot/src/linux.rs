use std::cell::RefCell;
use std::collections::BTreeMap;
use std::fs;
use std::io::IoSliceMut;
use std::process::Command;

use ahash::AHashMap;
use nix::sys::ptrace;
use nix::sys::uio::{RemoteIoVec, process_vm_readv};
use nix::sys::wait::waitpid;
use nix::unistd::Pid;
use slab::Slab;

use libmwemu::arch::{Arch, OperatingSystem};
use libmwemu::emu::Emu;
use libmwemu::flags::Flags;
use libmwemu::maps::Maps;
use libmwemu::maps::mem64::{Mem64, Permission};
use libmwemu::maps::tlb::TLB;
use libmwemu::regs64::Regs64;
use libmwemu::serialization::Serialization;
use libmwemu::serialization::emu::SerializableEmu;
use libmwemu::serialization::maps::SerializableMaps;

struct MapRegion {
    start: u64,
    end: u64,
    perms: Permission,
    path: String,
}

/// Parse `/proc/<pid>/maps`. Stable text format, unchanged for decades — a
/// small parser here is more robust than depending on a generic crate that
/// tries to cover every historical quirk (see: the procfs_core failure this
/// tool exists to route around).
fn parse_proc_maps(pid: i32) -> std::io::Result<Vec<MapRegion>> {
    let content = fs::read_to_string(format!("/proc/{pid}/maps"))?;
    let mut out = Vec::new();
    for line in content.lines() {
        let mut parts = line.splitn(6, ' ');
        let Some(range) = parts.next() else { continue };
        let Some(perms) = parts.next() else { continue };
        let Some((start_s, end_s)) = range.split_once('-') else {
            continue;
        };
        let (Ok(start), Ok(end)) = (
            u64::from_str_radix(start_s, 16),
            u64::from_str_radix(end_s, 16),
        ) else {
            continue;
        };
        let (r, w, x) = (
            perms.contains('r'),
            perms.contains('w'),
            perms.contains('x'),
        );
        let permission = match (r, w, x) {
            (false, false, false) => Permission::NONE,
            (true, false, false) => Permission::READ,
            (true, true, false) => Permission::READ_WRITE,
            (false, false, true) => Permission::EXECUTE,
            (true, false, true) => Permission::READ_EXECUTE,
            (true, true, true) => Permission::READ_WRITE_EXECUTE,
            _ => Permission::READ_WRITE_EXECUTE,
        };
        let path = parts.nth(3).unwrap_or("").trim().to_string();
        out.push(MapRegion {
            start,
            end,
            perms: permission,
            path,
        });
    }
    Ok(out)
}

/// `[vvar]`/`[vvar_vclock]`/`[vdso]`/`[vsyscall]` are kernel-injected special
/// mappings (VM_PFNMAP-style, no backing `struct page`) that `process_vm_readv`
/// can't reach cross-process (EFAULT). A same-kernel substitute is tempting
/// since their *content* would be identical to our own copy -- but reading
/// them safely turned out to be a dead end worth recording: `/proc/self/mem`
/// can't reach them either (same `get_user_pages` limitation, even for our
/// own copy), and a raw pointer load crashed this tool with SIGBUS on `[vvar]`
/// itself despite `/proc/pid/maps` reporting it `r--p` -- the reported
/// permission bit does not reliably predict whether a plain CPU load is safe
/// on these pages. Repeated live SIGBUS crashes on the analyst's own machine
/// is a worse outcome than an absent region, so these are left unmapped, the
/// same as any other unreadable region below. If `[vvar]`/`[vdso]` support is
/// wanted later, the safe place for it is the *replay* side inside mwemu
/// itself (a sandboxed, catchable context) synthesizing its own page when it
/// recognizes the access pattern -- not a live host-side read here.

/// Bulk-copy `len` bytes at `start` out of the target's address space in one
/// syscall (`process_vm_readv`), instead of `PTRACE_PEEKDATA` word by word.
fn read_remote_memory(pid: i32, start: u64, len: usize) -> Option<Vec<u8>> {
    let mut buf = vec![0u8; len];
    let mut local = [IoSliceMut::new(&mut buf)];
    let remote = [RemoteIoVec {
        base: start as usize,
        len,
    }];
    match process_vm_readv(Pid::from_raw(pid), &mut local, &remote) {
        Ok(n) if n == len => Some(buf),
        Ok(n) => {
            buf.truncate(n);
            Some(buf)
        }
        Err(e) => {
            eprintln!("  DIAG: process_vm_readv failed for 0x{start:x} len={len}: {e}");
            None
        }
    }
}

/// Ptrace-attach to an already-running `pid`, wait for the stop, capture
/// registers + the full readable memory map, detach (resuming it), and
/// return a real, ready-to-run `Emu` at the exact point of capture.
///
/// Needs ptrace permission: same-process-tree child, or CAP_SYS_PTRACE/root,
/// or the target's own `prctl(PR_SET_PTRACER, ..)` — see Yama ptrace_scope.
fn attach_and_capture(pid: i32) -> Result<Emu, String> {
    let target = Pid::from_raw(pid);

    ptrace::attach(target).map_err(|e| {
        format!(
            "ptrace attach failed: {e} — if this is an unrelated process, check \
             /proc/sys/kernel/yama/ptrace_scope (1 = only direct children unless \
             you have CAP_SYS_PTRACE, run as root, or the target called \
             prctl(PR_SET_PTRACER, ..))"
        )
    })?;
    waitpid(target, None).map_err(|e| format!("waitpid failed: {e}"))?;

    let regs = ptrace::getregs(target).map_err(|e| {
        let _ = ptrace::detach(target, None);
        format!("PTRACE_GETREGS failed: {e}")
    })?;
    // TODO: also capture FPU/SSE/AVX state (PTRACE_GETFPREGS / PTRACE_GETREGSET
    // with NT_X86_XSTATE) and feed it into the Emu's FPU. Confirmed missing:
    // `mwemu-snapshot spawn sleep 300` resumes and runs the real ld.so/libc
    // startup faithfully (real syscalls, real addresses) all the way into
    // sleep's own main(), but then GNU sleep's xstrtod (fractional-seconds
    // parser, uses SSE) rejects "300" as an invalid interval -- because the
    // emulator starts with a zeroed FPU instead of the process's real one.

    let regions = match parse_proc_maps(pid) {
        Ok(r) => r,
        Err(e) => {
            let _ = ptrace::detach(target, None);
            return Err(format!("failed to read /proc/{pid}/maps: {e}"));
        }
    };

    let mut mem_slab: Slab<Mem64> = Slab::new();
    let mut maps: BTreeMap<u64, usize> = BTreeMap::new();
    let mut name_map: AHashMap<String, usize> = AHashMap::new();
    let mut skipped = 0u32;

    for r in &regions {
        if r.perms.bits() == Permission::NONE.bits() {
            continue;
        }
        let len = (r.end - r.start) as usize;
        let Some(data) = read_remote_memory(pid, r.start, len) else {
            eprintln!(
                "  DIAG: skipping 0x{:x}-0x{:x} \"{}\"",
                r.start, r.end, r.path
            );
            skipped += 1;
            continue;
        };
        let name = if r.path.is_empty() {
            format!("mem_0x{:016x}", r.start)
        } else {
            r.path.clone()
        };
        let mem_entry = Mem64::new(
            name.clone(),
            r.start,
            r.start + data.len() as u64,
            data,
            r.perms,
        );
        let slab_key = mem_slab.insert(mem_entry);
        maps.insert(r.start, slab_key);
        if !r.path.is_empty() {
            name_map.entry(name).or_insert(slab_key);
        }
    }
    eprintln!(
        "mwemu-snapshot: {} region(s) captured, {} skipped (unreadable)",
        maps.len(),
        skipped
    );

    // Always detach, even if something above the memory copy went wrong, so
    // a failed snapshot never leaves the target stopped (the exact bug that
    // bit minidump-writer's error path during development of this tool).
    if let Err(e) = ptrace::detach(target, None) {
        eprintln!("warning: ptrace detach failed: {e} (target may still be stopped)");
    }

    let tlb = RefCell::new(TLB::new());
    let real_maps = Maps::new(mem_slab, maps, name_map, true, false, tlb);
    let serializable_maps = SerializableMaps::new(real_maps);

    let mut mwemu_regs = Regs64::default();
    mwemu_regs.rax = regs.rax;
    mwemu_regs.rbx = regs.rbx;
    mwemu_regs.rcx = regs.rcx;
    mwemu_regs.rdx = regs.rdx;
    mwemu_regs.rsi = regs.rsi;
    mwemu_regs.rdi = regs.rdi;
    mwemu_regs.rbp = regs.rbp;
    mwemu_regs.rsp = regs.rsp;
    mwemu_regs.rip = regs.rip;
    mwemu_regs.r8 = regs.r8;
    mwemu_regs.r9 = regs.r9;
    mwemu_regs.r10 = regs.r10;
    mwemu_regs.r11 = regs.r11;
    mwemu_regs.r12 = regs.r12;
    mwemu_regs.r13 = regs.r13;
    mwemu_regs.r14 = regs.r14;
    mwemu_regs.r15 = regs.r15;
    // Linux path in libmwemu's `fs:[disp]` decoding treats `regs.fs` as the
    // real fs_base linear address (arch_prctl/ARCH_SET_FS), not a segment
    // selector like on Windows — and `user_regs_struct` already carries the
    // real fs_base/gs_base, no extra ARCH_PRCTL round-trip needed.
    mwemu_regs.fs = regs.fs_base;
    mwemu_regs.gs = regs.gs_base;

    let mut flags = Flags::new();
    flags.load(regs.eflags as u32);

    let mut serializable_emu = SerializableEmu::default_for_arch(Arch::X86_64);
    serializable_emu.set_maps(serializable_maps);
    serializable_emu.set_regs(mwemu_regs);
    serializable_emu.set_flags(flags);
    serializable_emu.os = OperatingSystem::Linux;
    serializable_emu.filename = format!("live-pid-{pid}");

    Ok(serializable_emu.into())
}

fn usage() -> ! {
    eprintln!(
        "usage:\n  \
         mwemu-snapshot attach <pid> [-o out.mwemu]\n  \
         mwemu-snapshot spawn <command> [args...] [-o out.mwemu]"
    );
    std::process::exit(1);
}

pub fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        usage();
    }

    // `-o out.mwemu` may appear anywhere after the mode-specific args; pull
    // it out first so `spawn`'s trailing argv doesn't have to worry about it.
    let mut args = args;
    let mut out_path = "snapshot.mwemu".to_string();
    if let Some(pos) = args.iter().position(|a| a == "-o") {
        if pos + 1 >= args.len() {
            usage();
        }
        out_path = args.remove(pos + 1);
        args.remove(pos);
    }

    let emu = match args[0].as_str() {
        "attach" => {
            let Some(pid_s) = args.get(1) else { usage() };
            let pid: i32 = pid_s.parse().unwrap_or_else(|_| usage());
            attach_and_capture(pid)
        }
        "spawn" => {
            let Some(cmd) = args.get(1) else { usage() };
            let mut child = Command::new(cmd)
                .args(&args[2..])
                .spawn()
                .unwrap_or_else(|e| {
                    eprintln!("failed to spawn {cmd}: {e}");
                    std::process::exit(1);
                });
            let pid = child.id() as i32;
            eprintln!("mwemu-snapshot: spawned {cmd} as pid {pid}, attaching...");
            let result = attach_and_capture(pid);
            let _ = child.kill();
            let _ = child.wait();
            result
        }
        _ => usage(),
    };

    match emu {
        Ok(emu) => {
            eprintln!(
                "mwemu-snapshot: captured rip=0x{:x} rsp=0x{:x}",
                emu.regs().rip,
                emu.regs().rsp
            );
            Serialization::dump(&emu, &out_path);
            eprintln!(
                "mwemu-snapshot: saved to {out_path} (reopen with: mwemu -f <any same-arch file> -d {out_path} -v)"
            );
        }
        Err(e) => {
            eprintln!("mwemu-snapshot: {e}");
            std::process::exit(1);
        }
    }
}
