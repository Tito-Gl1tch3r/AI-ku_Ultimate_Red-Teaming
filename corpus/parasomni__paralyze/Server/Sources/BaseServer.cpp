#include "BaseServer.h"
#include <fstream>
#include <iostream>
#include <memory>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <sstream>

BaseServer::BaseServer(const std::string &server_address, int server_port,
                       const std::string &logger_address, int logger_port)
    : m_server_address(server_address), m_server_port(server_port),
      m_log_server_address(logger_address), m_log_server_port(logger_port) {}

BaseServer::~BaseServer() {}

const std::string &BaseServer::get_log_server_address() const {
  return m_log_server_address;
}

int BaseServer::get_log_server_port() const { return m_log_server_port; }

const std::string &BaseServer::get_server_address() const {
  return m_server_address;
}

int BaseServer::get_server_port() const { return m_server_port; }

void BaseServer::set_log_server_address(const std::string &log_server_address) {
  m_log_server_address = log_server_address;
}

void BaseServer::set_log_server_port(int log_server_port) {
  m_log_server_port = log_server_port;
}

void BaseServer::set_server_address(const std::string &server_address) {
  m_server_address = server_address;
}

void BaseServer::set_server_port(int server_port) {
  m_server_port = server_port;
}

std::unique_ptr<EVP_PKEY, decltype(&EVP_PKEY_free)>
BaseServer::loadPrivateKey(const std::string &pemFilePath) {
  std::ifstream pemFile(pemFilePath);
  if (!pemFile) {
    throw std::runtime_error("Failed to open PEM file: " + pemFilePath);
  }

  std::stringstream pemContents;
  pemContents << pemFile.rdbuf();
  std::string keyString = pemContents.str();

  BIO *bio = BIO_new_mem_buf(keyString.c_str(), keyString.size());
  if (!bio) {
    throw std::runtime_error("Failed to create BIO for private key");
  }

  // Load the private key
  EVP_PKEY *privateKey =
      PEM_read_bio_PrivateKey(bio, nullptr, nullptr, nullptr);
  BIO_free(bio);

  if (!privateKey) {
    throw std::runtime_error("Failed to load private key from PEM file");
  }

  return std::unique_ptr<EVP_PKEY, decltype(&EVP_PKEY_free)>(privateKey,
                                                             EVP_PKEY_free);
}