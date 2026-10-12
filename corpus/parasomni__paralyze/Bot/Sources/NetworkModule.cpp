#include "NetworkModule.h"
#include "NetworkEssentials.h"
#include <boost/beast/core.hpp>
#include <boost/beast/version.hpp>
#include <iostream>
#include <openssl/x509.h>
#include <openssl/x509v3.h>

NetworkModule::NetworkModule(const std::string &server_address, int server_port)
    : m_resolver(m_io_context),
      m_ssl_context(boost::asio::ssl::context::tlsv12_client),
      m_socket(m_io_context, m_ssl_context), m_init_token("feel_nothing"),
      m_jwt_file("jwt_file"), m_server_port(server_port),
      m_server_address(server_address) {
  m_ca_cert_file = "/path/to/paralyze/docs/installation/pki/servers/server1/server_cert.crt";
  m_cert_chain_file = "/path/to/paralyze/docs/installation/pki/clients/server1/client1/cs.chain.crt";
  m_private_key_file = "/path/to/paralyze/docs/installation/pki/clients/server1/client1/cs_private.key";

  m_ssl_context.set_verify_mode(boost::asio::ssl::verify_peer);
  m_ssl_context.use_certificate_chain_file(m_cert_chain_file);
  m_ssl_context.use_private_key_file(m_private_key_file,
                                     boost::asio::ssl::context::pem);
  m_ssl_context.load_verify_file(m_ca_cert_file);
  m_ssl_context.set_verify_callback(
      [](bool preverified, boost::asio::ssl::verify_context &ctx) {
        return preverified;
      });
}

NetworkModule::~NetworkModule() {}

std::map<std::string, std::string> NetworkModule::m_api_endpoints;
std::string NetworkModule::m_jwt = "feel_nothing";

const std::string &NetworkModule::get_server_address() const {
  return m_server_address;
}

int NetworkModule::get_server_port() const { return m_server_port; }

void NetworkModule::set_server_address(const std::string &server_address) {
  m_server_address = server_address;
}

void NetworkModule::set_server_port(int server_port) {
  m_server_port = server_port;
}

void NetworkModule::update_jwt_file(const std::string &jwt_file) {
  m_jwt_file = jwt_file;
}

void NetworkModule::set_jwt(const std::string &jwt) { m_jwt = jwt; }

void NetworkModule::update_ca_cert_file(const std::string &ca_cert_file) {
  m_ca_cert_file = ca_cert_file;
  m_ssl_context.load_verify_file(m_ca_cert_file);
}

const std::string &NetworkModule::get_jwt_file() const { return m_jwt_file; }

const std::string &NetworkModule::get_init_token() const {
  return m_init_token;
}

void NetworkModule::set_jwt_file(const std::string &jwt_file) {
  m_jwt_file = jwt_file;
}

void NetworkModule::set_api_endpoints(const nlohmann::json &api_endpoints) {
  BotLogger::getInstance().save_log("Setting API endpoints...", LogLevel::TRACE,
                                    BotModules::NETWORK);
  try {
    if (api_endpoints.contains("instructions") &&
        api_endpoints["instructions"].is_string()) {
      m_api_endpoints["instructions"] = api_endpoints["instructions"];
    } else {
      BotLogger::getInstance().save_log("Failed to set instructions endpoint.",
                                        LogLevel::ERROR, BotModules::NETWORK);
    }
    if (api_endpoints.contains("jwt") && api_endpoints["jwt"].is_string()) {
      m_api_endpoints["jwt"] = api_endpoints["jwt"];
    } else {
      BotLogger::getInstance().save_log("Failed to set jwt endpoint.",
                                        LogLevel::ERROR, BotModules::NETWORK);
    }
    if (api_endpoints.contains("tool_suites") &&
        api_endpoints["tool_suites"].is_string()) {
      m_api_endpoints["tool_suites"] = api_endpoints["tool_suites"];
    } else {
      BotLogger::getInstance().save_log("Failed to set tool suites endpoint.",
                                        LogLevel::ERROR, BotModules::NETWORK);
    }
    BotLogger::getInstance().save_log("API endpoints set.", LogLevel::INFO,
                                      BotModules::NETWORK);
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to set API endpoints.",
                                      LogLevel::ERROR, BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
  }
}

// networking
boost::asio::io_context &NetworkModule::get_io_context() {
  return m_io_context;
}

boost::asio::ip::tcp::resolver &NetworkModule::get_resolver() {
  return m_resolver;
}

boost::asio::ssl::stream<boost::asio::ip::tcp::socket> &
NetworkModule::get_socket() {
  return m_socket;
}

const std::string &NetworkModule::get_cert_file() const { return m_jwt_file; }

const std::string &NetworkModule::get_jwt() const { return m_jwt; }

