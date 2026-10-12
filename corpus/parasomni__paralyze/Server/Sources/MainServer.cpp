#include "ConfigModule.h"
#include "CCServer.h"
#include "DBController.h"
#include <chrono>
#include <iostream>
#include <thread>

void print_collection_string() {
  std::string log_collection = "";
  while (true) {
    if (log_collection !=
        BaseLogger::getInstance().get_log_collection_string()) {
      log_collection = BaseLogger::getInstance().get_log_collection_string();
      std::cout << log_collection << std::flush;
      std::cout << "\r";
    }
    // std::this_thread::sleep_for(std::chrono::milliseconds(500));
  }
}

int main() {
  std::cout << "Starting control server..." << std::endl;
  std::cout << "Setting log level to TRACE..." << std::endl;
  BaseLogger::getInstance().set_log_level(LogLevel::TRACE);
  std::cout << "Starting log printer..." << std::endl;
  std::thread log_printer(print_collection_string);
  log_printer.detach();

  std::cout << "Initializing config module..." << std::endl;
  nlohmann::json config_module_dump =
      Essentials::getInstance().get_json_dump_from_file(
          "../../configs/config_module.json");
  ConfigModule::getInstance().init_config_module(config_module_dump);
  std::cout << "Init token: " << ConfigModule::getInstance().get_init_token()
            << std::endl;

  std::cout << "Initializing DB controller..." << std::endl;
  DBController::getInstance().init_controller(
      "../../configs/db_controller.conf");

  std::cout << "Reading config file..." << std::endl;
  nlohmann::json config_dump;
  config_dump = Essentials::getInstance().get_json_dump_from_file(
      "../../configs/control_server.json");

  std::cout << "Creating control server..." << std::endl;
  CCServer control_server(config_dump);
  std::cout << "Starting control server..." << std::endl;
  try {
    control_server.start_server();
  } catch (const std::exception &e) {
    std::cout << BaseLogger::getInstance().get_log_collection_string()
              << std::endl;
  }
}