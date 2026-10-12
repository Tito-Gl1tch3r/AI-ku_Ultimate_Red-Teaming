#include "BotEssentials.h"
#include <ctime>
#include <fstream>
#include <openssl/evp.h>
#include <openssl/ossl_typ.h>
#include <openssl/rand.h>
#include <sstream>

// file handling
std::vector<std::byte> BotEssentials::read_from_file(const std::string &file) {
  std::ifstream input(file, std::ios::binary);
  if (!input) {
    throw std::ios_base::failure("Failed to open file for reading: " + file);
  }
  std::vector<char> buffer((std::istreambuf_iterator<char>(input)),
                           std::istreambuf_iterator<char>());
  std::vector<std::byte> bytes(buffer.size());
  std::transform(buffer.begin(), buffer.end(), bytes.begin(),
                 [](char c) { return static_cast<std::byte>(c); });

  return bytes;
}

void BotEssentials::write_to_file(const std::string &file,
                                  const std::vector<std::byte> &data) {
  std::ofstream output(file, std::ios::binary);
  if (!output) {
    throw std::ios_base::failure("Failed to open file for writing: " + file);
  }
  std::vector<char> char_data(data.size());
  std::transform(data.begin(), data.end(), char_data.begin(),
                 [](std::byte b) { return static_cast<char>(b); });

  output.write(char_data.data(), char_data.size());
}

bool BotEssentials::check_directory_existance(const std::string &directory) {
  return std::filesystem::exists(directory) &&
         std::filesystem::is_directory(directory);
}

bool BotEssentials::check_file_existance(const std::string &file) {
  return std::filesystem::exists(file) &&
         std::filesystem::is_regular_file(file);
}

nlohmann::json BotEssentials::get_json_dump_from_file(const std::string &file) {
  std::vector<std::byte> data = read_from_file(file);
  nlohmann::json json = bytes_to_json(data);
  return json;
}

// formating
std::string BotEssentials::get_current_time_as_string() {
  std::time_t current_time = std::time(nullptr);
  std::tm *local_time = std::localtime(&current_time);

  char buffer[100];
  std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", local_time);

  return std::string(buffer);
}

nlohmann::json BotEssentials::bytes_to_json(std::vector<std::byte> &data) {
  std::string json_str;
  json_str.reserve(data.size());
  std::transform(data.begin(), data.end(), std::back_inserter(json_str),
                 [](std::byte b) { return static_cast<char>(b); });
  nlohmann::json json = nlohmann::json::parse(json_str);
  return json;
}

std::vector<std::byte>
BotEssentials::json_to_bytes(const nlohmann::json &data) {
  std::string json_str = data.dump();
  std::vector<std::byte> bytes(json_str.size());
  std::transform(json_str.begin(), json_str.end(), bytes.begin(),
                 [](char c) { return static_cast<std::byte>(c); });

  return bytes;
}

std::string BotEssentials::bytes_to_string(const std::vector<std::byte> &data) {
  std::string result(data.size(), '\0');
  std::transform(data.begin(), data.end(), result.begin(),
                 [](std::byte b) { return static_cast<char>(b); });
  return result;
}

std::vector<std::byte> BotEssentials::string_to_bytes(const std::string &data) {
  std::vector<std::byte> result(data.size());
  std::transform(data.begin(), data.end(), result.begin(),
                 [](char c) { return static_cast<std::byte>(c); });
  return result;
}

std::vector<std::byte> BotEssentials::int_to_byte(int data) {
  std::vector<std::byte> bytes;
  for (std::size_t i = 0; i < sizeof(data); i++) {
    bytes.push_back(static_cast<std::byte>((data >> (i * 8)) & 0xFF));
  }
  return bytes;
}

int BotEssentials::byte_to_int(const std::vector<std::byte> &data) {
  int result = 0;
  for (std::size_t i = 0; i < sizeof(result); i++) {
    result |= static_cast<int>(data[i]) << (i * 8);
  }
  return result;
}

std::vector<std::byte> BotEssentials::char_vector_to_byte_vector(
    const std::vector<unsigned char> &data) {
  std::vector<std::byte> bytes;
  bytes.reserve(data.size());
  for (const auto &ch : data) {
    bytes.push_back(static_cast<std::byte>(ch));
  }
  return bytes;
}