std::string NetworkModule::current_time_stamp() {
  time_t now = time(0);
  tm *ltm = localtime(&now);
  std::string time_stamp =
      std::to_string(1900 + ltm->tm_year) + "-" +
      std::to_string(1 + ltm->tm_mon) + "-" + std::to_string(ltm->tm_mday) +
      "T" + std::to_string(ltm->tm_hour) + ":" + std::to_string(ltm->tm_min) +
      ":" + std::to_string(ltm->tm_sec);
  return time_stamp;
}

void NetworkModule::reinitialize_socket() {
  m_socket = boost::asio::ssl::stream<boost::asio::ip::tcp::socket>(
      m_io_context, m_ssl_context);
}

void NetworkModule::close_socket() {
  boost::system::error_code ec;
  m_socket.shutdown(ec);
  if (ec) {
    BotLogger::getInstance().save_log("Failed to shutdown SSL stream: " +
                                          ec.message(),
                                      LogLevel::ERROR, BotModules::NETWORK);
  }

  m_socket.lowest_layer().close(ec);
  if (ec) {
    BotLogger::getInstance().save_log("Failed to close socket: " + ec.message(),
                                      LogLevel::ERROR, BotModules::NETWORK);
  }
}

bool NetworkModule::connect_to_server() {
  try {
    if (!m_socket.lowest_layer().is_open()) {
      reinitialize_socket();
    }
    BotLogger::getInstance().save_log("Initializing tls connection...",
                                      LogLevel::TRACE, BotModules::NETWORK);
    boost::asio::ip::tcp::resolver::query query(m_server_address,
                                                std::to_string(m_server_port));
    boost::asio::ip::tcp::resolver::iterator endpoint_iterator =
        m_resolver.resolve(query);

    boost::asio::connect(m_socket.lowest_layer(), endpoint_iterator);

    m_socket.handshake(boost::asio::ssl::stream_base::client);

    BotLogger::getInstance().save_log("Connected to server.", LogLevel::INFO,
                                      BotModules::NETWORK);

    return true;

  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to connect to server.",
                                      LogLevel::ERROR, BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
    return false;
  }
}

bool NetworkModule::send_https_get_request(const std::string &target,
                                           std::vector<std::byte> &response) {
  try {
    if (!connect_to_server()) {
      return false;
    }

    boost::beast::http::request<boost::beast::http::string_body> req{
        boost::beast::http::verb::get, target, 11};
    req.set(boost::beast::http::field::host, m_server_address);
    req.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);
    req.set(boost::beast::http::field::authorization, "Bearer " + m_jwt);
    req.set("X-Timestamp", current_time_stamp());

    std::ostringstream request_stream;
    request_stream << req;
    std::string request_str = request_stream.str();
    BotLogger::getInstance().save_log("HTTP Request: \r\n" + request_str,
                                      LogLevel::TRACE, BotModules::NETWORK);

    boost::beast::flat_buffer buffer;
    boost::beast::http::response<boost::beast::http::dynamic_body> res;

    BotLogger::getInstance().save_log("Writing to socket...", LogLevel::TRACE,
                                      BotModules::NETWORK);
    try {
      boost::beast::http::write(m_socket, req);
    } catch (const std::exception &e) {
      BotLogger::getInstance().save_log("Failed to write to socket.",
                                        LogLevel::ERROR, BotModules::NETWORK);
      BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                              BotModules::NETWORK);
      return false;
    }

    BotLogger::getInstance().save_log("Reading HTTPS GET response...",
                                      LogLevel::TRACE, BotModules::NETWORK);
    try {
      boost::beast::http::read(m_socket, buffer, res);
    } catch (const std::exception &e) {
      BotLogger::getInstance().save_log("Failed to read from socket.",
                                        LogLevel::ERROR, BotModules::NETWORK);
      BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                              BotModules::NETWORK);
      return false;
    }

    BotLogger::getInstance().save_log(
        "Response status: " + std::to_string(static_cast<int>(res.result())) +
            " (" + std::string(res.reason()) + ")",
        LogLevel::TRACE, BotModules::NETWORK);

    if (res.result() != boost::beast::http::status::ok) {
      BotLogger::getInstance().save_log(
          "HTTP Error: " + std::to_string(static_cast<int>(res.result())) +
              " (" + std::string(res.reason()) + ")",
          LogLevel::ERROR, BotModules::NETWORK);
      m_socket.lowest_layer().close();
      return false;
    }
    extract_https_response(res, response);

    close_socket();
    return true;
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to send HTTPS request.",
                                      LogLevel::ERROR, BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
    close_socket();
    return false;
  }
}

