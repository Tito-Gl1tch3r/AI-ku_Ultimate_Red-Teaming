#include "DBController.h"
#include <filesystem>
#include <fstream>
#include <iostream>

void DBController::init_controller(const std::string &config_file) {
  BaseLogger::getInstance().save_log("Initializing DB controller...",
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  read_config(config_file, m_db_config);

  // Initialize MariaDB driver
  sql::Driver *driver = sql::mariadb::get_driver_instance();
  std::string url_str = get_url();
  sql::SQLString url(url_str);
  sql::Properties properties = get_properties();
  m_connection =
      std::unique_ptr<sql::Connection>(driver->connect(url, properties));
  // Establish connection
  // Create a statement object
  m_stmt = std::unique_ptr<sql::Statement>(m_connection->createStatement());
  BaseLogger::getInstance().save_log("Initialized DB controller.",
                                     LogLevel::TRACE,
                                     ServerInstance::DBCONTROLLER);
}

void DBController::read_config(const std::string &filename,
                               std::map<std::string, std::string> &config) {
  BaseLogger::getInstance().save_log("Reading config file: " + filename,
                                     LogLevel::TRACE,
                                     ServerInstance::DBCONTROLLER);
  std::ifstream file(filename);
  if (!file.is_open()) {
    BaseLogger::getInstance().save_log(
        "Could not open config file: " + filename, LogLevel::ERROR,
        ServerInstance::DBCONTROLLER);
    return;
  }
  try {
    while (!file.eof()) {
      std::string line;
      std::getline(file, line);
      if (line.empty() || line[0] == '>') {
        continue;
      }
      auto delimiter = line.find('=');
      if (delimiter == std::string::npos) {
        BaseLogger::getInstance().save_log(
            "Invalid line in config file: " + line, LogLevel::ERROR,
            ServerInstance::DBCONTROLLER);
      }
      config[line.substr(0, delimiter)] = line.substr(delimiter + 1);
    }

  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
  }
}

std::string
DBController::generate_query(const std::map<std::string, std::string> &bot,
                             const std::string &action) {
  BaseLogger::getInstance().save_log("Generating query for " + bot.at("uuid"),
                                     LogLevel::TRACE,
                                     ServerInstance::DBCONTROLLER);
  std::string query;
  if (action == "x08b4") {
    query = "INSERT INTO bots (uuid, ip_address, port, location, status, "
            "last_seen, bot_type, token, OS) VALUES ('" +
            bot.at("uuid") + "', '" + bot.at("ip_address") + "', " +
            bot.at("port") + ", '" + bot.at("location") + "', '" +
            bot.at("status") + "', '" + bot.at("last_seen") + "', '" +
            bot.at("bot_type") + "', '" + bot.at("token") + "', '" +
            bot.at("OS") + "')";
  } else if (action == "x08c3") {
    query = "UPDATE bots SET ip_address = '" + bot.at("ip_address") +
            "', port = " + bot.at("port") + ", location = '" +
            bot.at("location") + "', status = '" + bot.at("status") +
            "', last_seen = '" + bot.at("last_seen") + "', bot_type = '" +
            bot.at("bot_type") + "', token = '" + bot.at("token") +
            "', OS = '" + bot.at("OS") + "' WHERE uuid = '" + bot.at("uuid") +
            "'";
  }
  return query;
}

std::string DBController::get_url() {
  return "jdbc:mariadb://" + m_db_config["server"] + ":" + m_db_config["port"] +
         "/" + m_db_config["database"];
}

sql::Properties DBController::get_properties() {
  sql::Properties properties(
      {{"user", m_db_config["user"]}, {"password", m_db_config["password"]}});
  if (!m_db_config.count("disable-ssl")) {
    properties["useSSL"] = "true";
    properties["requireSSL"] = "true";
    properties["sslKey"] = m_db_config["sslKey"];
    properties["sslCert"] = m_db_config["sslCert"];
    properties["sslCA"] = m_db_config["sslCA"];
  }
  return properties;
}

void DBController::insert_bot(const std::map<std::string, std::string> &bot) {
  BaseLogger::getInstance().save_log(
      "Adding bot to database: " + bot.at("uuid"), LogLevel::INFO,
      ServerInstance::DBCONTROLLER);
  try {
    std::string query = generate_query(bot, "x08b4");
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot(const std::map<std::string, std::string> &bot) {
  BaseLogger::getInstance().save_log(
      "Updating bot in database: " + bot.at("uuid"), LogLevel::INFO,
      ServerInstance::DBCONTROLLER);
  try {
    std::string query = generate_query(bot, "x08c3");
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::delete_bot(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Deleting bot from database: " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "DELETE FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot_status(const std::string &uuid,
                                     const std::string &status) {
  BaseLogger::getInstance().save_log(
      "Updating status of bot " + uuid + " to " + status, LogLevel::INFO,
      ServerInstance::DBCONTROLLER);
  try {
    std::string query =
        "UPDATE bots SET status = '" + status + "' WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot_last_seen(const std::string &uuid,
                                        const std::string &last_seen) {
  BaseLogger::getInstance().save_log(
      "Updating last seen of bot " + uuid + " to " + last_seen, LogLevel::INFO,
      ServerInstance::DBCONTROLLER);
  try {
    std::string query = "UPDATE bots SET last_seen = '" + last_seen +
                        "' WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot_location(const std::string &uuid,
                                       const std::string &location) {
  BaseLogger::getInstance().save_log(
      "Updating location of bot " + uuid + " to " + location, LogLevel::INFO,
      ServerInstance::DBCONTROLLER);
  try {
    std::string query = "UPDATE bots SET location = '" + location +
                        "' WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot_ip_address(const std::string &uuid,
                                         const std::string &ip_address) {
  BaseLogger::getInstance().save_log(
      "Updating IP address of bot " + uuid + " to " + ip_address,
      LogLevel::INFO, ServerInstance::DBCONTROLLER);
  try {
    std::string query = "UPDATE bots SET ip_address = '" + ip_address +
                        "' WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot_port(const std::string &uuid, const int port) {
  BaseLogger::getInstance().save_log(
      "Updating port of bot " + uuid + " to " + std::to_string(port),
      LogLevel::INFO, ServerInstance::DBCONTROLLER);
  try {
    std::string query = "UPDATE bots SET port = " + std::to_string(port) +
                        " WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot_token(const std::string &uuid,
                                    const std::string &token) {
  BaseLogger::getInstance().save_log(
      "Updating token of bot " + uuid + " to " + token, LogLevel::INFO,
      ServerInstance::DBCONTROLLER);
  try {
    std::string query =
        "UPDATE bots SET token = '" + token + "' WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

void DBController::update_bot_bot_type(const std::string &uuid,
                                       const std::string &bot_type) {
  BaseLogger::getInstance().save_log(
      "Updating bot type of bot " + uuid + " to " + bot_type, LogLevel::INFO,
      ServerInstance::DBCONTROLLER);
  try {
    std::string query = "UPDATE bots SET bot_type = '" + bot_type +
                        "' WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
}

std::string DBController::get_bot_type(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting bot type of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "SELECT bot_type FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("bot_type"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_ip_address(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting IP address of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query =
        "SELECT ip_address FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("ip_address"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_last_seen(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting last seen of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query =
        "SELECT last_seen FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("last_seen"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_location(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting location of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "SELECT location FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("location"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_os(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting OS of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "SELECT OS FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("OS"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_port(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting port of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "SELECT port FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("port"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_status(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting status of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "SELECT status FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("status"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_token(const std::string &uuid) {
  BaseLogger::getInstance().save_log("Getting token of bot " + uuid,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "SELECT token FROM bots WHERE uuid = '" + uuid + "'";
    std::unique_ptr<sql::ResultSet> res(m_stmt->executeQuery(query));
    if (res->next()) {
      return std::string(res->getString("token"));
    }
  } catch (sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}

std::string DBController::get_uuid(const std::string &token) {
  BaseLogger::getInstance().save_log("Getting UUID of bot with token: " + token,
                                     LogLevel::INFO,
                                     ServerInstance::DBCONTROLLER);
  try {
    std::string query = "SELECT uuid FROM bots WHERE token = ?";
    std::unique_ptr<sql::PreparedStatement> pstmt(
        m_connection->prepareStatement(query));
    pstmt->setString(1, token);

    std::unique_ptr<sql::ResultSet> res(pstmt->executeQuery());
    if (res->next()) {
      std::string uuid = std::string(res->getString("uuid"));
      BaseLogger::getInstance().save_log("UUID found: " + uuid, LogLevel::INFO,
                                         ServerInstance::DBCONTROLLER);
      return uuid;
    } else {
      BaseLogger::getInstance().save_log("No matching token found in database.",
                                         LogLevel::ERROR,
                                         ServerInstance::DBCONTROLLER);
    }
  } catch (const sql::SQLException &e) {
    BaseLogger::getInstance().save_exception(e, LogLevel::ERROR,
                                             ServerInstance::DBCONTROLLER);
  }
  return "";
}