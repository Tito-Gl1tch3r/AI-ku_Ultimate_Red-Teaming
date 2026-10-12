#define _DEFAULT_SOURCE
/*
 * LogReaper v1.0 - High-Speed Log Analysis & Forensics Tool
 * Part of the NullSec Toolkit
 * 
 * Copyright (c) 2025 bad-antics
 * MIT License
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <dirent.h>
#include <sys/stat.h>
#include <time.h>
#include <regex.h>
#include <signal.h>
#include <errno.h>

#define VERSION "1.0.0"
#define MAX_LINE 8192
#define MAX_PATTERNS 512
#define MAX_IOCS 4096

// ANSI colors
#define RED     "\033[1;31m"
#define GREEN   "\033[1;32m"
#define YELLOW  "\033[1;33m"
#define BLUE    "\033[1;34m"
#define MAGENTA "\033[1;35m"
#define CYAN    "\033[1;36m"
#define WHITE   "\033[1;37m"
#define RESET   "\033[0m"

// Severity levels
typedef enum {
    SEV_LOW = 0,
    SEV_MEDIUM = 1,
    SEV_HIGH = 2,
    SEV_CRITICAL = 3
} severity_t;

// Detection pattern
typedef struct {
    char name[64];
    char pattern[512];
    severity_t severity;
    regex_t regex;
    int compiled;
} pattern_t;

// Finding result
typedef struct {
    char pattern_name[64];
    char source_file[256];
    char line[MAX_LINE];
    int line_num;
    time_t timestamp;
    severity_t severity;
} finding_t;

// IOC types
typedef struct {
    char ips[MAX_IOCS][46];
    char domains[MAX_IOCS][256];
    char hashes[MAX_IOCS][65];
    int ip_count;
    int domain_count;
    int hash_count;
} ioc_list_t;

// Global state
static pattern_t patterns[MAX_PATTERNS];
static int pattern_count = 0;
static finding_t *findings = NULL;
static int finding_count = 0;
static int finding_capacity = 0;
static ioc_list_t iocs = {0};
static volatile int running = 1;

// Statistics
static struct {
    int files_scanned;
    long lines_processed;
    int critical;
    int high;
    int medium;
    int low;
} stats = {0};

// Auth patterns
static const char *auth_patterns[][3] = {
    {"AUTH_BRUTE_SSH", "Failed password.*sshd", "HIGH"},
    {"AUTH_BRUTE_SSH", "authentication failure.*sshd", "HIGH"},
    {"AUTH_SUDO_ABUSE", "sudo:.*command not allowed", "MEDIUM"},
    {"AUTH_SUDO_ABUSE", "sudo:.*3 incorrect password attempts", "HIGH"},
    {"AUTH_SU_ROOT", "su\\[.*\\].*session opened.*root", "HIGH"},
    {"AUTH_FAIL_BURST", "PAM.*authentication failure", "MEDIUM"},
    {"AUTH_NEW_USER", "useradd\\[.*\\].*new user", "MEDIUM"},
    {"AUTH_PASSWD_CHG", "passwd\\[.*\\].*password changed", "MEDIUM"},
    {"AUTH_KEY_ACCEPT", "Accepted publickey for", "LOW"},
    {"AUTH_INVALID_USER", "Invalid user.*from", "HIGH"},
    {NULL, NULL, NULL}
};

// Web attack patterns  
static const char *web_patterns[][3] = {
    {"WEB_SQLI", "('|\"|--).*([Oo][Rr]|[Uu][Nn][Ii][Oo][Nn]).*([Ss][Ee][Ll][Ee][Cc][Tt]|[Dd][Rr][Oo][Pp])", "CRITICAL"},
    {"WEB_SQLI", "(;|').*([Dd][Rr][Oo][Pp]|[Dd][Ee][Ll][Ee][Tt][Ee]).*[Tt][Aa][Bb][Ll][Ee]", "CRITICAL"},
    {"WEB_XSS", "<[Ss][Cc][Rr][Ii][Pp][Tt].*>", "HIGH"},
    {"WEB_XSS", "[Oo][Nn][Ee][Rr][Rr][Oo][Rr]=", "HIGH"},
    {"WEB_LFI", "\\.\\./\\.\\./", "CRITICAL"},
    {"WEB_LFI", "/etc/passwd", "CRITICAL"},
    {"WEB_LFI", "/etc/shadow", "CRITICAL"},
    {"WEB_RFI", "(http|https|ftp)://.*\\.(php|txt|sh)", "CRITICAL"},
    {"WEB_PATH_TRAV", "%2e%2e/", "HIGH"},
    {"WEB_PATH_TRAV", "\\.\\.%2f", "HIGH"},
    {"WEB_CMD_INJ", ";.*(cat|ls|id|whoami|wget|curl)", "CRITICAL"},
    {"WEB_CMD_INJ", "\\|(cat|ls|id|whoami|wget|curl)", "CRITICAL"},
    {"WEB_CMD_INJ", "\`.*\`", "HIGH"},
    {"WEB_SCANNER", "nikto|sqlmap|nmap|dirbuster|gobuster|wfuzz", "MEDIUM"},
    {"WEB_SCANNER", "acunetix|nessus|qualys|burp", "MEDIUM"},
    {NULL, NULL, NULL}
};

// System patterns
static const char *system_patterns[][3] = {
    {"SYS_KERNEL_MOD", "kernel:.*module.*loaded", "MEDIUM"},
    {"SYS_SELINUX_OFF", "selinux.*disabled", "HIGH"},
    {"SYS_SELINUX_OFF", "setenforce.*0", "HIGH"},
    {"SYS_CRON_CHANGE", "crontab\\[.*\\].*REPLACE", "MEDIUM"},
    {"SYS_CRON_CHANGE", "CRON\\[.*\\].*CMD", "LOW"},
    {"SYS_SERVICE_NEW", "systemd\\[.*\\].*Started", "LOW"},
    {"SYS_MOUNT_EXEC", "mount.*exec", "MEDIUM"},
    {"SYS_FIREWALL", "iptables.*DROP", "LOW"},
    {"SYS_FIREWALL", "nftables.*drop", "LOW"},
    {"SYS_OOM", "Out of memory: Killed process", "HIGH"},
    {"SYS_SEGFAULT", "segfault at", "MEDIUM"},
    {NULL, NULL, NULL}
};

// Malware/rootkit patterns
static const char *malware_patterns[][3] = {
    {"MAL_NETCAT_REV", "nc.*-e.*/bin/(ba)?sh", "CRITICAL"},
    {"MAL_PYTHON_REV", "python.*socket.*connect", "HIGH"},
    {"MAL_PERL_REV", "perl.*socket.*INET", "HIGH"},
    {"MAL_BASH_REV", "/dev/tcp/", "CRITICAL"},
    {"MAL_WGET_EXEC", "wget.*\\|.*sh", "CRITICAL"},
    {"MAL_CURL_EXEC", "curl.*\\|.*sh", "CRITICAL"},
    {"MAL_BASE64_EXEC", "base64.*-d.*\\|.*sh", "CRITICAL"},
    {"MAL_PROC_HIDE", "/proc/.*/cmdline", "MEDIUM"},
    {"MAL_PRELOAD", "LD_PRELOAD", "HIGH"},
    {"MAL_PTRACE", "ptrace.*ATTACH", "HIGH"},
    {"MAL_MEMFD", "memfd_create", "HIGH"},
    {NULL, NULL, NULL}
};

