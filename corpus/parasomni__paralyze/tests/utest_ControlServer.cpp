#define BOOST_TEST_MODULE ControlServerTest
#include "ControlServer.h"
#include <boost/asio.hpp>
#include <boost/test/included/unit_test.hpp>
#include <nlohmann/json.hpp>

struct ControlServerFixture {
  ControlServerFixture()
      : config_file({{"certificate_chain", "path/to/cert_chain.pem"},
                     {"private_key", "path/to/private_key.pem"},
                     {"dh_file", "path/to/dh_file.pem"},
                     {"instructions",
                      {{"dos", "dos_instruction"},
                       {"init", "init_instruction"},
                       {"update", "update_instruction"},
                       {"sleep", "sleep_instruction"},
                       {"tool_suites", "tool_suites"}}},
                     {"general",
                      {{"server", {{"address", "127.0.0.1"}, {"port", "8080"}}},
                       {"logger", {{"address", "127.0.0.1"}, {"port", "8081"}}},
                       {"io_context_threads", "2"}}},
                     {"networking",
                      {{"ssl",
                        {{"certificate_chain", "path/to/cert_chain.pem"},
                         {"private_key", "path/to/private_key.pem"},
                         {"public_key", "path/to/public_key.pem"},
                         {"dh_file", "path/to/dh_file.pem"}}},
                       {"http",
                        {{"server_header", "TestServer"},
                         {"api_endpoints",
                          {{"/api/settings", "settings_endpoint"},
                           {"/api/auth/jwt", "auth_endpoint"}}}}}}}}),
        server(config_file) {}

  nlohmann::json config_file;
  ControlServer server;
};

BOOST_FIXTURE_TEST_SUITE(ControlServerTestSuite, ControlServerFixture)

BOOST_AUTO_TEST_CASE(test_start_accept) {
  BOOST_CHECK_NO_THROW(server.start_accept());
}

BOOST_AUTO_TEST_SUITE_END()