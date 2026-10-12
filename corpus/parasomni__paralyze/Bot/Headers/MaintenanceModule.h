#pragma once
#include "NetworkModule.h"
#include <nlohmann/json.hpp>

class MaintenanceModule : public NetworkModule {
public:
  MaintenanceModule(const std::string &server_address, int server_port);
  ~MaintenanceModule();
  std::string get_module_name() const override;
  void fetch_updates();
  void evaluate_instructions(const nlohmann::json &instructions);
  void add_module(IModule *module);
  void update_connection_config(const std::string &server_address,
                                int server_port);
  void update_cert_config(const std::string &cert_file);
  void install_updates();
  void execute_module(const nlohmann::json &instructions);

private:
  boost::asio::ip::tcp::socket m_socket;
  std::vector<IModule *> modules;
};