// Signal handler for live mode
void signal_handler(int sig) {
    if (sig == SIGINT) {
        running = 0;
        printf("\n" YELLOW "[*] Stopping..." RESET "\n");
    }
}

// Get severity from string
severity_t get_severity(const char *str) {
    if (strcmp(str, "CRITICAL") == 0) return SEV_CRITICAL;
    if (strcmp(str, "HIGH") == 0) return SEV_HIGH;
    if (strcmp(str, "MEDIUM") == 0) return SEV_MEDIUM;
    return SEV_LOW;
}

// Get severity string
const char* severity_str(severity_t sev) {
    switch(sev) {
        case SEV_CRITICAL: return RED "CRITICAL" RESET;
        case SEV_HIGH:     return RED "HIGH" RESET;
        case SEV_MEDIUM:   return YELLOW "MEDIUM" RESET;
        default:           return GREEN "LOW" RESET;
    }
}

// Load patterns from array
void load_patterns(const char *arr[][3]) {
    for (int i = 0; arr[i][0] != NULL && pattern_count < MAX_PATTERNS; i++) {
        strncpy(patterns[pattern_count].name, arr[i][0], 63);
        strncpy(patterns[pattern_count].pattern, arr[i][1], 511);
        patterns[pattern_count].severity = get_severity(arr[i][2]);
        
        if (regcomp(&patterns[pattern_count].regex, arr[i][1], 
                    REG_EXTENDED | REG_ICASE | REG_NOSUB) == 0) {
            patterns[pattern_count].compiled = 1;
            pattern_count++;
        }
    }
}

