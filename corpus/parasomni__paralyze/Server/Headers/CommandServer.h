#pragma once
#include "Authenticator.h"
#include "BaseServer.h"
#include <boost/asio.hpp>
#include <memory>
#include <nlohmann/json.hpp>
#include <string>
#include <thread>
#include <utility>
#include <vector>

class CommandServer : public BaseServer {
private:
  boost::asio::io_context::work m_work;
  std::vector<std::shared_ptr<boost::asio::io_context>> m_io_context;
  std::vector<std::thread> m_threads;
  std::unique_ptr<boost::asio::ip::tcp::acceptor> m_acceptor;
  std::unique_ptr<boost::asio::ip::tcp::socket> m_log_socket;
  std::string m_tool_suites_file;
  std::string m_bot_data_path;
  std::string m_config_file;
  Authenticator *m_authenticator;

public:
  CommandServer(const std::string &config_file);
  ~CommandServer();
  void start_server() override;
  void react_to_config_update() override;
  void do_accept() override;
  void handle_client(
      std::shared_ptr<boost::asio::ip::tcp::socket> client_socket) override;
  bool send_tool(nlohmann::json tool, int bot_id,
                 std::shared_ptr<boost::asio::ip::tcp::socket> client_socket);
  bool send_update_instructions();
  bool send_updates();
  void authenticate_bot();
};