#pragma once
#include "BotEssentials.h"
#include "BotModules.h"
#include "LogLevel.h"
#include <ctime>
#include <sstream>
#include <string>
#include <vector>

class BotLogger {
private:
  std::string m_log_collection = "";
  LogLevel m_log_level = LogLevel::INFO;
  // BotModules m_logged_module;
  BotLogger() = default;
  BotLogger(const BotLogger &) = delete;
  BotLogger &operator=(const BotLogger &) = delete;

public:
  static BotLogger &getInstance() {
    static BotLogger instance;
    return instance;
  }

  void set_log_level(LogLevel level) { m_log_level = level; }

  void save_log(const std::string &message, LogLevel level,
                BotModules logged_module) {
    if (level >= m_log_level) {
      m_log_collection += "[" + get_current_time_as_string() + "] " + "--" +
                          "[" + logged_module_to_string(logged_module) + "]" +
                          "[" + getLogLevelString(level) + "]" + ": " +
                          message + "\n";
    }
  }

  void save_exception(const std::exception &e, LogLevel level,
                      BotModules logged_module) {
    save_log(std::string("Exception caught: ") + e.what(), level,
             logged_module);
  }

  std::vector<std::byte> get_log_collection_bytes() {
    std::vector<std::byte> bytes;
    for (char c : m_log_collection) {
      bytes.push_back(static_cast<std::byte>(c));
    }
    return bytes;
  }

  const std::string &get_log_collection_string() const {
    return m_log_collection;
  }

private:
  const std::string get_current_time_as_string() {
    std::time_t current_time = std::time(nullptr);
    std::tm *local_time = std::localtime(&current_time);

    char buffer[100];
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", local_time);

    std::string time_str(buffer);
    return time_str;
  }

  std::string getLogLevelString(LogLevel level) {
    switch (level) {
    case LogLevel::TRACE:
      return "TRACE";
    case LogLevel::DEBUG:
      return "DEBUG";
    case LogLevel::INFO:
      return "INFO";
    case LogLevel::WARNING:
      return "WARNING";
    case LogLevel::ERROR:
      return "ERROR";
    case LogLevel::FATAL:
      return "FATAL";
    default:
      return "UNKNOWN";
    }
  }

  std::string logged_module_to_string(BotModules module) {
    switch (module) {
    case BotModules::MAINTENANCE:
      return "MAINTENANCE";
    case BotModules::PROXY:
      return "PROXY";
    case BotModules::EXFILTRATION:
      return "EXFILTRATION";
    case BotModules::LOADER:
      return "LOADER";
    case BotModules::CONTROL:
      return "CONTROL";
    case BotModules::DOS:
      return "DOS";
    case BotModules::NUKE:
      return "NUKE";
    case BotModules::AUTHENTICATOR:
      return "AUTHENTICATOR";
    case BotModules::CRYPT:
      return "CRYPT";
    case BotModules::NETWORK:
      return "NETWORK";
    default:
      return "UNKNOWN";
    }
  }
};