// Add finding
void add_finding(const char *pattern_name, const char *file, const char *line, 
                 int line_num, severity_t sev) {
    if (finding_count >= finding_capacity) {
        finding_capacity = finding_capacity == 0 ? 256 : finding_capacity * 2;
        finding_t *tmp = realloc(findings, finding_capacity * sizeof(finding_t));
        if (!tmp) {
            fprintf(stderr, "logreaper: out of memory\n");
            return;
        }
        findings = tmp;
    }
    
    finding_t *f = &findings[finding_count++];
    strncpy(f->pattern_name, pattern_name, 63);
    strncpy(f->source_file, file, 255);
    strncpy(f->line, line, MAX_LINE - 1);
    f->line_num = line_num;
    f->severity = sev;
    f->timestamp = time(NULL);
    
    switch(sev) {
        case SEV_CRITICAL: stats.critical++; break;
        case SEV_HIGH:     stats.high++; break;
        case SEV_MEDIUM:   stats.medium++; break;
        default:           stats.low++; break;
    }
}

// Extract IP addresses from line
void extract_ips(const char *line) {
    regex_t ip_regex;
    regmatch_t match[1];
    const char *ip_pattern = "([0-9]{1,3}\\.){3}[0-9]{1,3}";
    
    if (regcomp(&ip_regex, ip_pattern, REG_EXTENDED) != 0) return;
    
    const char *p = line;
    while (regexec(&ip_regex, p, 1, match, 0) == 0 && iocs.ip_count < MAX_IOCS) {
        int len = match[0].rm_eo - match[0].rm_so;
        if (len < 46) {
            char ip[46];
            strncpy(ip, p + match[0].rm_so, len);
            ip[len] = '\0';
            
            // Check for duplicate
            int exists = 0;
            for (int i = 0; i < iocs.ip_count; i++) {
                if (strcmp(iocs.ips[i], ip) == 0) { exists = 1; break; }
            }
            if (!exists && strcmp(ip, "127.0.0.1") != 0) {
                strcpy(iocs.ips[iocs.ip_count++], ip);
            }
        }
        p += match[0].rm_eo;
    }
    regfree(&ip_regex);
}

// Analyze single line
void analyze_line(const char *file, const char *line, int line_num, int extract_iocs) {
    stats.lines_processed++;
    
    for (int i = 0; i < pattern_count; i++) {
        if (!patterns[i].compiled) continue;
        if (regexec(&patterns[i].regex, line, 0, NULL, 0) == 0) {
            add_finding(patterns[i].name, file, line, line_num, patterns[i].severity);
        }
    }
    
    if (extract_iocs) {
        extract_ips(line);
    }
}

// Analyze single file
int analyze_file(const char *filepath, int extract_iocs) {
    FILE *fp = fopen(filepath, "r");
    if (!fp) return -1;
    
    stats.files_scanned++;
    char line[MAX_LINE];
    int line_num = 0;
    
    while (fgets(line, sizeof(line), fp) && running) {
        line_num++;
        // Strip newline
        line[strcspn(line, "\n")] = 0;
        analyze_line(filepath, line, line_num, extract_iocs);
    }
    
    fclose(fp);
    return 0;
}