std::vector<unsigned char>
BotEssentials::byte_vector_to_char_vector(const std::vector<std::byte> &data) {
  std::vector<unsigned char> chars;
  chars.reserve(data.size());
  std::transform(data.begin(), data.end(), std::back_inserter(chars),
                 [](std::byte b) { return static_cast<unsigned char>(b); });
  return chars;
}

std::vector<unsigned char> BotEssentials::generate_salt(int length) {
  std::vector<unsigned char> salt(length);
  if (RAND_bytes(salt.data(), length) != 1) {
    throw std::runtime_error("Failed to generate salt");
  }
  return salt;
}

std::vector<unsigned char>
BotEssentials::derive_key(const std::string &password,
                          const std::vector<unsigned char> &salt,
                          int key_length, int iterations) {
  std::vector<unsigned char> key(key_length);
  if (PKCS5_PBKDF2_HMAC(password.c_str(), password.size(), salt.data(),
                        salt.size(), iterations, EVP_sha256(), key_length,
                        key.data()) != 1) {
    throw std::runtime_error("Failed to derive key");
  }
  return key;
}

std::vector<std::byte>
BotEssentials::encrypt(const std::vector<std::byte> &data,
                       const std::string &password) {
  std::vector<unsigned char> plaintext = byte_vector_to_char_vector(data);

  std::vector<unsigned char> salt = generate_salt(16);
  std::vector<unsigned char> key = derive_key(password, salt, 32, 100000);
  std::vector<unsigned char> iv = generate_salt(16);

  std::vector<unsigned char> encrypted_data(data.size());

  EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
  if (!ctx)
    throw std::runtime_error("Failed to create context");

  if (1 !=
      EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key.data(), iv.data())) {
    EVP_CIPHER_CTX_free(ctx);
    throw std::runtime_error("Encryption initialization failed");
  }

  std::vector<unsigned char> ciphertext(
      plaintext.size() + EVP_CIPHER_block_size(EVP_aes_256_cbc()));
  int len;
  if (1 != EVP_EncryptUpdate(ctx, ciphertext.data(), &len, plaintext.data(),
                             plaintext.size())) {
    EVP_CIPHER_CTX_free(ctx);
    throw std::runtime_error("Encryption failed");
  }
  int ciphertext_len = len;

  if (1 != EVP_EncryptFinal_ex(ctx, ciphertext.data() + len, &len)) {
    EVP_CIPHER_CTX_free(ctx);
    throw std::runtime_error("Final encryption step failed");
  }
  ciphertext_len += len;
  ciphertext.resize(ciphertext_len);

  EVP_CIPHER_CTX_free(ctx);

  // save key and iv in environment var

  return char_vector_to_byte_vector(ciphertext);
}

std::pair<std::vector<std::byte>, std::vector<std::byte>>
BotEssentials::get_key_iv() {
  std::string key_str = std::getenv("ENCRYPTION_KEY");
  std::string iv_str = std::getenv("ENCRYPTION_IV");
  return {string_to_bytes(key_str), string_to_bytes(iv_str)};
}

std::vector<std::byte>
BotEssentials::decrypt(const std::vector<std::byte> &data) {
  std::vector<unsigned char> ciphertext = byte_vector_to_char_vector(data);
  std::pair<std::vector<std::byte>, std::vector<std::byte>> key_iv =
      get_key_iv();
  std::vector<unsigned char> key = byte_vector_to_char_vector(key_iv.first);
  std::vector<unsigned char> iv = byte_vector_to_char_vector(key_iv.second);

  EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
  if (!ctx)
    throw std::runtime_error("Failed to create context");

  if (1 !=
      EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key.data(), iv.data())) {
    EVP_CIPHER_CTX_free(ctx);
    throw std::runtime_error("Decryption initialization failed");
  }

  std::vector<unsigned char> plaintext(ciphertext.size());
  int len;
  if (1 != EVP_DecryptUpdate(ctx, plaintext.data(), &len, ciphertext.data(),
                             ciphertext.size())) {
    EVP_CIPHER_CTX_free(ctx);
    throw std::runtime_error("Decryption failed");
  }
  int plaintext_len = len;

  if (1 != EVP_DecryptFinal_ex(ctx, plaintext.data() + len, &len)) {
    EVP_CIPHER_CTX_free(ctx);
    throw std::runtime_error("Final decryption step failed");
  }
  plaintext_len += len;
  plaintext.resize(plaintext_len);

  EVP_CIPHER_CTX_free(ctx);
  return char_vector_to_byte_vector(plaintext);
}