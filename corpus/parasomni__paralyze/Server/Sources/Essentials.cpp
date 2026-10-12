#include "Essentials.h"
#include <boost/uuid/uuid.hpp>
#include <boost/uuid/uuid_generators.hpp>
#include <boost/uuid/uuid_io.hpp>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <openssl/pem.h>

Essentials Essentials::instance;

// file handling
std::vector<std::byte> Essentials::read_from_file(const std::string &file) {
  std::ifstream input(file, std::ios::binary);
  std::vector<char> buffer((std::istreambuf_iterator<char>(input)),
                           std::istreambuf_iterator<char>());
  std::vector<std::byte> byte_buffer(buffer.size());
  std::memcpy(byte_buffer.data(), buffer.data(), buffer.size());
  return byte_buffer;
}

void Essentials::write_to_file(const std::string &file,
                               const std::vector<std::byte> &data) {
  std::ofstream output(file, std::ios::binary);
  std::vector<char> buffer(data.size());
  std::memcpy(buffer.data(), data.data(), data.size());
  output.write(buffer.data(), buffer.size());
}

nlohmann::json Essentials::get_json_dump_from_file(const std::string &file) {
  std::vector<std::byte> data = read_from_file(file);
  nlohmann::json json = bytes_to_json(data);
  return json;
}

void Essentials::write_json_dump_to_file(const nlohmann::json &data,
                                         const std::string &file) {
  std::string json_str = data.dump();
  std::vector<std::byte> bytes = string_to_bytes(json_str);
  write_to_file(file, bytes);
}

bool Essentials::check_directory_existance(const std::string &directory) {
  if (std::filesystem::exists(directory)) {
    if (!std::filesystem::is_directory(directory)) {
      return false;
    } else {
      return true;
    }
  } else {
    return false;
  }
}

std::string Essentials::loadKey(const std::string &filePath) {
  std::ifstream file(filePath);
  if (!file.is_open()) {
    throw std::runtime_error("Failed to open public key file: " + filePath);
  }

  std::stringstream buffer;
  buffer << file.rdbuf();
  if (buffer.str().empty()) {
    throw std::runtime_error("Public key file is empty: " + filePath);
  }
  return buffer.str();
}

// formating
nlohmann::json Essentials::bytes_to_json(const std::vector<std::byte> &data) {
  std::vector<char> buffer(data.size());
  std::memcpy(buffer.data(), data.data(), data.size());
  return nlohmann::json::parse(buffer.begin(), buffer.end());
}

std::string Essentials::bytes_to_string(const std::vector<std::byte> &data) {
  std::string str(reinterpret_cast<const char *>(data.data()), data.size());
  return str;
}

std::vector<std::byte> Essentials::string_to_bytes(const std::string &data) {
  std::vector<std::byte> bytes(data.size());
  std::memcpy(bytes.data(), data.data(), data.size());
  return bytes;
}

std::string Essentials::gen_uuid() {
  boost::uuids::uuid uuid = boost::uuids::random_generator()();
  return boost::uuids::to_string(uuid);
}

std::string Essentials::evp_pkey_to_pem(EVP_PKEY *pkey) {
  if (!pkey) {
    throw std::runtime_error("Invalid EVP_PKEY");
  }

  BIO *bio = BIO_new(BIO_s_mem());
  if (!bio) {
    throw std::runtime_error("Failed to create BIO");
  }

  if (!PEM_write_bio_PUBKEY(bio, pkey)) {
    BIO_free(bio);
    throw std::runtime_error("Failed to write public key to BIO");
  }

  BUF_MEM *buf_mem;
  BIO_get_mem_ptr(bio, &buf_mem);
  std::string pem(buf_mem->data, buf_mem->length);

  BIO_free(bio);
  return pem;
}