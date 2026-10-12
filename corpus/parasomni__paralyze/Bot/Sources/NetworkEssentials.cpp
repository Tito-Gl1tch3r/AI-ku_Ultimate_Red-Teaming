#include "NetworkEssentials.h"
#include "BotLogger.h"

X509 *NetworkEssentials::load_certificate(const char *cert_file) {
  FILE *file = fopen(cert_file, "r");
  if (!file) {
    BotLogger::getInstance().save_log(
        "Failed to open certificate file: " + std::string(cert_file),
        LogLevel::ERROR, BotModules::AUTHENTICATOR);
    return nullptr;
  }
  X509 *cert = PEM_read_X509(file, nullptr, nullptr, nullptr);
  fclose(file);
  if (!cert) {
    BotLogger::getInstance().save_log(
        "Failed to load certificate from file: " + std::string(cert_file),
        LogLevel::ERROR, BotModules::AUTHENTICATOR);
  }
  return cert;
}

void NetworkEssentials::write_certificate_to_file(
    X509 *cert, const std::string &cert_file) {
  FILE *file = fopen(cert_file.c_str(), "w");
  PEM_write_X509(file, cert);
  fclose(file);
}

X509 *NetworkEssentials::bytes_to_x509(const std::vector<std::byte> &data) {
  BIO *bio = BIO_new_mem_buf(data.data(), data.size());
  X509 *cert = PEM_read_bio_X509(bio, nullptr, nullptr, nullptr);
  BIO_free(bio);
  return cert;
}

std::vector<std::byte> NetworkEssentials::X509_REQ_to_bytes(X509_REQ *csr) {
  BIO *bio = BIO_new(BIO_s_mem());
  PEM_write_bio_X509_REQ(bio, csr);
  BUF_MEM *bptr;
  BIO_get_mem_ptr(bio, &bptr);
  std::vector<std::byte> data(
      reinterpret_cast<std::byte *>(bptr->data),
      reinterpret_cast<std::byte *>(bptr->data + bptr->length));
  BIO_free(bio);
  return data;
}

EVP_PKEY *NetworkEssentials::load_private_key(const char *key_file) {
  FILE *file = fopen(key_file, "r");
  if (!file) {
    BotLogger::getInstance().save_log(
        "Failed to open private key file: " + std::string(key_file),
        LogLevel::ERROR, BotModules::AUTHENTICATOR);
    return nullptr;
  }
  EVP_PKEY *pkey = PEM_read_PrivateKey(file, nullptr, nullptr, nullptr);
  fclose(file);
  if (!pkey) {
    BotLogger::getInstance().save_log(
        "Failed to load private key from file: " + std::string(key_file),
        LogLevel::ERROR, BotModules::AUTHENTICATOR);
  }
  return pkey;
}
