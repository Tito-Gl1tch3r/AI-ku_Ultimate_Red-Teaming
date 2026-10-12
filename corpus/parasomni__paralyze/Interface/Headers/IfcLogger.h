#pragma once
#include "IfcInstance.h"
#include "LogLevel.h"
#include <ctime>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <vector>

class IfcLogger {
private:
  std::mutex m_log_mutex;
  std::string m_log_collection = "";
  LogLevel m_log_level = LogLevel::INFO;
  IfcLogger() = default;
  IfcLogger(const IfcLogger &) = delete;
  IfcLogger &operator=(const IfcLogger &) = delete;

public:
  static IfcLogger &getInstance() {
    static IfcLogger instance;
    return instance;
  }

  void set_log_level(LogLevel level) { m_log_level = level; }

  void save_log(const std::string &message, LogLevel level,
                IfcInstance instance) {
    std::lock_guard<std::mutex> lock(m_log_mutex);
    if (level >= m_log_level) {
      m_log_collection += "[" + get_current_time_as_string() + "] " + "--" +
                          "[" + get_iface_instance_as_string(instance) + "]" +
                          "[" + getLogLevelString(level) + "]" + ": " +
                          message + "\n";
    }
  }

  void save_exception(const std::exception &e, LogLevel level,
                      IfcInstance instance) {
    save_log(std::string("Exception caught: ") + e.what(), level, instance);
  }

  std::vector<std::byte> get_log_collection_bytes() {
    std::vector<std::byte> bytes;
    for (char c : m_log_collection) {
      bytes.push_back(static_cast<std::byte>(c));
    }
    return bytes;
  }

  std::string &get_log_collection_string() { return m_log_collection; }

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
  std::string get_iface_instance_as_string(IfcInstance instance) {
    switch (instance) {
    case IfcInstance::CFGWRITER:
      return "CFGWRITER";
    case IfcInstance::LOGGER:
      return "LOGGER";
    }
  }
};