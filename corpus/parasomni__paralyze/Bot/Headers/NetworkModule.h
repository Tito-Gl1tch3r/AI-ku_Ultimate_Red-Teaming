#pragma once
#include "BotLogger.h"
#include "IModule.h"
#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/beast/http.hpp>
#include <nlohmann/json.hpp>

class NetworkModule {
private:
  boost::asio::io_context m_io_context;
  boost::asio::ip::tcp::resolver m_resolver;
  boost::asio::ssl::context m_ssl_context;
  boost::asio::ssl::stream<boost::asio::ip::tcp::socket> m_socket;
  std::string m_init_token;
  std::string m_jwt_file;
  int m_server_port;
  std::string m_server_address;

protected:
  std::string m_cert_chain_file;
  std::string m_ca_cert_file;
  std::string m_private_key_file;
  static std::map<std::string, std::string> m_api_endpoints;
  static std::string m_jwt;

public:
  NetworkModule(const std::string &server_address, int server_port);
  ~NetworkModule();

  // getters
  const std::string &get_init_token() const;
  const std::string &get_server_address() const;
  const std::string &get_jwt_file() const;
  const std::string &get_jwt() const;
  int get_server_port() const;
  boost::asio::io_context &get_io_context();
  boost::asio::ip::tcp::resolver &get_resolver();
  boost::asio::ssl::stream<boost::asio::ip::tcp::socket> &get_socket();
  const std::string &get_cert_file() const;
  std::string get_jwt_from_file();

  // setters
  void set_server_address(const std::string &server_address);
  void set_server_port(int server_port);
  void set_jwt_file(const std::string &jwt_file);
  void set_jwt(const std::string &jwt);
  void update_jwt_file(const std::string &jwt_file);
  void update_server_address_port(const std::string &server_address,
                                  int server_port);
  static void set_api_endpoints(const nlohmann::json &api_endpoints);
  void write_jwt_to_file(const std::vector<std::byte> &jwt);
  void update_ca_cert_file(const std::string &ca_cert_file);

  // authentication
  bool receive_jwt();

  // networking
  std::string current_time_stamp();
  void reinitialize_socket();
  void close_socket();
  bool connect_to_server();
  bool send_https_get_request(const std::string &target,
                              std::vector<std::byte> &response);
  bool send_https_post_request(const std::string &target,
                               const std::vector<std::byte> &data,
                               std::vector<std::byte> &response,
                               const std::string &content_type);
  void extract_https_response(
      boost::beast::http::response<boost::beast::http::dynamic_body> &res,
      std::vector<std::byte> &response);
};