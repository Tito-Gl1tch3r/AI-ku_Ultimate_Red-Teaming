#include "ConfigModule.h"
#include "BaseLogger.h"
#include <bsoncxx/json.hpp>
#include <iostream>

ConfigModule ConfigModule::instance;

void ConfigModule::init_config_module(const nlohmann::json &config) {
  m_config = config;
  m_client = mongocxx::client{
      mongocxx::uri{m_config["general"]["uri"].get<std::string>()}};
}

nlohmann::json ConfigModule::get_bot_config(const std::string &uuid) {
  try {
    mongocxx::database db =
        m_client[m_config["bot_configs"]["name"].get<std::string>()];
    mongocxx::collection collection =
        db[m_config["bot_configs"]["collection"].get<std::string>()];
    bsoncxx::builder::basic::document filter_builder;
    filter_builder.append(bsoncxx::builder::basic::kvp("uuid", uuid));
    bsoncxx::document::value filter = filter_builder.extract();

    mongocxx::cursor cursor = collection.find(filter.view());
    nlohmann::json config;
    for (auto &&doc : cursor) {
      std::string json_str = bsoncxx::to_json(doc);
      nlohmann::json json_doc = nlohmann::json::parse(json_str);
      json_doc.erase("uuid");
      config = json_doc;
    }
    return config;
  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_log("Failed to get bot instructions",
                                       LogLevel::ERROR, ServerInstance::CONFIG);
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONFIG);
    return nlohmann::json();
  }
}

nlohmann::json
ConfigModule::get_instruction(const std::string &instruction_name) {
  try {
    mongocxx::database db =
        m_client[m_config["bot_instructions"]["name"].get<std::string>()];
    mongocxx::collection collection =
        db[m_config["bot_instructions"]["collection"].get<std::string>()];
    bsoncxx::builder::basic::document filter_builder;
    filter_builder.append(
        bsoncxx::builder::basic::kvp("config_name", instruction_name));
    bsoncxx::document::value filter = filter_builder.extract();

    mongocxx::cursor cursor = collection.find(filter.view());
    nlohmann::json instruction;
    for (auto &&doc : cursor) {
      std::string json_str = bsoncxx::to_json(doc);
      nlohmann::json json_doc = nlohmann::json::parse(json_str);
      json_doc.erase("_id");
      json_doc.erase("config_name");
      instruction = json_doc;
    }
    return instruction;
  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_log("Failed to get instruction",
                                       LogLevel::ERROR, ServerInstance::CONFIG);
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONFIG);
    return nlohmann::json();
  }
}

std::string ConfigModule::get_init_token() {
  return m_config["general"]["init_token"];
}

void ConfigModule::set_bot_instructions(const std::string &uuid,
                                        const nlohmann::json &instructions) {
  try {
    BaseLogger::getInstance().save_log("Setting bot instructions for " + uuid,
                                       LogLevel::INFO, ServerInstance::CONFIG);
    mongocxx::database db =
        m_client[m_config["bot_configs"]["name"].get<std::string>()];
    mongocxx::collection collection =
        db[m_config["bot_configs"]["collection"].get<std::string>()];

    bsoncxx::builder::basic::document filter_builder;

    filter_builder.append(bsoncxx::builder::basic::kvp("_id", uuid));
    filter_builder.append(bsoncxx::builder::basic::kvp("config_name", uuid));
    bsoncxx::document::value filter = filter_builder.extract();

    bsoncxx::builder::basic::document update_builder;
    update_builder.append(bsoncxx::builder::basic::kvp(
        "$set", bsoncxx::from_json(instructions.dump())));

    collection.update_one(filter.view(), update_builder.view(),
                          mongocxx::options::update().upsert(true));
  } catch (const std::exception &e) {
    BaseLogger::getInstance().save_log("Failed to set bot instructions",
                                       LogLevel::ERROR, ServerInstance::CONFIG);
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::CONFIG);
  }
}

void ConfigModule::set_init_token(const std::string &token) {
  m_config["general"]["init_token"] = token;
}