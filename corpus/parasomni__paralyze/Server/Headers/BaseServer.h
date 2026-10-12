#pragma once
#include "BaseLogger.h"
#include "Essentials.h"
#include <boost/asio.hpp>
#include <memory>
#include <string>

class BaseServer {
private:
  std::string m_server_address;
  int m_server_port;
  std::string m_log_server_address;
  int m_log_server_port;

public:
  BaseServer(const std::string &server_address, int server_port,
             const std::string &logger_address, int logger_port);
  ~BaseServer();

  // getters
  const std::string &get_log_server_address() const;
  int get_log_server_port() const;
  const std::string &get_server_address() const;
  int get_server_port() const;

  // setters
  void set_log_server_address(const std::string &log_server_address);
  void set_log_server_port(int log_server_port);
  void set_server_address(const std::string &server_address);
  void set_server_port(int server_port);

  // keys
  std::unique_ptr<EVP_PKEY, decltype(&EVP_PKEY_free)>
  loadPrivateKey(const std::string &pemFilePath);

  // server
  virtual void react_to_config_update(const nlohmann::json &config) = 0;
  virtual void start_accept() = 0;
  virtual void start_server() = 0;
};