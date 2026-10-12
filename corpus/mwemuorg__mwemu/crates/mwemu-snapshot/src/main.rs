//! mwemu-snapshot — clone a live Linux process into mwemu.
//!
//! Ptrace-attaches (or spawns-then-attaches) a target, copies its registers
//! and its entire readable memory map, and hands libmwemu a real `Emu` at
//! exactly the point it was captured — then saves it in mwemu's own native
//! snapshot format so it can be reopened later with `mwemu -f <file>` or
//! `Serialization::load`.
//!
//! All the ptrace/unsafe work lives here, in this standalone binary — never
//! inside libmwemu itself, which stays free of it.
//!
//! Usage:
//!   mwemu-snapshot attach <pid> [-o out.mwemu]
//!   mwemu-snapshot spawn <command> [args...] [-o out.mwemu]
//!
//! `attach` needs ptrace permission on an unrelated PID: Yama's default
//! ptrace_scope=1 only allows a direct child unless you have CAP_SYS_PTRACE,
//! run as root, or the target opted in via prctl(PR_SET_PTRACER). `spawn`
//! sidesteps that entirely by making the target our own child.

#[cfg(target_os = "linux")]
mod linux;

#[cfg(target_os = "linux")]
fn main() {
    linux::main();
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("mwemu-snapshot: Linux-only (ptrace-based live process cloning).");
    std::process::exit(1);
}
