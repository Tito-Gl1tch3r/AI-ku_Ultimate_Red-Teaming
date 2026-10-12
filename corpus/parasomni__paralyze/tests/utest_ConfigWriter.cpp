#include "ConfigWriter.h"
#include "MongoDBFixture.h"
#include <boost/test/unit_test.hpp>
#include <bsoncxx/json.hpp>
#include <iostream>
#include <mongocxx/collection.hpp>
#include <mongocxx/database.hpp>

BOOST_FIXTURE_TEST_SUITE(ConfigWriterTestSuite, MongoDBFixture)

BOOST_AUTO_TEST_CASE(test_write_config_to_db) {
  BOOST_TEST_MESSAGE("Testing write_config_to_db");
  // Initialize ConfigWriter
  nlohmann::json config = IfcEssentials::getInstance().get_json_dump_from_file(
      "../../configs/config_writer.json");
  ConfigWriter writer(config);
  BOOST_TEST_MESSAGE("Initialized ConfigWriter");
  // Create a sample config
  nlohmann::json dos = IfcEssentials::getInstance().get_json_dump_from_file(
      "../../configs/dos_instructions.json");
  BOOST_TEST_MESSAGE("Created sample config");
  // Write config to database
  writer.write_config_to_db(config["bot_instructions"]["name"],
                            config["bot_instructions"]["collection"],
                            "dos_instructions", config);

  BOOST_TEST_MESSAGE("Wrote config to database");
  // Verify that the config was written to the database
  auto db = client[std::string(config["bot_instructions"]["name"])];
  auto collection = db[std::string(config["bot_instructions"]["collection"])];
  bsoncxx::builder::basic::document filter_builder;
  filter_builder.append(
      bsoncxx::builder::basic::kvp("config_name", "dos_instructions"));
  auto cursor = collection.find(filter_builder.view());

  int count = 0;
  for (auto &&doc : cursor) {
    std::string json_str = bsoncxx::to_json(doc);
    nlohmann::json result_json = nlohmann::json::parse(json_str);
    BOOST_CHECK_EQUAL(result_json["config_name"], "dos_instructions");
    BOOST_CHECK_EQUAL(result_json["module"], "dos");
    BOOST_CHECK_EQUAL(result_json["action"], "attack");
    count++;
  }

  BOOST_CHECK_EQUAL(count, 1);
  BOOST_TEST_MESSAGE(IfcLogger::getInstance().get_log_collection_string());
}

BOOST_AUTO_TEST_SUITE_END()