#define BOOST_TEST_MODULE UnitTests
#include "ConfigModule.h"
#include "MongoDBFixture.h"
#include <boost/test/included/unit_test.hpp>
#include <bsoncxx/json.hpp>
#include <mongocxx/collection.hpp>
#include <mongocxx/database.hpp>

BOOST_FIXTURE_TEST_SUITE(ConfigModuleTestSuite, MongoDBFixture)

BOOST_AUTO_TEST_CASE(test_get_bot_instructions) {
  // Initialize ConfigModule
  nlohmann::json config = Essentials::getInstance().get_json_dump_from_file(
      "../../configs/config_module.json");
  ConfigModule::getInstance().init_config_module(config);

  // Retrieve the bot instructions
  nlohmann::json retrieved_instructions =
      ConfigModule::getInstance().get_bot_instructions("dos_instructions");

  // Verify the retrieved instructions
  BOOST_CHECK_EQUAL(retrieved_instructions["module"], "dos");
  BOOST_CHECK_EQUAL(retrieved_instructions["action"], "attack");
  std::cout << "Test passed" << std::endl;
}

BOOST_AUTO_TEST_CASE(test_set_init_token) {
  // Initialize ConfigModule
  ConfigModule::getInstance().init_config_module(
      "../../configs/config_module.json");

  // Set a new init token
  std::string new_token = "new_init_token";
  ConfigModule::getInstance().set_init_token(new_token);

  // Verify the init token in the config
  nlohmann::json config = Essentials::getInstance().get_json_dump_from_file(
      "../../configs/config_module.json");
  BOOST_CHECK_EQUAL(config["general"]["init_token"], new_token);
  std::cout << "Test passed" << std::endl;
}

BOOST_AUTO_TEST_SUITE_END()