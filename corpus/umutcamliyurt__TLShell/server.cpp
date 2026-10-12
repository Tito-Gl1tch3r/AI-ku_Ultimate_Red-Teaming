#include <openssl/ssl.h>
#include <openssl/err.h>
#include <iostream>
#include <iomanip>
#include <cstring>
#include <unistd.h>
#include <arpa/inet.h>
#include <thread>
#include <cstdlib>
#include <map>
#include <memory>
#include <mutex>
#include <atomic>
#include <csignal>
#include <vector>

void initialize_openssl() {
    SSL_load_error_strings();
    OpenSSL_add_ssl_algorithms();
}

void cleanup_openssl() {
    EVP_cleanup();
}

SSL_CTX *create_context() {
    const SSL_METHOD *method;
    SSL_CTX *ctx;

    method = TLS_server_method();
    ctx = SSL_CTX_new(method);
    if (!ctx) {
        perror("Unable to create SSL context");
        ERR_print_errors_fp(stderr);
        exit(EXIT_FAILURE);
    }

    SSL_CTX_set_options(ctx, SSL_OP_NO_SSLv2 | SSL_OP_NO_SSLv3 | SSL_OP_NO_TLSv1 | SSL_OP_NO_TLSv1_1);

    return ctx;
}

void configure_context(SSL_CTX *ctx) {
    if (SSL_CTX_use_certificate_file(ctx, "server.crt", SSL_FILETYPE_PEM) <= 0) {
        ERR_print_errors_fp(stderr);
        exit(EXIT_FAILURE);
    }

    if (SSL_CTX_use_PrivateKey_file(ctx, "server.key", SSL_FILETYPE_PEM) <= 0) {
        ERR_print_errors_fp(stderr);
        exit(EXIT_FAILURE);
    }
}

struct ClientSession {
    int id;
    int sockfd;
    SSL* ssl;
    std::string peer;
    std::thread reader;
    std::atomic<bool> alive{true};
    std::mutex write_mtx;
};

static std::atomic<bool> g_running{true};
static std::mutex g_clients_mtx;
static std::map<int, std::shared_ptr<ClientSession>> g_clients;
static std::mutex g_cout_mtx;
static std::atomic<int> g_next_id{1};
static std::atomic<int> g_active_id{-1};

void safe_print(const std::string& s) {
    std::lock_guard<std::mutex> lk(g_cout_mtx);
    std::cout << s << std::flush;
}

void close_session(const std::shared_ptr<ClientSession>& cs) {
    if (!cs) return;
    cs->alive = false;
    if (cs->ssl) {
        SSL_shutdown(cs->ssl);
        SSL_free(cs->ssl);
        cs->ssl = nullptr;
    }
    if (cs->sockfd >= 0) {
        close(cs->sockfd);
        cs->sockfd = -1;
    }
}

void remove_client(int id) {
    std::shared_ptr<ClientSession> to_close;
    {
        std::lock_guard<std::mutex> lk(g_clients_mtx);
        auto it = g_clients.find(id);
        if (it != g_clients.end()) {
            to_close = it->second;
            g_clients.erase(it);
        }
    }
    if (to_close) close_session(to_close);

    if (g_active_id == id) {
        g_active_id = -1;
        safe_print("\n[server] Active session cleared (client " + std::to_string(id) + " disconnected).\n> ");
    }
}

void client_reader(std::shared_ptr<ClientSession> cs) {
    char buf[4096];
    while (g_running && cs->alive) {
        int bytes = SSL_read(cs->ssl, buf, sizeof(buf) - 1);
        if (bytes > 0) {
            buf[bytes] = '\0';
            safe_print("\n[" + std::to_string(cs->id) + " " + cs->peer + "] " + std::string(buf) + "\n> ");
        } else {
            int err = SSL_get_error(cs->ssl, bytes);
            if (err == SSL_ERROR_ZERO_RETURN) {
                safe_print("\n[server] Client " + std::to_string(cs->id) + " closed TLS connection.\n");
            } else {
                safe_print("\n[server] Error reading from client " + std::to_string(cs->id) + ".\n");
            }
            break;
        }
    }
    remove_client(cs->id);
}

bool send_to_client(const std::shared_ptr<ClientSession>& cs, const std::string& msg) {
    if (!cs || !cs->alive) return false;
    std::lock_guard<std::mutex> lk(cs->write_mtx);
    int rc = SSL_write(cs->ssl, msg.c_str(), (int)msg.size());
    return rc == (int)msg.size();
}

void list_clients() {
    std::lock_guard<std::mutex> lk(g_clients_mtx);
    std::cout << "\nConnected clients:" << (g_clients.empty() ? " (none)" : "") << "\n";
    for (auto& [id, cs] : g_clients) {
        std::cout << "  #" << id << (g_active_id == id ? " *" : "  ")
                  << "  " << cs->peer << (cs->alive ? "" : " (dead)") << "\n";
    }
}

void broadcast(const std::string& msg) {
    std::vector<std::shared_ptr<ClientSession>> snapshot;
    {
        std::lock_guard<std::mutex> lk(g_clients_mtx);
        for (auto& [id, cs] : g_clients) snapshot.push_back(cs);
    }
    for (auto& cs : snapshot) send_to_client(cs, msg);
}

