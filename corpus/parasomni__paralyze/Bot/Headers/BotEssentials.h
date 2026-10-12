#pragma once
#include <boost/asio.hpp>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

class BotEssentials {
private:
  BotEssentials() = default;
  BotEssentials(const BotEssentials &) = delete;
  BotEssentials &operator=(const BotEssentials &) = delete;
  static BotEssentials instance;

  std::vector<unsigned char> generate_salt(int length);
  std::vector<unsigned char> derive_key(const std::string &password,
                                        const std::vector<unsigned char> &salt,
                                        int key_length, int iterations);
  std::pair<std::vector<std::byte>, std::vector<std::byte>> get_key_iv();

public:
  static BotEssentials &getInstance() {
    static BotEssentials instance;
    return instance;
  }
  // file handling
  std::vector<std::byte> read_from_file(const std::string &file);
  void write_to_file(const std::string &file,
                     const std::vector<std::byte> &data);
  bool check_directory_existance(const std::string &directory);
  bool check_file_existance(const std::string &file);
  nlohmann::json get_json_dump_from_file(const std::string &file);

  // encryption
  std::vector<std::byte> encrypt(const std::vector<std::byte> &data,
                                 const std::string &password);

  std::vector<std::byte> decrypt(const std::vector<std::byte> &data);

  // formating
  nlohmann::json bytes_to_json(std::vector<std::byte> &data);
  std::vector<std::byte> json_to_bytes(const nlohmann::json &data);
  std::string bytes_to_string(const std::vector<std::byte> &data);
  std::vector<std::byte> string_to_bytes(const std::string &data);
  std::vector<std::byte> int_to_byte(int data);
  int byte_to_int(const std::vector<std::byte> &data);
  std::string get_current_time_as_string();
  std::vector<std::byte>
  char_vector_to_byte_vector(const std::vector<unsigned char> &data);
  std::vector<unsigned char>
  byte_vector_to_char_vector(const std::vector<std::byte> &data);
};