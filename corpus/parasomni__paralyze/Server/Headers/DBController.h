#pragma once
#include "BaseLogger.h"
#include "Essentials.h"
#include <map>
#include <mariadb/conncpp.hpp>
#include <string>

// DATABASE SCHEMA
// TABLE CONTENTS:
// 1. uuid (string)
// 2. ip_address (string)
// 3. port (int)
// 4. location (string)
// 5. status (string)
// 6. last_seen (string)
// 7. bot_type (string) ? what is this
// 8. token (string)
// 9. OS (string)

class DBController {
private:
  DBController() = default;
  DBController(const DBController &) = delete;
  DBController &operator=(const DBController &) = delete;
  std::map<std::string, std::string> m_db_config;
  sql::Driver *m_driver;
  std::unique_ptr<sql::Connection> m_connection;
  std::unique_ptr<sql::Statement> m_stmt;
  sql::Properties m_properties;

  // helpers
  void load_db_config(const std::string &config_file);
  std::string generate_query(const std::map<std::string, std::string> &bot,
                             const std::string &action);
  void read_config(const std::string &filename,
                   std::map<std::string, std::string> &config);

public:
  static DBController &getInstance() {
    static DBController instance;
    return instance;
  }
  void react_to_config_update(const std::map<std::string, std::string> &config);
  void init_controller(const std::string &config_file);

  // setters
  void insert_bot(const std::map<std::string, std::string> &bot);
  void update_bot(const std::map<std::string, std::string> &bot);
  void delete_bot(const std::string &uuid);

  void update_bot_status(const std::string &uuid, const std::string &status);
  void update_bot_last_seen(const std::string &uuid,
                            const std::string &last_seen);
  void update_bot_location(const std::string &uuid,
                           const std::string &location);
  void update_bot_ip_address(const std::string &uuid,
                             const std::string &ip_address);
  void update_bot_port(const std::string &uuid, const int port);
  void update_bot_token(const std::string &uuid, const std::string &token);
  void update_bot_bot_type(const std::string &uuid,
                           const std::string &bot_type);

  // getters
  std::string get_token(const std::string &uuid);
  std::string get_bot_type(const std::string &uuid);
  std::string get_location(const std::string &uuid);
  std::string get_status(const std::string &uuid);
  std::string get_last_seen(const std::string &uuid);
  std::string get_ip_address(const std::string &uuid);
  std::string get_port(const std::string &uuid);
  std::string get_uuid(const std::string &token);
  std::string get_os(const std::string &uuid);
  std::string get_url();
  sql::Properties get_properties();
};