// Analyze directory recursively
int analyze_directory(const char *dirpath, int extract_iocs) {
    DIR *dir = opendir(dirpath);
    if (!dir) return -1;
    
    struct dirent *entry;
    char path[1024];
    
    while ((entry = readdir(dir)) != NULL && running) {
        if (entry->d_name[0] == '.') continue;
        
        snprintf(path, sizeof(path), "%s/%s", dirpath, entry->d_name);
        
        struct stat st;
        if (stat(path, &st) != 0) continue;
        
        if (S_ISDIR(st.st_mode)) {
            analyze_directory(path, extract_iocs);
        } else if (S_ISREG(st.st_mode)) {
            // Only analyze text/log files
            const char *ext = strrchr(entry->d_name, '.');
            if (ext && (strcmp(ext, ".log") == 0 || strcmp(ext, ".txt") == 0)) {
                analyze_file(path, extract_iocs);
            } else if (!ext) {
                // Files without extension (common for logs)
                analyze_file(path, extract_iocs);
            }
        }
    }
    
    closedir(dir);
    return 0;
}

// Live monitoring mode
void live_monitor(const char *filepath) {
    signal(SIGINT, signal_handler);
    
    FILE *fp = fopen(filepath, "r");
    if (!fp) {
        fprintf(stderr, RED "[!] Cannot open: %s\n" RESET, filepath);
        return;
    }
    
    // Seek to end
    fseek(fp, 0, SEEK_END);
    
    printf(CYAN "[*] Live monitoring: %s (Ctrl+C to stop)\n" RESET, filepath);
    
    char line[MAX_LINE];
    int line_num = 0;
    
    while (running) {
        if (fgets(line, sizeof(line), fp)) {
            line_num++;
            line[strcspn(line, "\n")] = 0;
            
            int prev_count = finding_count;
            analyze_line(filepath, line, line_num, 1);
            
            // If new finding, print immediately
            if (finding_count > prev_count) {
                finding_t *f = &findings[finding_count - 1];
                printf("\n[%s] %s\n", severity_str(f->severity), f->pattern_name);
                printf("    %s\n", f->line);
            }
        } else {
            clearerr(fp);
            usleep(100000); // 100ms
        }
    }
    
    fclose(fp);
}

// Print summary banner
void print_banner(void) {
    printf(CYAN "\n");
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║           " WHITE "🪓 LogReaper Analysis Results" CYAN "                     ║\n");
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║" WHITE "  Files Scanned:  %-44d" CYAN "║\n", stats.files_scanned);
    printf("║" WHITE "  Lines Analyzed: %-44ld" CYAN "║\n", stats.lines_processed);
    printf("╠══════════════════════════════════════════════════════════════╣\n");
    printf("║  " RED "🔴 CRITICAL" CYAN "  │ %-44d║\n", stats.critical);
    printf("║  " RED "🟠 HIGH" CYAN "      │ %-44d║\n", stats.high);
    printf("║  " YELLOW "🟡 MEDIUM" CYAN "    │ %-44d║\n", stats.medium);
    printf("║  " GREEN "🟢 LOW" CYAN "       │ %-44d║\n", stats.low);
    printf("╚══════════════════════════════════════════════════════════════╝\n" RESET);
    printf("\n");
}

// Print findings
void print_findings(int verbose) {
    print_banner();
    
    if (finding_count == 0) {
        printf(GREEN "[✓] No threats detected\n" RESET);
        return;
    }
    
    // Print findings by severity (critical first) - fixed loop
    int sev_order[] = {SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM, SEV_LOW};
    for (int s = 0; s < 4; s++) {
        int sev = sev_order[s];
        for (int i = 0; i < finding_count; i++) {
            if (findings[i].severity != sev) continue;
            
            printf("[%s] %s\n", severity_str(findings[i].severity), 
                   findings[i].pattern_name);
            printf("    File: %s:%d\n", findings[i].source_file, 
                   findings[i].line_num);
            if (verbose) {
                printf("    Line: %.80s%s\n", findings[i].line,
                       strlen(findings[i].line) > 80 ? "..." : "");
            }
            printf("\n");
        }
    }
}

// Print IOCs
void print_iocs(void) {
    if (iocs.ip_count == 0) {
        printf(YELLOW "[*] No IOCs extracted\n" RESET);
        return;
    }
    
    printf(CYAN "\n═══ Extracted IOCs ═══\n" RESET);
    printf("\n" WHITE "IP Addresses (%d):\n" RESET, iocs.ip_count);
    for (int i = 0; i < iocs.ip_count; i++) {
        printf("  %s\n", iocs.ips[i]);
    }
}

