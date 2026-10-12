#include "ConfigWriter.h"
#include "IfcEssentials.h"
#include <iostream>

void print_collection_string() {
  std::string log_collection = "";
  while (true) {
    if (log_collection !=
        IfcLogger::getInstance().get_log_collection_string()) {
      log_collection = IfcLogger::getInstance().get_log_collection_string();
      std::cout << log_collection << std::flush;
      std::cout << "\r";
    }
    // std::this_thread::sleep_for(std::chrono::milliseconds(500));
  }
}

int main() {
  std::cout << "Starting config writer..." << std::endl;
  std::cout << "Setting log level to TRACE..." << std::endl;
  IfcLogger::getInstance().set_log_level(LogLevel::TRACE);
  std::cout << "Starting log printer..." << std::endl;
  std::thread log_printer(print_collection_string);
  log_printer.detach();

  std::cout << "Reading config writer config file..." << std::endl;
  nlohmann::json config = IfcEssentials::getInstance().get_json_dump_from_file(
      "../../configs/config_writer.json");
  nlohmann::json sleep_config =
      IfcEssentials::getInstance().get_json_dump_from_file(
          "../../configs/sleep_instructions.json");
  nlohmann::json test_bot_config =
      IfcEssentials::getInstance().get_json_dump_from_file(
          "../../configs/test_bot.json");
  nlohmann::json init_instructions =
      IfcEssentials::getInstance().get_json_dump_from_file(
          "../../configs/init_instructions.json");
  nlohmann::json dos_instructions =
      IfcEssentials::getInstance().get_json_dump_from_file(
          "../../configs/dos_instructions.json");
  nlohmann::json proxy_instructions =
      IfcEssentials::getInstance().get_json_dump_from_file(
          "../../configs/proxy_instructions.json");
  nlohmann::json suite_server_instructions =
      IfcEssentials::getInstance().get_json_dump_from_file(
          "../../configs/suite_server_instructions.json");

  std::cout << "Creating config writer..." << std::endl;
  ConfigWriter *config_writer = new ConfigWriter(config);
  std::cout << "Writing config to database..." << std::endl;
  config_writer->write_config_to_db(config["bot_instructions"]["name"],
                                    config["bot_instructions"]["collection"],
                                    "sleep_instructions", sleep_config);
  config_writer->write_config_to_db(
      config["bot_configs"]["name"], config["bot_configs"]["collection"],
      "c90d11b2-4c9f-4966-9fbc-f54136e55d30", test_bot_config);

  config_writer->write_config_to_db(config["bot_instructions"]["name"],
                                    config["bot_instructions"]["collection"],
                                    "init_instructions", init_instructions);

  config_writer->write_config_to_db(config["bot_instructions"]["name"],
                                    config["bot_instructions"]["collection"],
                                    "dos_instructions", dos_instructions);
  
  
  config_writer->write_config_to_db(config["bot_instructions"]["name"],
                                    config["bot_instructions"]["collection"],
                                    "proxy_instructions", proxy_instructions);       
                                    
  config_writer->write_config_to_db(config["bot_instructions"]["name"],
                                    config["bot_instructions"]["collection"],
                                    "suite_server_instructions", suite_server_instructions);                       

  std::cout << "Deleting config writer..." << std::endl;
  delete config_writer;
}