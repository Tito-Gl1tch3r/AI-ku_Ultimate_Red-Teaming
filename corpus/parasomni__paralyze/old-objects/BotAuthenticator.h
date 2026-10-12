#pragma once
#include "BotEssentials.h"
#include "EncryptionStub.h"
#include <openssl/evp.h>
#include <openssl/x509.h>
#include <string>
#include <vector>

class BotAuthenticator {
  std::string m_init_token;
  std::string m_cert_file;
  std::string m_key_file;

public:
  BotAuthenticator(const std::string &init_token, const std::string &cert_file,
                   const std::string &key_file);
  ~BotAuthenticator();

  EVP_PKEY *generate_key_pair();
  X509 *load_certificate(const char *cert_file);
  void write_certificate_to_file(X509 *cert);
  X509 *bytes_to_x509(const std::vector<std::byte> &data);
  std::vector<std::byte> X509_REQ_to_bytes(X509_REQ *csr);
  EVP_PKEY *load_private_key(const char *key_file);
  X509_REQ *generate_CSR(EVP_PKEY *pkey, const char *CN);
  std::vector<unsigned char> compute_hmac(EVP_PKEY *pkey,
                                          const std::string &init_token);
  void authenticate(EncryptionStub *crypt_stub,
                    boost::asio::ip::tcp::socket &socket);
  std::vector<std::byte> sign_message(const std::vector<std::byte> &message);
  bool verify_signature(const std::vector<std::byte> &message,
                        const std::vector<unsigned char> &signature);
};