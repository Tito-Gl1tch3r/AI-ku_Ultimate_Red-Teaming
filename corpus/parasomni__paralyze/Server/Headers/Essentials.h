#pragma once
#include "BaseLogger.h"
#include <boost/asio.hpp>
#include <nlohmann/json.hpp>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <string>
#include <vector>

class Essentials {
private:
  Essentials() = default;
  Essentials(const Essentials &) = delete;
  Essentials &operator=(const Essentials &) = delete;
  static Essentials instance;

public:
  static Essentials &getInstance() { return instance; }
  // file handling
  std::vector<std::byte> read_from_file(const std::string &file);
  void write_to_file(const std::string &file,
                     const std::vector<std::byte> &data);
  nlohmann::json get_json_dump_from_file(const std::string &file);
  void write_json_dump_to_file(const nlohmann::json &data,
                               const std::string &file);
  bool check_directory_existance(const std::string &directory);
  std::string loadKey(const std::string &filePath);

  // formating
  nlohmann::json bytes_to_json(const std::vector<std::byte> &data);
  std::string bytes_to_string(const std::vector<std::byte> &data);
  std::vector<std::byte> string_to_bytes(const std::string &data);
  std::string evp_pkey_to_pem(EVP_PKEY *pkey);

  // miscellanous
  std::string gen_uuid();
};