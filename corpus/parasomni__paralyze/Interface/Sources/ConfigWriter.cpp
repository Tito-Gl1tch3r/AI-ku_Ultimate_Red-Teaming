#include "ConfigWriter.h"
#include <bsoncxx/json.hpp>

ConfigWriter::ConfigWriter(const nlohmann::json &config)
    : m_instance{},
      m_client{mongocxx::uri{config["general"]["uri"].get<std::string>()}},
      m_config{config} {}

void ConfigWriter::react_to_config_update(const nlohmann::json &config) {
  try {
    m_config = config;
    m_client = mongocxx::client{
        mongocxx::uri{m_config["general"]["uri"].get<std::string>()}};
    IfcLogger::getInstance().save_log("ConfigWriter updated", LogLevel::INFO,
                                      IfcInstance::CFGWRITER);
  } catch (const std::exception &e) {
    IfcLogger::getInstance().save_log("Failed to update ConfigWriter",
                                      LogLevel::ERROR, IfcInstance::CFGWRITER);
    IfcLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            IfcInstance::CFGWRITER);
  }
}

ConfigWriter::~ConfigWriter() {}

void ConfigWriter::write_config_to_db(const std::string &db_name,
                                      const std::string &collection_name,
                                      const std::string &config_name,
                                      const nlohmann::json &config) {
  IfcLogger::getInstance().save_log("Writing config to database",
                                    LogLevel::TRACE, IfcInstance::CFGWRITER);
  try {
    mongocxx::database db = m_client[db_name];
    mongocxx::collection collection = db[collection_name];

    bsoncxx::builder::basic::document filter_builder;
    filter_builder.append(
        bsoncxx::builder::basic::kvp("config_name", config_name));
    bsoncxx::document::value filter = filter_builder.extract();

    bsoncxx::builder::basic::document update_builder;
    update_builder.append(bsoncxx::builder::basic::kvp(
        "$set", bsoncxx::from_json(config.dump())));

    collection.update_one(filter.view(), update_builder.view(),
                          mongocxx::options::update().upsert(true));
    IfcLogger::getInstance().save_log("Config written to database",
                                      LogLevel::TRACE, IfcInstance::CFGWRITER);
  } catch (const std::exception &e) {
    IfcLogger::getInstance().save_log("Failed to write config to database",
                                      LogLevel::ERROR, IfcInstance::CFGWRITER);
    IfcLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                            IfcInstance::CFGWRITER);
  }
}