void kick_client(int id) {
    std::shared_ptr<ClientSession> cs;
    {
        std::lock_guard<std::mutex> lk(g_clients_mtx);
        auto it = g_clients.find(id);
        if (it != g_clients.end()) cs = it->second;
    }
    if (!cs) {
        safe_print("[server] No such client #" + std::to_string(id) + "\n");
        return;
    }
    close_session(cs);
}

void console_loop() {
    safe_print(
        "\nCommands:\n"
        "  /list                      - list clients\n"
        "  /switch <id>               - set active session\n"
        "  /broadcast <text>          - send to all clients\n"
        "  /kick <id>                 - disconnect a client\n"
        "  /help                      - show this help\n"
        "  /exit                      - shutdown server\n"
        "Typing anything else sends it to the active session.\n> ");

    std::string line;
    while (g_running && std::getline(std::cin, line)) {
        if (line.rfind("/", 0) == 0) {
            if (line == "/help") {
                safe_print(
                    "Commands:\n"
                    "  /list\n  /switch <id>\n  /broadcast <text>\n  /kick <id>\n  /help\n  /exit\n> ");
            } else if (line == "/list") {
                list_clients();
                safe_print("> ");
            } else if (line.rfind("/switch ", 0) == 0) {
                int id = std::atoi(line.substr(8).c_str());
                std::lock_guard<std::mutex> lk(g_clients_mtx);
                if (g_clients.count(id)) {
                    g_active_id = id;
                    safe_print("[server] Active session -> #" + std::to_string(id) + "\n> ");
                } else {
                    safe_print("[server] No such client #" + std::to_string(id) + "\n> ");
                }
            } else if (line.rfind("/broadcast ", 0) == 0) {
                std::string msg = line.substr(11);
                if (!msg.empty()) broadcast(msg);
                safe_print("> ");
            } else if (line.rfind("/kick ", 0) == 0) {
                int id = std::atoi(line.substr(6).c_str());
                kick_client(id);
                safe_print("> ");
            } else if (line == "/exit") {
                g_running = false;
                break;
            } else {
                safe_print("[server] Unknown command. Type /help.\n> ");
            }
        } else {
            int id = g_active_id.load();
            std::shared_ptr<ClientSession> cs;
            {
                std::lock_guard<std::mutex> lk(g_clients_mtx);
                auto it = g_clients.find(id);
                if (it != g_clients.end()) cs = it->second;
            }
            if (!cs) {
                safe_print("[server] No active session. Use /list then /switch <id>.\n> ");
                continue;
            }
            if (!send_to_client(cs, line)) {
                safe_print("[server] Failed to send to client #" + std::to_string(id) + "\n> ");
            } else {
                safe_print("> ");
            }
        }
    }
    g_running = false;
}

void sigint_handler(int) {
    g_running = false;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <port>" << std::endl;
        return EXIT_FAILURE;
    }

    int port = atoi(argv[1]);
    if (port <= 0) {
        std::cerr << "Invalid port number." << std::endl;
        return EXIT_FAILURE;
    }

    std::signal(SIGINT, sigint_handler);

    initialize_openssl();

    SSL_CTX *ctx = create_context();
    configure_context(ctx);

    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("Unable to create socket");
        exit(EXIT_FAILURE);
    }

    int opt = 1;
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(sockfd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("Unable to bind");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    if (listen(sockfd, 16) < 0) {
        perror("Unable to listen");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    std::thread console_thr(console_loop);

    safe_print("Server listening on port " + std::to_string(port) + "...\n");

    while (g_running) {
        struct sockaddr_in caddr{};
        socklen_t len = sizeof(caddr);
        int client_sock = accept(sockfd, (struct sockaddr*)&caddr, &len);
        if (client_sock < 0) {
            if (!g_running) break;
            perror("Unable to accept");
            continue;
        }

        SSL *ssl = SSL_new(ctx);
        SSL_set_fd(ssl, client_sock);

        if (SSL_accept(ssl) <= 0) {
            ERR_print_errors_fp(stderr);
            SSL_free(ssl);
            close(client_sock);
            continue;
        }

        char ipstr[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &caddr.sin_addr, ipstr, sizeof(ipstr));
        int id = g_next_id++;

        auto cs = std::make_shared<ClientSession>();
        cs->id = id;
        cs->sockfd = client_sock;
        cs->ssl = ssl;
        cs->peer = std::string(ipstr) + ":" + std::to_string(ntohs(caddr.sin_port));

        {
            std::lock_guard<std::mutex> lk(g_clients_mtx);
            g_clients[id] = cs;
            if (g_active_id < 0) g_active_id = id;
        }

        safe_print("[server] Client #" + std::to_string(id) + " connected from " + cs->peer + "\n> ");

        cs->reader = std::thread(client_reader, cs);
        cs->reader.detach();
    }

    close(sockfd);

    std::vector<std::shared_ptr<ClientSession>> snapshot;
    {
        std::lock_guard<std::mutex> lk(g_clients_mtx);
        for (auto& [id, cs] : g_clients) snapshot.push_back(cs);
        g_clients.clear();
    }
    for (auto& cs : snapshot) close_session(cs);

    if (console_thr.joinable()) console_thr.join();

    SSL_CTX_free(ctx);
    cleanup_openssl();

    safe_print("\n[server] Shutdown complete.\n");
    return 0;
}