// Output JSON
void output_json(const char *filename) {
    FILE *fp = fopen(filename, "w");
    if (!fp) {
        fprintf(stderr, RED "[!] Cannot write to: %s\n" RESET, filename);
        return;
    }
    
    time_t now = time(NULL);
    char timebuf[32];
    strftime(timebuf, sizeof(timebuf), "%Y%m%d-%H%M%S", localtime(&now));
    
    fprintf(fp, "{\n");
    fprintf(fp, "  \"scan_id\": \"lr-%s\",\n", timebuf);
    fprintf(fp, "  \"version\": \"%s\",\n", VERSION);
    fprintf(fp, "  \"stats\": {\n");
    fprintf(fp, "    \"files_scanned\": %d,\n", stats.files_scanned);
    fprintf(fp, "    \"lines_processed\": %ld,\n", stats.lines_processed);
    fprintf(fp, "    \"critical\": %d,\n", stats.critical);
    fprintf(fp, "    \"high\": %d,\n", stats.high);
    fprintf(fp, "    \"medium\": %d,\n", stats.medium);
    fprintf(fp, "    \"low\": %d\n", stats.low);
    fprintf(fp, "  },\n");
    
    fprintf(fp, "  \"iocs\": {\n");
    fprintf(fp, "    \"ips\": [");
    for (int i = 0; i < iocs.ip_count; i++) {
        fprintf(fp, "\"%s\"%s", iocs.ips[i], i < iocs.ip_count - 1 ? ", " : "");
    }
    fprintf(fp, "]\n  },\n");
    
    fprintf(fp, "  \"findings\": [\n");
    for (int i = 0; i < finding_count; i++) {
        fprintf(fp, "    {\n");
        fprintf(fp, "      \"pattern\": \"%s\",\n", findings[i].pattern_name);
        fprintf(fp, "      \"severity\": %d,\n", findings[i].severity);
        fprintf(fp, "      \"file\": \"%s\",\n", findings[i].source_file);
        fprintf(fp, "      \"line_num\": %d\n", findings[i].line_num);
        fprintf(fp, "    }%s\n", i < finding_count - 1 ? "," : "");
    }
    fprintf(fp, "  ]\n");
    fprintf(fp, "}\n");
    
    fclose(fp);
    printf(GREEN "[✓] Report saved: %s\n" RESET, filename);
}

// Output CSV  
void output_csv(const char *filename) {
    FILE *fp = fopen(filename, "w");
    if (!fp) {
        fprintf(stderr, RED "[!] Cannot write to: %s\n" RESET, filename);
        return;
    }
    
    fprintf(fp, "severity,pattern,file,line_num\n");
    for (int i = 0; i < finding_count; i++) {
        const char *sev_name[] = {"LOW", "MEDIUM", "HIGH", "CRITICAL"};
        fprintf(fp, "%s,%s,%s,%d\n", 
                sev_name[findings[i].severity],
                findings[i].pattern_name,
                findings[i].source_file,
                findings[i].line_num);
    }
    
    fclose(fp);
    printf(GREEN "[✓] CSV saved: %s\n" RESET, filename);
}

// Print usage
void print_usage(const char *prog) {
    printf(CYAN "🪓 LogReaper v%s - Log Analysis & Forensics\n\n" RESET, VERSION);
    printf("Usage: %s [OPTIONS] <target>\n\n", prog);
    printf("Modules:\n");
    printf("  -a, --auth       Auth log analysis (brute force, sudo, su)\n");
    printf("  -w, --web        Web log analysis (SQLi, XSS, LFI, RFI)\n");
    printf("  -s, --system     System log analysis (kernel, services)\n");
    printf("  -m, --malware    Malware/rootkit indicators\n");
    printf("  -A, --all        All modules (default)\n\n");
    printf("Options:\n");
    printf("  -l, --live       Live monitoring mode\n");
    printf("  -i, --iocs       Extract IOCs (IPs, domains, hashes)\n");
    printf("  -o, --output     Output JSON report to file\n");
    printf("  -c, --csv        Output CSV report to file\n");
    printf("  -v, --verbose    Verbose output (show matched lines)\n");
    printf("  -q, --quiet      Quiet mode (summary only)\n");
    printf("  -h, --help       Show this help\n\n");
    printf("Examples:\n");
    printf("  %s -a /var/log/auth.log\n", prog);
    printf("  %s -w /var/log/nginx/access.log\n", prog);
    printf("  %s -A /var/log/ -o report.json\n", prog);
    printf("  %s -l /var/log/syslog\n", prog);
    printf("  %s -m -v /var/log/kern.log\n", prog);
}