bool NetworkModule::send_https_post_request(const std::string &target,
                                            const std::vector<std::byte> &data,
                                            std::vector<std::byte> &response,
                                            const std::string &content_type) {
  try {
    if (!connect_to_server()) {
      return false;
    }

    std::string data_str(data.size(), '\0');
    std::transform(data.begin(), data.end(), data_str.begin(),
                   [](std::byte b) { return static_cast<char>(b); });

    boost::beast::http::request<boost::beast::http::string_body> req{
        boost::beast::http::verb::post, target, 11};
    req.set(boost::beast::http::field::host, m_server_address);
    req.set(boost::beast::http::field::user_agent, BOOST_BEAST_VERSION_STRING);
    req.set(boost::beast::http::field::content_type, content_type);
    req.set(boost::beast::http::field::authorization, "Bearer " + m_jwt);
    req.set("X-Timestamp", current_time_stamp());
    req.body() = data_str;
    req.prepare_payload();

    // Convert the request to a string for logging
    std::ostringstream request_stream;
    request_stream << req;
    std::string request_str = request_stream.str();
    BotLogger::getInstance().save_log("HTTP Request: \r\n" + request_str,
                                      LogLevel::TRACE, BotModules::NETWORK);

    boost::beast::flat_buffer buffer;
    boost::beast::http::response<boost::beast::http::dynamic_body> res;

    BotLogger::getInstance().save_log("Sending HTTPS POST request...",
                                      LogLevel::TRACE, BotModules::NETWORK);
    boost::beast::http::write(m_socket, req);

    BotLogger::getInstance().save_log("Reading HTTPS POST response...",
                                      LogLevel::TRACE, BotModules::NETWORK);
    boost::beast::http::read(m_socket, buffer, res);

    if (res.result() != boost::beast::http::status::ok) {
      BotLogger::getInstance().save_log("Failed to send HTTPS POST request.",
                                        LogLevel::ERROR, BotModules::NETWORK);
      close_socket();
      return false;
    }

    extract_https_response(res, response);

    close_socket();
    return true;
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to send HTTPS POST request.",
                                      LogLevel::ERROR, BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
    close_socket();
    return false;
  }
}

void NetworkModule::extract_https_response(
    boost::beast::http::response<boost::beast::http::dynamic_body> &res,
    std::vector<std::byte> &response) {
  try {
    std::string response_str =
        boost::beast::buffers_to_string(res.body().data());
    response.assign(reinterpret_cast<const std::byte *>(response_str.data()),
                    reinterpret_cast<const std::byte *>(response_str.data() +
                                                        response_str.size()));
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to extract HTTPS response.",
                                      LogLevel::ERROR, BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
  }
}

bool NetworkModule::receive_jwt() {
  try {
    std::vector<std::byte> response;
    if (!send_https_post_request(
            m_api_endpoints["jwt"],
            BotEssentials::getInstance().string_to_bytes(m_init_token),
            response, "application/json")) {
      return false;
    }
    auto json_response = nlohmann::json::parse(response);
    if (json_response.contains("jwt")) {
      std::string jwt = json_response["jwt"];
      set_jwt(jwt);
      write_jwt_to_file(BotEssentials::getInstance().string_to_bytes(jwt));
      return true;
    } else {
      BotLogger::getInstance().save_log("JWT not found in response.",
                                        LogLevel::ERROR, BotModules::NETWORK);
      return false;
    }
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to receive JWT.", LogLevel::ERROR,
                                      BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
    return false;
  }
}

void NetworkModule::write_jwt_to_file(const std::vector<std::byte> &jwt) {
  try {
    BotLogger::getInstance().save_log("Writing JWT to file...", LogLevel::TRACE,
                                      BotModules::NETWORK);
    std::vector<std::byte> encr_jwt =
        BotEssentials::getInstance().string_to_bytes(m_jwt);
    // BotEssentials::getInstance().encrypt(jwt, m_init_token);
    BotEssentials::getInstance().write_to_file(m_jwt_file, encr_jwt);
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to write JWT to file.",
                                      LogLevel::ERROR, BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
  }
}

std::string NetworkModule::get_jwt_from_file() {
  try {
    BotLogger::getInstance().save_log("Reading JWT from file...",
                                      LogLevel::TRACE, BotModules::NETWORK);
    std::vector<std::byte> encr_jwt =
        BotEssentials::getInstance().read_from_file(m_jwt_file);
    // BotEssentials::getInstance().decrypt(encr_jwt);
    std::string decrypted_jwt =
        BotEssentials::getInstance().bytes_to_string(encr_jwt);

    BotLogger::getInstance().save_log("JWT read from file: " + decrypted_jwt,
                                      LogLevel::INFO, BotModules::NETWORK);
    return decrypted_jwt;
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to read JWT from file.",
                                      LogLevel::ERROR, BotModules::NETWORK);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::NETWORK);
    return "";
  }
}