#!/usr/bin/env python3
# K!ll Fl!utter - Flutter SSL Pinning Bypass Tool
# By: f3rb
# Supports: Android (APK) + iOS (IPA)
# Architectures: arm64-v8a, x86_64, armeabi-v7a (Android) + arm64 (iOS)
# For authorized penetration testing only

import struct, re, sys, os, zipfile, subprocess, argparse, plistlib


# ─────────────────────────────────────────────
#  BOX HELPERS (keeps all boxes perfectly aligned)
# ─────────────────────────────────────────────

BOX_WIDTH = 54  # visible characters between the ║ borders

C_CYAN   = "\033[96m"
C_YELLOW = "\033[93m"
C_GREEN  = "\033[92m"
C_RED    = "\033[91m"
C_GREY   = "\033[90m"
C_PURPLE = "\033[95m"
C_RESET  = "\033[0m"


def box_top():
    return C_CYAN + "╔" + "═" * BOX_WIDTH + "╗" + C_RESET


def box_bottom():
    return C_CYAN + "╚" + "═" * BOX_WIDTH + "╝" + C_RESET


def box_line(text, color=""):
    """text is the raw visible text (no ANSI). Pads to BOX_WIDTH and adds borders."""
    padded = text.ljust(BOX_WIDTH)
    return f"{C_CYAN}║{C_RESET}{color}{padded}{C_RESET}{C_CYAN}║{C_RESET}"


# ─────────────────────────────────────────────
#  BANNER & HELP
# ─────────────────────────────────────────────

def print_banner():
    print(C_CYAN + """
██╗  ██╗██╗██╗     ██╗     
██║ ██╔╝██║██║     ██║     
█████╔╝ ██║██║     ██║     
██╔═██╗ ██║██║     ██║     
██║  ██╗██║███████╗███████╗
╚═╝  ╚═╝╚═╝╚══════╝╚══════╝""" + C_PURPLE + """
███████╗██╗     ██╗   ██╗████████╗████████╗███████╗██████╗ 
██╔════╝██║     ██║   ██║╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗
█████╗  ██║     ██║   ██║   ██║      ██║   █████╗  ██████╔╝
██╔══╝  ██║     ██║   ██║   ██║      ██║   ██╔══╝  ██╔══██╗
██║     ███████╗╚██████╔╝   ██║      ██║   ███████╗██║  ██║
╚═╝     ╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝""" + C_RESET)

    print(box_top())
    print(box_line("  K!ll Fl!utter  —  Flutter SSL Pinning Bypass", C_YELLOW))
    print(box_line("  By: f3rb                              v3.0.0", C_GREEN))
    print(box_line("  Android (APK) + iOS (IPA) Support", C_PURPLE))
    print(box_line("  Multi-arch: arm64 / x86_64 / armeabi-v7a", C_PURPLE))
    print(box_line("  For authorized penetration testing only", C_PURPLE))
    print(box_bottom())
    print("")


def print_help():
    print_banner()
    print("""
\033[93mUSAGE:\033[0m
  python3 kill_flutter.py <path_to_apk_or_ipa> [options]

\033[93mOPTIONS:\033[0m
  \033[92m-h, --help\033[0m          Show this help message
  \033[92m-i, --ip\033[0m            Your machine IP (for proxy/iptables commands)
  \033[92m-p, --port\033[0m          Burp Suite port (default: 8080)
  \033[92m-o, --output\033[0m        Output directory for generated files
  \033[92m--arch\033[0m              Android ABI to target: arm64-v8a | x86_64 |
                      armeabi-v7a | x86  (auto-detected if omitted;
                      defaults to arm64-v8a when present)
  \033[92m--list-arch\033[0m         List the ABIs bundled in the APK and exit
  \033[92m--platform\033[0m          Force platform: android or ios
  \033[92m--device-ip\033[0m         iOS device IP (for SSH iptables)

\033[93mEXAMPLES:\033[0m
  \033[90m# Android APK (defaults to arm64-v8a)\033[0m
  python3 kill_flutter.py app.apk -i 192.168.1.10 -p 8080

  \033[90m# Target an x86_64 emulator build\033[0m
  python3 kill_flutter.py app.apk --arch x86_64 -i 192.168.1.10

  \033[90m# Target a 32-bit device build\033[0m
  python3 kill_flutter.py app.apk --arch armeabi-v7a -i 192.168.1.10

  \033[90m# Just see what's inside\033[0m
  python3 kill_flutter.py app.apk --list-arch

  \033[90m# iOS IPA\033[0m
  python3 kill_flutter.py app.ipa -i 192.168.1.10 -p 8080

\033[93mWORKFLOW:\033[0m
  \033[96m1.\033[0m Auto-detects platform from file extension
  \033[96m2.\033[0m Extracts the chosen ABI's libflutter.so (or Flutter framework)
  \033[96m3.\033[0m Scans for ssl_client/ssl_server string anchors
  \033[96m4.\033[0m Detects arch from the ELF/Mach-O header and routes to the
     matching offset engine (ARM64 ADRP+ADD, x86_64 RIP-relative LEA,
     or ARMv7 MOVW/MOVT+ADD-PC / literal pool)
  \033[96m5.\033[0m Walks back to the function prologue to get the hook offset
  \033[96m6.\033[0m Generates a ready-to-use Frida script + copy-paste commands

\033[93mREQUIREMENTS:\033[0m
  \033[92m- Python 3\033[0m
  \033[92m- Frida\033[0m             pip install frida-tools
  \033[92m- capstone\033[0m          pip install capstone   (only for x86_64 / armeabi-v7a)
  \033[92m- aapt\033[0m              Android SDK build tools (Android only)
  \033[92m- Rooted Android / Jailbroken iOS device\033[0m
  \033[92m- Burp Suite\033[0m        invisible proxy on all interfaces

\033[93mNOTE ON ARCHITECTURES:\033[0m
  Android maps only the ABI matching the device/emulator at runtime, so the
  offset must come from the SAME ABI you will actually run Frida against:
    - real phones          -> arm64-v8a (a few old/budget ones -> armeabi-v7a)
    - Intel/AMD emulators  -> x86_64 (older images -> x86)
  The arm64 engine is dependency-free. x86_64 and armeabi-v7a require capstone.

\033[93mANDROID — REVERT IPTABLES:\033[0m
  adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination <IP>:8080"
  adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination <IP>:8080"
  \033[90m# Or simply: adb reboot\033[0m

\033[93miOS — REVERT IPTABLES (via SSH):\033[0m
  ssh root@<device-ip> "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination <IP>:8080"
  ssh root@<device-ip> "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination <IP>:8080"
  \033[90m# Or simply reboot the device\033[0m
""")


