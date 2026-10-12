#include "LogSender.h"
#include "CryptSetup.h"
#include <thread>

LogSender::LogSender(const std::string &server_address, int port)
    : m_server_address(server_address), m_server_port(port),
      m_logger_socket(m_io_context) {
  boost::asio::ip::tcp::resolver resolver(m_io_context);
  boost::asio::ip::tcp::resolver::results_type endpoints =
      resolver.resolve(server_address, std::to_string(port));
  boost::asio::connect(m_logger_socket, endpoints);
}

LogSender::~LogSender() {}

const std::string &LogSender::get_server_address() const {
  return m_server_address;
}

int LogSender::get_port() const { return m_server_port; }

void LogSender::set_server_address(const std::string &server_address) {
  m_server_address = server_address;
}

void LogSender::set_server_port(int server_port) {
  m_server_port = server_port;
}

void LogSender::send_log_to_server(const std::vector<std::byte> &log_data) {
  BaseLogger::getInstance().save_log("Sending logs to server.",
                                     LogLevel::TRACE);
  try {
    BaseLogger::getInstance().save_log("Encrypting logs.", LogLevel::TRACE);
    const std::vector<std::byte> encr_log_data =
        m_crypt_stub->encrypt(log_data);
    if (Essentials::getInstance().send_data_to_server(m_logger_socket,
                                                      encr_log_data)) {
      BaseLogger::getInstance().save_log("Logs sent to server.",
                                         LogLevel::INFO);
    } else {
      BaseLogger::getInstance().save_log("Failed to send logs to server.",
                                         LogLevel::ERROR);
    }
  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::FATAL);
  }
}

void LogSender::initialize_crypt_stub(const unsigned char *key) {
  BaseLogger::getInstance().save_log("Initializing encryption stub.",
                                     LogLevel::TRACE);
  m_crypt_stub = new EncryptionStub(key);
}

void LogSender::start_log_sender() {
  std::thread io_thread([this]() { m_io_context.run(); });
  io_thread.detach();
  if (!setup_encryption()) {
    BaseLogger::getInstance().save_log("Failed to setup encryption.",
                                       LogLevel::FATAL);
    return;
  } else {
    BaseLogger::getInstance().save_log("Encryption setup successful.",
                                       LogLevel::INFO);
  }
  send_log_to_server(BaseLogger::getInstance().get_log_collection_bytes());
  std::this_thread::sleep_for(std::chrono::seconds(3600));
}

bool LogSender::setup_encryption() {
  return CryptSetup::getInstance().setup_encryption_stub(m_logger_socket,
                                                         *m_crypt_stub, true);
}