int main(int argc, char *argv[]) {
    int opt;
    int mode_auth = 0, mode_web = 0, mode_system = 0, mode_malware = 0;
    int mode_live = 0, mode_iocs = 0, verbose = 0, quiet = 0;
    char *output_file = NULL;
    char *csv_file = NULL;
    
    static struct option long_opts[] = {
        {"auth",    no_argument,       0, 'a'},
        {"web",     no_argument,       0, 'w'},
        {"system",  no_argument,       0, 's'},
        {"malware", no_argument,       0, 'm'},
        {"all",     no_argument,       0, 'A'},
        {"live",    no_argument,       0, 'l'},
        {"iocs",    no_argument,       0, 'i'},
        {"output",  required_argument, 0, 'o'},
        {"csv",     required_argument, 0, 'c'},
        {"verbose", no_argument,       0, 'v'},
        {"quiet",   no_argument,       0, 'q'},
        {"help",    no_argument,       0, 'h'},
        {0, 0, 0, 0}
    };
    
    while ((opt = getopt_long(argc, argv, "awsmAlio:c:vqh", long_opts, NULL)) != -1) {
        switch (opt) {
            case 'a': mode_auth = 1; break;
            case 'w': mode_web = 1; break;
            case 's': mode_system = 1; break;
            case 'm': mode_malware = 1; break;
            case 'A': mode_auth = mode_web = mode_system = mode_malware = 1; break;
            case 'l': mode_live = 1; break;
            case 'i': mode_iocs = 1; break;
            case 'o': output_file = optarg; break;
            case 'c': csv_file = optarg; break;
            case 'v': verbose = 1; break;
            case 'q': quiet = 1; break;
            case 'h':
            default:
                print_usage(argv[0]);
                return opt == 'h' ? 0 : 1;
        }
    }
    
    if (optind >= argc) {
        print_usage(argv[0]);
        return 1;
    }
    
    // Default to all modules
    if (!mode_auth && !mode_web && !mode_system && !mode_malware) {
        mode_auth = mode_web = mode_system = mode_malware = 1;
    }
    
    // Load selected patterns
    if (mode_auth)    load_patterns(auth_patterns);
    if (mode_web)     load_patterns(web_patterns);
    if (mode_system)  load_patterns(system_patterns);
    if (mode_malware) load_patterns(malware_patterns);
    
    if (!quiet) {
        printf(CYAN "[*] Loaded %d detection patterns\n" RESET, pattern_count);
    }
    
    char *target = argv[optind];
    
    if (mode_live) {
        live_monitor(target);
    } else {
        struct stat st;
        if (stat(target, &st) != 0) {
            fprintf(stderr, RED "[!] Target not found: %s\n" RESET, target);
            return 1;
        }
        
        if (!quiet) {
            printf(CYAN "[*] Analyzing: %s\n" RESET, target);
        }
        
        if (S_ISDIR(st.st_mode)) {
            analyze_directory(target, mode_iocs);
        } else {
            analyze_file(target, mode_iocs);
        }
        
        if (!quiet) {
            print_findings(verbose);
        }
        
        if (mode_iocs && !quiet) {
            print_iocs();
        }
        
        if (output_file) {
            output_json(output_file);
        }
        
        if (csv_file) {
            output_csv(csv_file);
        }
    }
    
    // Cleanup
    for (int i = 0; i < pattern_count; i++) {
        if (patterns[i].compiled) {
            regfree(&patterns[i].regex);
        }
    }
    free(findings);
    
    return stats.critical > 0 ? 2 : (stats.high > 0 ? 1 : 0);
}
