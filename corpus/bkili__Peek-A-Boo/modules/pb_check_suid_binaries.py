# /modules/pb_check_gtfo_suid.py

from pathlib import Path
from modules.base import BaseModule
from core.utils.ssh_handler import create_ssh_client, ssh_exec
from core.utils.formatter import printc

GTFObins = {
    "7z",
    "ab",
    "agetty",
    "alpine",
    "ansible-playbook",
    "aoss",
    "apt",
    "apt-get",
    "ar",
    "aria2c",
    "arj",
    "arp",
    "ash",
    "aspell",
    "at",
    "awk",
    "base32",
    "base64",
    "bash",
    "bc",
    "bconsole",
    "bpftrace",
    "bridge",
    "bundler",
    "busybox",
    "bzip2",
    "c89",
    "c99",
    "capsh",
    "cat",
    "chroot",
    "clamscan",
    "cp",
    "cpio",
    "crontab",
    "csh",
    "csvtool",
    "curl",
    "cut",
    "dash",
    "date",
    "dc",
    "dd",
    "dialog",
    "diff",
    "dig",
    "dmesg",
    "dmsetup",
    "docker",
    "dosbox",
    "dotnet",
    "dpkg",
    "ed",
    "elvish",
    "emacs",
    "env",
    "eqn",
    "espeak",
    "ex",
    "expand",
    "expect",
    "facter",
    "file",
    "find",
    "flock",
    "fmt",
    "fold",
    "ftp",
    "gawk",
    "gcc",
    "gcloud",
    "gdb",
    "gem",
    "getent",
    "gimp",
    "git",
    "gpg",
    "grep",
    "gzip",
    "hd",
    "head",
    "hexdump",
    "iconv",
    "install",
    "ionice",
    "ip",
    "irb",
    "ispell",
    "join",
    "journalctl",
    "jq",
    "ksh",
    "ld.so",
    "less",
    "lftp",
    "ln",
    "locate",
    "loginctl",
    "logsave",
    "look",
    "ltrace",
    "lua",
    "mail",
    "make",
    "man",
    "mawk",
    "minicom",
    "more",
    "mount",
    "mtr",
    "mv",
    "mysql",
    "nano",
    "nasm",
    "nc",
    "ncftp",
    "neofetch",
    "netcat",
    "nft",
    "nice",
    "nl",
    "nm",
    "nmap",
    "node",
    "nohup",
    "npm",
    "nsenter",
    "od",
    "openssl",
    "openvpn",
    "opkg",
    "pdb",
    "perl",
    "pg",
    "php",
    "pic",
    "ping",
    "pkexec",
    "podman",
    "pr",
    "printenv",
    "ps",
    "ptpython",
    "puppet",
    "python",
    "python3",
    "rbash",
    "readelf",
    "readlink",
    "red",
    "restic",
    "rlwrap",
    "rpm",
    "rsync",
    "ruby",
    "run-mailcap",
    "rvim",
    "sash",
    "scp",
    "screen",
    "script",
    "sed",
    "setarch",
    "sftp",
    "sh",
    "sha1sum",
    "sha256sum",
    "shuf",
    "sl",
    "socat",
    "socksify",
    "soelim",
    "sort",
    "sqlite3",
    "ssh",
    "sshd",
    "stat",
    "stdbuf",
    "strace",
    "strings",
    "stunnel",
    "su",
    "sudo",
    "sum",
    "sv",
    "svn",
    "systemctl",
    "tail",
    "tar",
    "task",
    "tbl",
    "tcpdump",
    "tee",
    "telnet",
    "tftp",
    "time",
    "timeout",
    "tmux",
    "top",
    "touch",
    "tput",
    "tr",
    "troff",
    "ts",
    "tty",
    "ul",
    "uname",
    "unexpand",
    "uniq",
    "units",
    "unlzma",
    "unzip",
    "uudecode",
    "uuencode",
    "valgrind",
    "vi",
    "vim",
    "w",
    "watch",
    "wc",
    "wget",
    "who",
    "whoami",
    "write",
    "xargs",
    "xclip",
    "xhost",
    "xinput",
    "xmessage",
    "xmodmap",
    "xmore",
    "xprop",
    "xsel",
    "xsltproc",
    "xterm",
    "xxd",
    "xz",
    "zcat",
    "zsh",
}


class Module(BaseModule):
    def __init__(self):
        super().__init__()

        self.name = "pb_check_suid_binaries"
        self.description = (
            "Enumerate SUID binaries on the target system "
            "and check for known GTFOBins matches."
        )
        self.category = "recon"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = "https://github.com/bkili"
        self.license = ""
        self.version = "0.0.1"

        # Default options for the module
        self.default_options = {
            "rhost": "",
            "rport": "22",
            "username": "",
            "password": "",
        }

        # List of options that are considered required
        # (shown in CLI with 'yes' under Required)
        self.required_options = ["rhost", "username", "password"]

        self.options = self.default_options.copy()

    def requires(self):
        return []

    def run(self, shared_data):
        # Options
        host = self.options.get("rhost").strip()
        port = int(self.options.get("rport"))
        username = self.options.get("username").strip()
        password = self.options.get("password").strip()

        # Create ssh client
        try:
            printc(f"Trying to connect {host}:{port}", level="module")
            ssh = create_ssh_client(host, port, username, password)
        except Exception as e:
            printc(f"Failed to connect : {e}", level="error")
            return

        printc("SSH connected. Scanning for SUID binaries ...", level="module")
        suid_command = "find / -perm -4000 -type f 2> /dev/null"
        stdin, stdout, stderr = ssh_exec(ssh, suid_command)
        suid_binaries = stdout.splitlines()

        if not suid_binaries:
            printc("No SUID binaries found (?)", level="warn")
            return

        seen = set()
        unique_binaries = []
        for suid_binary in suid_binaries:
            bin_name = Path(suid_binary).name
            if bin_name not in seen:
                unique_binaries.append(bin_name)
                seen.add(bin_name)

        gtfo_bins = []
        non_gtfo_bins = []

        for bin_name in sorted(unique_binaries):
            if bin_name in GTFObins:
                url = f"https://gtfobins.github.io/gtfobins/{bin_name}"
                gtfo_bins.append((bin_name, url))
            else:
                non_gtfo_bins.append(bin_name)

        printc(f"{len(unique_binaries)} SUID binaries found.", level="info")
        printc("Found SUID binaries:", level="module")

        for bin_name, url in gtfo_bins:
            printc(f"[✓] {bin_name} : {url}", level="success")

        for bin_name in non_gtfo_bins:
            printc(f"[!] {bin_name}", level="info")

        ssh.close()