# ─────────────────────────────────────────────
#  PLATFORM DETECTION
# ─────────────────────────────────────────────

def detect_platform(file_path, forced=None):
    if forced:
        return forced.lower()
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.apk':
        return 'android'
    elif ext == '.ipa':
        return 'ios'
    else:
        print("\033[93m[!] Cannot detect platform from extension. Use --platform android or --platform ios\033[0m")
        sys.exit(1)


# ─────────────────────────────────────────────
#  ANDROID — PACKAGE NAME
# ─────────────────────────────────────────────

def get_package_name_android(apk_path):
    try:
        result = subprocess.run(
            ['aapt', 'dump', 'badging', apk_path],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("package:"):
                for part in line.split():
                    if part.startswith("name="):
                        return part.split("'")[1]
    except Exception as e:
        print(f"\033[93m[!] aapt failed: {e}\033[0m")
    return None


# ─────────────────────────────────────────────
#  iOS — BUNDLE ID
# ─────────────────────────────────────────────

def get_bundle_id_ios(ipa_path):
    try:
        with zipfile.ZipFile(ipa_path, 'r') as z:
            # Find Info.plist
            for name in z.namelist():
                if re.match(r'Payload/[^/]+\.app/Info\.plist$', name):
                    with z.open(name) as f:
                        content = f.read()

                    try:
                        plist_data = plistlib.loads(content)
                        if 'CFBundleIdentifier' in plist_data:
                            return plist_data['CFBundleIdentifier'].strip()
                    except Exception as parse_e:
                        print(f"\033[93m[!] Could not parse Info.plist data: {parse_e}\033[0m")
    except Exception as e:
        print(f"\033[93m[!] Could not read Info.plist from zip: {e}\033[0m")
    return None


# ─────────────────────────────────────────────
#  ANDROID — EXTRACT libflutter.so (arch-aware)
# ─────────────────────────────────────────────

# ABIs we know how to analyse, best -> worst practical value
KNOWN_ABIS = ['arm64-v8a', 'armeabi-v7a', 'x86_64', 'x86']


def list_flutter_arches(apk_path):
    """Return {abi: zip_entry_name} for every libflutter.so found in the APK."""
    found = {}
    with zipfile.ZipFile(apk_path, 'r') as z:
        for name in z.namelist():
            m = re.search(r'lib/([^/]+)/libflutter\.so$', name)
            if m:
                found[m.group(1)] = name
    return found


def extract_flutter_android(apk_path, out_dir, arch=None):
    """Extract the requested (or auto-selected) ABI's libflutter.so.
    Returns (so_path, abi) or (None, None)."""
    arches = list_flutter_arches(apk_path)
    if not arches:
        print("\033[91m[-] No libflutter.so found in any lib/<abi>/ — is this a Flutter APK?\033[0m")
        return None, None

    available = ', '.join(sorted(arches))
    print(f"\033[96m[*]\033[0m ABIs present in APK: \033[93m{available}\033[0m")

    if arch is None:
        # Prefer arm64-v8a (real devices), then fall back to the first known ABI
        for cand in KNOWN_ABIS:
            if cand in arches:
                arch = cand
                break
        if arch is None:
            arch = sorted(arches)[0]
        print(f"\033[96m[*]\033[0m No --arch given, auto-selected: \033[93m{arch}\033[0m")

    if arch not in arches:
        print(f"\033[91m[-] ABI '{arch}' not bundled in this APK.\033[0m")
        print(f"\033[93m[!] Available: {available}  (pass one with --arch)\033[0m")
        return None, None

    so_path = os.path.join(out_dir, f'libflutter_{arch}.so')
    print(f"\033[96m[*]\033[0m Extracting {arch}/libflutter.so ...")
    with zipfile.ZipFile(apk_path, 'r') as z:
        with z.open(arches[arch]) as src, open(so_path, 'wb') as dst:
            dst.write(src.read())
    print(f"\033[92m[+]\033[0m Found: {arches[arch]}")
    print(f"\033[92m[+]\033[0m Saved: {so_path}")
    return so_path, arch


# ─────────────────────────────────────────────
#  iOS — EXTRACT Flutter framework binary
# ─────────────────────────────────────────────

def extract_flutter_ios(ipa_path, out_dir):
    fw_path = os.path.join(out_dir, 'Flutter')
    print(f"\033[96m[*]\033[0m Extracting Flutter framework from IPA...")
    with zipfile.ZipFile(ipa_path, 'r') as z:
        for name in z.namelist():
            if re.search(r'Payload/[^/]+\.app/Frameworks/Flutter\.framework/Flutter$', name):
                print(f"\033[92m[+]\033[0m Found: {name}")
                with z.open(name) as src, open(fw_path, 'wb') as dst:
                    dst.write(src.read())
                return fw_path
    print("\033[91m[-] Flutter.framework/Flutter not found — is this a Flutter IPA?\033[0m")
    return None


# ─────────────────────────────────────────────
#  ELF SEGMENT PARSERS
# ─────────────────────────────────────────────

def parse_elf64_segments(data):
    """ELF64 (arm64-v8a, x86_64).
    Returns (base_vaddr, code_foff, code_vaddr, code_filesz)."""
    if data[:4] != b'\x7fELF':
        return None, None, None, None

    e_phoff     = struct.unpack_from('<Q', data, 0x20)[0]
    e_phentsize = struct.unpack_from('<H', data, 0x36)[0]
    e_phnum     = struct.unpack_from('<H', data, 0x38)[0]

    base_vaddr = None
    code_foff = code_vaddr = code_filesz = None

    for i in range(e_phnum):
        ph      = data[e_phoff + i*e_phentsize : e_phoff + (i+1)*e_phentsize]
        p_type  = struct.unpack_from('<I', ph, 0x00)[0]
        p_flags = struct.unpack_from('<I', ph, 0x04)[0]
        p_offset = struct.unpack_from('<Q', ph, 0x08)[0]
        p_vaddr  = struct.unpack_from('<Q', ph, 0x10)[0]

        # PT_LOAD
        if p_type == 1:
            if p_offset == 0 and base_vaddr is None:
                base_vaddr = p_vaddr
            # PF_X
            if (p_flags & 1):
                code_foff   = p_offset
                code_vaddr  = p_vaddr
                code_filesz = struct.unpack_from('<Q', ph, 0x20)[0]
                print(f"\033[96m[*]\033[0m ELF64 code segment: file={hex(code_foff)} vaddr={hex(code_vaddr)} size={hex(code_filesz)}")

    if base_vaddr is None:
        base_vaddr = 0

    return base_vaddr, code_foff, code_vaddr, code_filesz


def parse_elf32_segments(data):
    """ELF32 (armeabi-v7a, x86).
    Program header layout differs from ELF64 (p_flags is at +0x18).
    Returns (base_vaddr, code_foff, code_vaddr, code_filesz)."""
    if data[:4] != b'\x7fELF':
        return None, None, None, None

    e_phoff     = struct.unpack_from('<I', data, 0x1C)[0]
    e_phentsize = struct.unpack_from('<H', data, 0x2A)[0]
    e_phnum     = struct.unpack_from('<H', data, 0x2C)[0]

    base_vaddr = None
    code_foff = code_vaddr = code_filesz = None

    for i in range(e_phnum):
        ph       = data[e_phoff + i*e_phentsize : e_phoff + (i+1)*e_phentsize]
        p_type   = struct.unpack_from('<I', ph, 0x00)[0]
        p_offset = struct.unpack_from('<I', ph, 0x04)[0]
        p_vaddr  = struct.unpack_from('<I', ph, 0x08)[0]
        p_filesz = struct.unpack_from('<I', ph, 0x10)[0]
        p_flags  = struct.unpack_from('<I', ph, 0x18)[0]   # ELF32: flags at +0x18

        # PT_LOAD
        if p_type == 1:
            if p_offset == 0 and base_vaddr is None:
                base_vaddr = p_vaddr
            # PF_X
            if (p_flags & 1):
                code_foff   = p_offset
                code_vaddr  = p_vaddr
                code_filesz = p_filesz
                print(f"\033[96m[*]\033[0m ELF32 code segment: file={hex(code_foff)} vaddr={hex(code_vaddr)} size={hex(code_filesz)}")

    if base_vaddr is None:
        base_vaddr = 0

    return base_vaddr, code_foff, code_vaddr, code_filesz


# ─────────────────────────────────────────────
#  MACH-O SEGMENT PARSER (iOS ARM64)
# ─────────────────────────────────────────────

def parse_macho_segments(data):
    """Returns (base_vaddr, code_foff, code_vaddr, code_filesz, data) for __TEXT executable segment.
    Always returns a 5-tuple; data may be a sliced arm64 view of a fat binary."""

    MH_MAGIC_64    = 0xFEEDFACF  # 64-bit little-endian
    FAT_MAGIC      = 0xCAFEBABE  # Fat binary (big-endian)
    LC_SEGMENT_64  = 0x19

    magic = struct.unpack_from('<I', data, 0)[0]

    # Handle fat binary — extract arm64 slice
    if struct.unpack_from('>I', data, 0)[0] == FAT_MAGIC:
        print(f"\033[96m[*]\033[0m Detected fat binary — extracting arm64 slice")
        nfat = struct.unpack_from('>I', data, 4)[0]
        for i in range(nfat):
            off = 8 + i * 20
            cputype      = struct.unpack_from('>I', data, off)[0]
            slice_offset = struct.unpack_from('>I', data, off + 8)[0]
            slice_size   = struct.unpack_from('>I', data, off + 12)[0]
            # ARM64 cputype = 0x0100000C
            if cputype == 0x0100000C:
                print(f"\033[92m[+]\033[0m arm64 slice found at offset {hex(slice_offset)}")
                data = data[slice_offset:slice_offset + slice_size]
                magic = struct.unpack_from('<I', data, 0)[0]
                break

    if magic != MH_MAGIC_64:
        print(f"\033[91m[-] Not a valid Mach-O 64-bit binary (magic={hex(magic)})\033[0m")
        return None, None, None, None, data

    ncmds    = struct.unpack_from('<I', data, 16)[0]
    cmd_off  = 32  # sizeof mach_header_64

    base_vaddr = None
    code_foff = code_vaddr = code_filesz = None

    for _ in range(ncmds):
        cmd     = struct.unpack_from('<I', data, cmd_off)[0]
        cmdsize = struct.unpack_from('<I', data, cmd_off + 4)[0]

        if cmd == LC_SEGMENT_64:
            # segname is 16 bytes at offset +8
            segname  = data[cmd_off + 8 : cmd_off + 24].rstrip(b'\x00').decode('utf-8', errors='ignore')
            vmaddr   = struct.unpack_from('<Q', data, cmd_off + 24)[0]
            vmsize   = struct.unpack_from('<Q', data, cmd_off + 32)[0]
            fileoff  = struct.unpack_from('<Q', data, cmd_off + 40)[0]
            filesize = struct.unpack_from('<Q', data, cmd_off + 48)[0]
            maxprot  = struct.unpack_from('<I', data, cmd_off + 56)[0]

            if fileoff == 0 and base_vaddr is None:
                base_vaddr = vmaddr

            # __TEXT segment with execute permission (VM_PROT_EXECUTE = 4)
            if segname == '__TEXT' and (maxprot & 4):
                code_foff   = fileoff
                code_vaddr  = vmaddr
                code_filesz = filesize
                print(f"\033[96m[*]\033[0m Mach-O __TEXT segment: file={hex(fileoff)} vaddr={hex(vmaddr)} size={hex(filesize)}")

        cmd_off += cmdsize

    if base_vaddr is None:
        base_vaddr = 0

    return base_vaddr, code_foff, code_vaddr, code_filesz, data  # return possibly-sliced data


# ─────────────────────────────────────────────
#  ARCH DETECTION (from the extracted binary itself)
# ─────────────────────────────────────────────

# EI_CLASS, e_machine -> engine key
EM_AARCH64 = 0xB7   # 183
EM_X86_64  = 0x3E   # 62
EM_ARM     = 0x28   # 40
EM_386     = 0x03   # 3


def detect_binary_arch(data):
    """Return one of: 'arm64', 'x86_64', 'arm', 'x86', or None (from ELF header)."""
    if data[:4] != b'\x7fELF':
        return None
    ei_class = data[4]          # 1=ELF32, 2=ELF64
    e_machine = struct.unpack_from('<H', data, 0x12)[0]
    if ei_class == 2 and e_machine == EM_AARCH64:
        return 'arm64'
    if ei_class == 2 and e_machine == EM_X86_64:
        return 'x86_64'
    if ei_class == 1 and e_machine == EM_ARM:
        return 'arm'
    if ei_class == 1 and e_machine == EM_386:
        return 'x86'
    return None


def _load_capstone():
    try:
        import capstone  # noqa
        return capstone
    except ImportError:
        print("\033[91m[-] This architecture needs capstone.\033[0m")
        print("\033[93m[!] Install it with:  pip install capstone\033[0m")
        return None


# ─────────────────────────────────────────────
#  ENGINE — ARM64 (ELF & Mach-O). Dependency-free.
#  ADRP+ADD reference finding + prologue walk-back.
# ─────────────────────────────────────────────

def scan_arm64(data, base_vaddr, code_foff, code_vaddr, code_filesz, ssl_client, ssl_server):
    def foff_to_vaddr(fo):
        return fo - code_foff + code_vaddr

    def foff_to_rva(fo):
        return (fo - code_foff + code_vaddr) - base_vaddr

    def find_refs(target_va):
        lo12 = target_va & 0xfff
        refs = []
        for fi in range(code_foff, code_foff + code_filesz - 4, 4):
            instr = struct.unpack_from('<I', data, fi)[0]
            # ADD (immediate, 64-bit) with matching lo12
            if (instr & 0xffc00000) == 0x91000000 and ((instr >> 10) & 0xfff) == lo12:
                if fi >= 4:
                    adrp = struct.unpack_from('<I', data, fi - 4)[0]
                    if (adrp & 0x9f000000) == 0x90000000:  # ADRP
                        immlo = (adrp >> 29) & 0x3
                        immhi = (adrp >> 5) & 0x7ffff
                        imm = ((immhi << 2) | immlo) << 12
                        if imm & (1 << 32):
                            imm -= (1 << 33)
                        pc_va = foff_to_vaddr(fi - 4)
                        if (pc_va & ~0xfff) + imm == (target_va & ~0xfff):
                            refs.append(fi)
        return refs

    print(f"\033[96m[*]\033[0m [arm64] Scanning ADRP+ADD refs... (may take a moment)")
    sc_refs = find_refs(ssl_client[0])
    ss_refs = find_refs(ssl_server[0])
    print(f"\033[96m[*]\033[0m ssl_client code refs: {[hex(x) for x in sc_refs]}")
    print(f"\033[96m[*]\033[0m ssl_server code refs: {[hex(x) for x in ss_refs]}")

    for a in sc_refs:
        for b in ss_refs:
            if abs(a - b) < 0x800:
                start = min(a, b)
                for i in range(start, max(code_foff, start - 0x300), -4):
                    instr = struct.unpack_from('<I', data, i)[0]
                    # SUB SP,SP,#imm  or  STP X29,X30,[SP,...]
                    if (instr & 0xff8003ff) == 0xd10003ff or (instr & 0xffe07fff) == 0xa9007bfd:
                        rva = foff_to_rva(i)
                        print(f"\033[92m[+]\033[0m [arm64] SSL verify offset (RVA): \033[93m{hex(rva)}\033[0m")
                        print(f"\033[92m[+]\033[0m First bytes: {data[i:i+16].hex(' ')}")
                        return rva

    print("\033[91m[-] [arm64] Could not find SSL verify function\033[0m")
    return None


# ─────────────────────────────────────────────
#  ENGINE — x86_64 (ELF). Needs capstone.
#  RIP-relative LEA reference finding + function-start detection.
# ─────────────────────────────────────────────

def scan_x86_64(data, base_vaddr, code_foff, code_vaddr, code_filesz, ssl_client, ssl_server):
    cs = _load_capstone()
    if cs is None:
        return None
    from capstone.x86 import X86_OP_MEM

    md = cs.Cs(cs.CS_ARCH_X86, cs.CS_MODE_64)
    md.detail = True

    code = data[code_foff:code_foff + code_filesz]

    print(f"\033[96m[*]\033[0m [x86_64] Linear disassembly of code segment...")
    insns = []                    # ordered (addr, size, mnemonic, op_str)
    addr_index = {}
    for insn in md.disasm(code, code_vaddr):
        addr_index[insn.address] = len(insns)
        insns.append(insn)
    if not insns:
        print("\033[91m[-] [x86_64] Disassembly produced no instructions\033[0m")
        return None

    sc_va = ssl_client[0]
    ss_va = ssl_server[0]

    def lea_refs(target_va):
        refs = []
        for insn in insns:
            if insn.mnemonic != 'lea':
                continue
            for op in insn.operands:
                if op.type == X86_OP_MEM and op.mem.base and \
                   insn.reg_name(op.mem.base) == 'rip' and op.mem.index == 0:
                    if insn.address + insn.size + op.mem.disp == target_va:
                        refs.append(insn.address)
        return refs

    sc_refs = lea_refs(sc_va)
    ss_refs = lea_refs(ss_va)
    print(f"\033[96m[*]\033[0m ssl_client LEA refs: {[hex(x) for x in sc_refs]}")
    print(f"\033[96m[*]\033[0m ssl_server LEA refs: {[hex(x) for x in ss_refs]}")

    if not sc_refs or not ss_refs:
        print("\033[91m[-] [x86_64] Missing RIP-relative refs to one/both anchors\033[0m")
        return None

    # Function-start candidates: endbr64, or the instruction right after a
    # control-flow break (ret/jmp/int3), or the very first instruction.
    BREAKERS = {'ret', 'jmp', 'int3', 'ud2'}
    candidates = set()
    for i, insn in enumerate(insns):
        if i == 0 or insn.mnemonic == 'endbr64':
            candidates.add(insn.address)
        elif i > 0 and insns[i-1].mnemonic in BREAKERS:
            candidates.add(insn.address)
    sorted_c = sorted(candidates)

    def func_start_before(va):
        import bisect
        idx = bisect.bisect_right(sorted_c, va) - 1
        return sorted_c[idx] if idx >= 0 else None

    # Pair refs that sit in the same function (window generous for x86 funcs)
    for a in sc_refs:
        for b in ss_refs:
            if abs(a - b) < 0x1200:
                fs = func_start_before(min(a, b))
                if fs is not None:
                    rva = fs - base_vaddr
                    fo = fs - code_vaddr + code_foff
                    print(f"\033[92m[+]\033[0m [x86_64] SSL verify offset (RVA): \033[93m{hex(rva)}\033[0m")
                    print(f"\033[92m[+]\033[0m First bytes: {data[fo:fo+16].hex(' ')}")
                    return rva

    print("\033[91m[-] [x86_64] Could not resolve enclosing function\033[0m")
    return None


# ─────────────────────────────────────────────
#  ENGINE — armeabi-v7a (ELF32). Needs capstone.
#  MOVW/MOVT+ADD-PC and LDR-literal refs + PUSH{...,lr} prologue.
#  Flutter ARM32 is compiled as Thumb-2.
# ─────────────────────────────────────────────

def scan_arm32(data, base_vaddr, code_foff, code_vaddr, code_filesz, ssl_client, ssl_server):
    cs = _load_capstone()
    if cs is None:
        return None
    from capstone.arm import ARM_OP_REG, ARM_OP_IMM, ARM_REG_PC

    def align4(x):
        return x & ~3

    def run(mode_thumb):
        mode = cs.CS_MODE_THUMB if mode_thumb else cs.CS_MODE_ARM
        md = cs.Cs(cs.CS_ARCH_ARM, mode)
        md.detail = True
        code = data[code_foff:code_foff + code_filesz]

        insns = []
        for insn in md.disasm(code, code_vaddr):
            insns.append(insn)
        return insns

    # Flutter ARM32 engine is Thumb-2; try Thumb first, fall back to ARM.
    insns = run(True)
    label = 'thumb'
    if len(insns) < (code_filesz // 8):     # suspiciously sparse -> try ARM
        alt = run(False)
        if len(alt) > len(insns):
            insns, label = alt, 'arm'
    print(f"\033[96m[*]\033[0m [armeabi-v7a] Disassembled {len(insns)} insns ({label} mode)")

    sc_va = ssl_client[0]
    ss_va = ssl_server[0]

    # --- Pass 1: MOVW/MOVT + ADD Rd,PC (PIC address computation) ---
    def movw_movt_refs():
        sc, ss = [], []
        regs = {}
        for insn in insns:
            m = insn.mnemonic
            ops = insn.operands
            if m == 'movw' and len(ops) == 2 and ops[0].type == ARM_OP_REG and ops[1].type == ARM_OP_IMM:
                regs[ops[0].reg] = ops[1].imm & 0xffff
            elif m == 'movt' and len(ops) == 2 and ops[0].type == ARM_OP_REG and ops[1].type == ARM_OP_IMM:
                r = ops[0].reg
                regs[r] = (regs.get(r, 0) & 0xffff) | ((ops[1].imm & 0xffff) << 16)
            elif m == 'add' and len(ops) >= 2 and ops[-1].type == ARM_OP_REG and ops[-1].reg == ARM_REG_PC:
                rd = ops[0].reg
                if rd in regs:
                    pc = align4(insn.address + 4)
                    tgt = (pc + regs[rd]) & 0xffffffff
                    if tgt == sc_va:
                        sc.append(insn.address)
                    elif tgt == ss_va:
                        ss.append(insn.address)
            else:
                # a plain mov/other write to a reg invalidates stale tracking
                if ops and ops[0].type == ARM_OP_REG and m in ('mov', 'ldr', 'sub', 'orr', 'eor'):
                    regs.pop(ops[0].reg, None)
        return sc, ss

    # --- Pass 2: LDR Rd,[pc,#imm] literal pool (best-effort) ---
    def ldr_literal_refs():
        sc, ss = [], []
        for insn in insns:
            if insn.mnemonic != 'ldr':
                continue
            ops = insn.operands
            # ldr rd, [pc, #imm]
            if len(ops) == 2 and ops[1].type == cs.arm.ARM_OP_MEM and \
               ops[1].mem.base == ARM_REG_PC:
                pool_va = align4(insn.address + 4) + ops[1].mem.disp
                pool_fo = pool_va - code_vaddr + code_foff
                if 0 <= pool_fo <= len(data) - 4:
                    word = struct.unpack_from('<I', data, pool_fo)[0]
                    if word == sc_va:
                        sc.append(insn.address)
                    elif word == ss_va:
                        ss.append(insn.address)
        return sc, ss

    sc_refs, ss_refs = movw_movt_refs()
    if not (sc_refs and ss_refs):
        l_sc, l_ss = ldr_literal_refs()
        sc_refs += l_sc
        ss_refs += l_ss
    print(f"\033[96m[*]\033[0m ssl_client refs: {[hex(x) for x in sc_refs]}")
    print(f"\033[96m[*]\033[0m ssl_server refs: {[hex(x) for x in ss_refs]}")

    if not sc_refs or not ss_refs:
        print("\033[91m[-] [armeabi-v7a] Missing refs to one/both anchors\033[0m")
        return None

    # Function starts: Thumb prologue PUSH {..., lr}
    push_lr = []
    for insn in insns:
        if insn.mnemonic in ('push', 'push.w') and 'lr' in insn.op_str:
            push_lr.append(insn.address)
    push_lr.sort()

    def func_start_before(va):
        import bisect
        idx = bisect.bisect_right(push_lr, va) - 1
        return push_lr[idx] if idx >= 0 else None

    for a in sc_refs:
        for b in ss_refs:
            if abs(a - b) < 0x800:
                fs = func_start_before(min(a, b))
                if fs is not None:
                    rva = fs - base_vaddr
                    fo = fs - code_vaddr + code_foff
                    print(f"\033[92m[+]\033[0m [armeabi-v7a] SSL verify offset (RVA): \033[93m{hex(rva)}\033[0m")
                    print(f"\033[92m[+]\033[0m First bytes: {data[fo:fo+16].hex(' ')}")
                    # Thumb functions are odd-addressed when branched to; the
                    # module-base + rva Frida hook works with the even address.
                    return rva

    print("\033[91m[-] [armeabi-v7a] Could not resolve enclosing function\033[0m")
    return None


# ─────────────────────────────────────────────
#  CORE — FIND SSL OFFSET (dispatches by architecture)
# ─────────────────────────────────────────────

def find_offset(binary_path, platform, arch=None):
    print(f"\033[96m[*]\033[0m Loading binary: {binary_path}")
    with open(binary_path, 'rb') as f:
        data = f.read()

    # Find string anchors (architecture-independent)
    ssl_client = [m.start() for m in re.finditer(b'ssl_client\x00', data)]
    ssl_server = [m.start() for m in re.finditer(b'ssl_server\x00', data)]

    if not ssl_client or not ssl_server:
        print("\033[91m[-] ssl_client/ssl_server strings not found — may not be a Flutter binary\033[0m")
        return None

    print(f"\033[92m[+]\033[0m ssl_client @ {[hex(x) for x in ssl_client]}")
    print(f"\033[92m[+]\033[0m ssl_server @ {[hex(x) for x in ssl_server]}")

    # ---- iOS: always arm64 Mach-O ----
    if platform == 'ios':
        base_vaddr, code_foff, code_vaddr, code_filesz, data = parse_macho_segments(data)
        ssl_client = [m.start() for m in re.finditer(b'ssl_client\x00', data)]
        ssl_server = [m.start() for m in re.finditer(b'ssl_server\x00', data)]
        if not ssl_client or not ssl_server:
            print("\033[91m[-] ssl_client/ssl_server strings not found in arm64 slice\033[0m")
            return None
        if code_foff is None:
            print("\033[91m[-] No executable segment found\033[0m")
            return None
        return scan_arm64(data, base_vaddr, code_foff, code_vaddr, code_filesz, ssl_client, ssl_server)

    # ---- Android: detect arch from the ELF header itself ----
    bin_arch = detect_binary_arch(data)
    if bin_arch is None:
        print("\033[91m[-] Unrecognised ELF machine type\033[0m")
        return None
    print(f"\033[96m[*]\033[0m Binary arch (from ELF header): \033[93m{bin_arch}\033[0m")

    if bin_arch in ('arm64', 'x86_64'):
        base_vaddr, code_foff, code_vaddr, code_filesz = parse_elf64_segments(data)
    else:  # arm (v7a) / x86 -> ELF32
        base_vaddr, code_foff, code_vaddr, code_filesz = parse_elf32_segments(data)

    if code_foff is None:
        print("\033[91m[-] No executable segment found\033[0m")
        return None

    if bin_arch == 'arm64':
        return scan_arm64(data, base_vaddr, code_foff, code_vaddr, code_filesz, ssl_client, ssl_server)
    elif bin_arch == 'x86_64':
        return scan_x86_64(data, base_vaddr, code_foff, code_vaddr, code_filesz, ssl_client, ssl_server)
    elif bin_arch == 'arm':
        return scan_arm32(data, base_vaddr, code_foff, code_vaddr, code_filesz, ssl_client, ssl_server)
    else:  # x86 (32-bit) — rare (old emulator images)
        print("\033[93m[!] x86 (32-bit) has no PC-relative addressing; static "
              "resolution is unreliable. Prefer x86_64 or run objection/frida "
              "dynamically. Skipping.\033[0m")
        return None


# ─────────────────────────────────────────────
#  FRIDA SCRIPT GENERATOR
# ─────────────────────────────────────────────

def write_frida_script(offset, package, platform, out_path):
    # Module name is libflutter.so on ALL Android ABIs; Flutter on iOS.
    module_name = 'libflutter.so' if platform == 'android' else 'Flutter'

    script = f"""// ================================================
// K!ll Fl!utter - Auto-generated Frida Script
// By: f3rb
// Platform : {platform.upper()}
// Package  : {package}
// Offset   : {hex(offset)}
// Module   : {module_name}
// ================================================

function hook_ssl_verify_result(address) {{
    Interceptor.attach(address, {{
        onEnter: function(args) {{
            console.log("[+] ssl_verify hooked — killing cert validation");
        }},
        onLeave: function(retval) {{
            console.log("[*] retval was: " + retval);
            retval.replace(ptr("0x1"));
            console.log("[*] forced success");
        }}
    }});
}}

function disablePinning() {{
    var m = Process.findModuleByName("{module_name}");
    if (!m) {{
        console.log("[-] {module_name} not found");
        return;
    }}
    console.log("[+] {module_name} base: " + m.base);

    var offset = {hex(offset)};
    var addr = m.base.add(offset);
    console.log("[+] Hooking at: " + addr);
    hook_ssl_verify_result(addr);
}}

setTimeout(disablePinning, 1000);
"""
    with open(out_path, 'w') as f:
        f.write(script)
    print(f"\033[92m[+]\033[0m Frida script saved: \033[93m{out_path}\033[0m")


# ─────────────────────────────────────────────
#  PRINT FINAL COMMANDS
# ─────────────────────────────────────────────

def print_commands_android(package, proxy, script_path):
    set_443   = f'adb shell su -c "iptables -t nat -A OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    set_80    = f'adb shell su -c "iptables -t nat -A OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'
    verify    = 'adb shell su -c "iptables -t nat -L OUTPUT --line-numbers"'
    frida_cmd = f'frida -U -f {package} -l "{script_path}"'
    del_443   = f'adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    del_80    = f'adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'

    print("")
    print(box_top())
    print(box_line("          ANDROID — COPY PASTE COMMANDS", C_YELLOW))
    print(box_bottom())
    print("")
    print("\033[93m[1] Set iptables on device:\033[0m")
    print("  " + set_443)
    print("  " + set_80)
    print("")
    print("\033[93m[2] Verify iptables rules:\033[0m")
    print("  " + verify)
    print("")
    print("\033[93m[3] Launch Frida:\033[0m")
    print("\033[92m  " + frida_cmd + "\033[0m")
    print("")
    print("\033[93m[4] Revert when done:\033[0m")
    print("  " + del_443)
    print("  " + del_80)
    print("\033[90m  # or just: adb reboot\033[0m")


def print_commands_ios(package, proxy, script_path, device_ip):
    frida_cmd = f'frida -U -f {package} -l "{script_path}"'
    set_443   = f'ssh root@{device_ip} "iptables -t nat -A OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    set_80    = f'ssh root@{device_ip} "iptables -t nat -A OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'
    del_443   = f'ssh root@{device_ip} "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    del_80    = f'ssh root@{device_ip} "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'

    print("")
    print(box_top())
    print(box_line("            iOS — COPY PASTE COMMANDS", C_YELLOW))
    print(box_bottom())
    print("")
    print("\033[93m[1] Set WiFi proxy on device:\033[0m")
    print(f"  Settings → WiFi → Your Network → HTTP Proxy → Manual")
    print(f"  Server: {proxy.split(':')[0]}  Port: {proxy.split(':')[1]}")
    print("")
    print("\033[93m[2] Set iptables on device (jailbroken via SSH):\033[0m")
    print("  " + set_443)
    print("  " + set_80)
    print("")
    print("\033[93m[3] Launch Frida:\033[0m")
    print("\033[92m  " + frida_cmd + "\033[0m")
    print("")
    print("\033[93m[4] Revert when done:\033[0m")
    print("  " + del_443)
    print("  " + del_80)
    print("\033[90m  # or just reboot the device\033[0m")


def print_summary(package, offset, script_path, proxy, platform, arch=None):
    print("")
    print(box_top())
    print(box_line(f"  Platform : {platform.upper()}", C_GREEN))
    if arch:
        print(box_line(f"  ABI      : {arch}", C_GREEN))
    print(box_line(f"  Package  : {package}", C_GREEN))
    print(box_line(f"  Offset   : {hex(offset)}", C_GREEN))
    print(box_line(f"  Script   : {os.path.basename(script_path)}", C_GREEN))
    print(box_line(f"  Proxy    : {proxy}", C_GREEN))
    print(box_bottom())
    print("")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        print_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('app', nargs='?', help='Path to APK or IPA')
    parser.add_argument('-i', '--ip', default='<YOUR_IP>', help='Your machine IP')
    parser.add_argument('-p', '--port', default='8080', help='Burp port')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('--arch', choices=KNOWN_ABIS, help='Android ABI to target')
    parser.add_argument('--list-arch', action='store_true', help='List ABIs in the APK and exit')
    parser.add_argument('--platform', choices=['android', 'ios'], help='Force platform')
    parser.add_argument('--device-ip', default='<DEVICE_IP>', help='iOS device IP (for SSH iptables)')
    args = parser.parse_args()

    print_banner()

    app_path = args.app
    if not app_path:
        print("\033[91m[-] No APK/IPA provided. Use -h for help.\033[0m")
        sys.exit(1)

    if not os.path.exists(app_path):
        print(f"\033[91m[-] File not found: {app_path}\033[0m")
        sys.exit(1)

    platform = detect_platform(app_path, args.platform)

    # --list-arch shortcut (Android only)
    if args.list_arch:
        if platform != 'android':
            print("\033[93m[!] --list-arch only applies to Android APKs\033[0m")
            sys.exit(0)
        arches = list_flutter_arches(app_path)
        if not arches:
            print("\033[91m[-] No libflutter.so found in this APK\033[0m")
        else:
            print("\033[92m[+]\033[0m ABIs bundled in this APK:")
            for a in sorted(arches):
                supported = "\033[92msupported\033[0m" if a in ('arm64-v8a', 'x86_64', 'armeabi-v7a') else "\033[93mlimited\033[0m"
                print(f"    - {a:<14} ({supported})")
        sys.exit(0)

    out_dir  = args.output or os.path.dirname(os.path.abspath(app_path))
    os.makedirs(out_dir, exist_ok=True)

    ip        = args.ip
    port      = args.port
    proxy     = ip + ":" + port
    device_ip = args.device_ip

    print(f"\033[96m[*]\033[0m Platform : \033[93m{platform.upper()}\033[0m")
    print(f"\033[96m[*]\033[0m App      : {app_path}")
    print(f"\033[96m[*]\033[0m Output   : {out_dir}")
    print(f"\033[96m[*]\033[0m Proxy    : {proxy}")

    # Step 1: Get identifier
    if platform == 'android':
        package = get_package_name_android(app_path)
        if package:
            print(f"\033[92m[+]\033[0m Package: \033[93m{package}\033[0m")
        else:
            package = input("\033[93m[?] Enter package name manually: \033[0m").strip()
    else:
        package = get_bundle_id_ios(app_path)
        if package:
            print(f"\033[92m[+]\033[0m Bundle ID: \033[93m{package}\033[0m")
        else:
            package = input("\033[93m[?] Enter bundle ID manually (e.g. com.example.app): \033[0m").strip()

    # Step 2: Extract Flutter binary
    arch = None
    if platform == 'android':
        binary_path, arch = extract_flutter_android(app_path, out_dir, args.arch)
    else:
        binary_path = extract_flutter_ios(app_path, out_dir)

    if not binary_path:
        sys.exit(1)

    # Step 3: Find SSL offset
    offset = find_offset(binary_path, platform, arch)
    if offset is None:
        sys.exit(1)

    # Step 4: Write Frida script
    script_path = os.path.join(out_dir, 'flutter_bypass.js')
    write_frida_script(offset, package, platform, script_path)

    # Step 5: Print commands
    if platform == 'android':
        print_commands_android(package, proxy, script_path)
    else:
        print_commands_ios(package, proxy, script_path, device_ip)

    print_summary(package, offset, script_path, proxy, platform, arch)


if __name__ == '__main__':
    main()
