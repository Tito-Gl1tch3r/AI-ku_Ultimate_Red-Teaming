#pragma once
#include "BaseLogger.h"
#include "Essentials.h"
#include <openssl/evp.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <string>
#include <vector>

class Authenticator {
private:
  std::string m_init_token;
  std::string m_ca_cert_file;
  std::string m_ca_key_file;

public:
  Authenticator(const std::string &init_token, const std::string &ca_cert_file,
                const std::string &ca_key_file);
  ~Authenticator();

  bool verify_hmac(EVP_PKEY *pkey,
                   const std::vector<unsigned char> &received_hmac,
                   const std::string &init_token);
  X509 *load_ca_certificate(const char *ca_cert_file);
  X509 *issue_certificate(X509_REQ *csr);
  bool verify_certificate(X509 *bot_cert, X509 *ca_cert);
  void react_to_config_update(const std::string &init_token,
                              const std::string &ca_cert_file,
                              const std::string &ca_key_file);
  void handle_authentication(boost::asio::ip::tcp::socket &socket);
  bool verify_signed_message(const std::vector<std::byte> &message,
                             const std::vector<unsigned char> &signature,
                             X509 *cert);
  X509_REQ *bytes_to_x509(const std::vector<std::byte> &data);
};