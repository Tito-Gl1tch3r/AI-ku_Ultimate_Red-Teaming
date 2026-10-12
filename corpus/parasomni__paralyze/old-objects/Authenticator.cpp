#include "Authenticator.h"
#include <openssl/hmac.h>
#include <openssl/pem.h>

Authenticator::Authenticator(const std::string &init_token,
                             const std::string &ca_cert_file,
                             const std::string &ca_key_file)
    : m_init_token(init_token), m_ca_cert_file(ca_cert_file),
      m_ca_key_file(ca_key_file) {}

Authenticator::~Authenticator() {}

bool Authenticator::verify_hmac(EVP_PKEY *pkey,
                                const std::vector<unsigned char> &received_hmac,
                                const std::string &init_token) {
  unsigned char *key = nullptr;
  size_t key_len = EVP_PKEY_size(pkey);
  key = (unsigned char *)OPENSSL_malloc(key_len);
  EVP_PKEY_get_raw_private_key(pkey, key, &key_len);

  unsigned int len = EVP_MAX_MD_SIZE;
  std::vector<unsigned char> computed_hmac(len);

  HMAC(EVP_sha256(), key, key_len, (const unsigned char *)init_token.c_str(),
       init_token.length(), computed_hmac.data(), &len);
  computed_hmac.resize(len);

  OPENSSL_free(key);

  return received_hmac == computed_hmac;
}

X509 *Authenticator::load_ca_certificate(const char *ca_cert_file) {
  FILE *fp = fopen(ca_cert_file, "r");
  if (!fp) {
    return nullptr;
  }

  X509 *ca_cert = PEM_read_X509(fp, nullptr, nullptr, nullptr);
  fclose(fp);

  return ca_cert;
}

X509 *Authenticator::issue_certificate(X509_REQ *csr) {
  BaseLogger::getInstance().save_log("Issuing certificate", LogLevel::INFO,
                                     ServerInstance::AUTHENTICATOR);
  FILE *ca_cert_file = fopen(m_ca_cert_file.c_str(), "r");
  if (!ca_cert_file) {
    BaseLogger::getInstance().save_log("Failed to open CA certificate file",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return nullptr;
  }
  X509 *ca_cert = PEM_read_X509(ca_cert_file, nullptr, nullptr, nullptr);
  fclose(ca_cert_file);
  if (!ca_cert) {
    BaseLogger::getInstance().save_log("Failed to read CA certificate",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return nullptr;
  }
  FILE *ca_key_file = fopen(m_ca_key_file.c_str(), "r");
  if (!ca_key_file) {
    BaseLogger::getInstance().save_log("Failed to open CA key file",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return nullptr;
  }
  EVP_PKEY *ca_key =
      PEM_read_PrivateKey(ca_key_file, nullptr, nullptr, nullptr);
  fclose(ca_key_file);
  if (!ca_key) {
    BaseLogger::getInstance().save_log("Failed to read CA key", LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return nullptr;
  }

  X509 *cert = X509_new();
  if (!cert) {
    BaseLogger::getInstance().save_log("Failed to create new certificate",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return nullptr;
  }
  X509_set_version(cert, 2);
  ASN1_INTEGER_set(X509_get_serialNumber(cert), 1);
  X509_gmtime_adj(X509_get_notBefore(cert), 0);
  X509_gmtime_adj(X509_get_notAfter(cert), 31536000L);
  X509_set_pubkey(cert, X509_REQ_get_pubkey(csr));
  X509_set_subject_name(cert, X509_REQ_get_subject_name(csr));
  X509_set_issuer_name(cert, X509_get_subject_name(ca_cert));
  if (!X509_sign(cert, ca_key, EVP_sha256())) {
    BaseLogger::getInstance().save_log("Failed to sign certificate",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return nullptr;
  }
  EVP_PKEY_free(ca_key);
  X509_free(ca_cert);
  return cert;
}

bool Authenticator::verify_certificate(X509 *bot_cert, X509 *ca_cert) {
  EVP_PKEY *ca_pubkey = X509_get_pubkey(ca_cert);
  if (!ca_pubkey) {
    BaseLogger::getInstance().save_log("Failed to get CA public key",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return false;
  }
  int ret = X509_verify(bot_cert, ca_pubkey);
  EVP_PKEY_free(ca_pubkey);
  return ret == 1;
}

void Authenticator::react_to_config_update(const std::string &init_token,
                                           const std::string &ca_cert_file,
                                           const std::string &ca_key_file) {
  m_init_token = init_token;
  m_ca_cert_file = ca_cert_file;
  m_ca_key_file = ca_key_file;
}

void Authenticator::handle_authentication(
    boost::asio::ip::tcp::socket &socket) {
  BaseLogger::getInstance().save_log("Handling authentication", LogLevel::INFO,
                                     ServerInstance::AUTHENTICATOR);
  std::vector<std::byte> data(1024);
  boost::system::error_code error;
  size_t len = socket.read_some(boost::asio::buffer(data), error);
  if (error) {
    BaseLogger::getInstance().save_log("Error reading data: " + error.message(),
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return;
  }
  data.resize(len);

  std::vector<unsigned char> hmac(data.begin(), data.end());
  X509 *ca_cert = load_ca_certificate(m_ca_cert_file.c_str());
  if (!ca_cert) {
    BaseLogger::getInstance().save_log("Failed to load CA certificate",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return;
  }

  if (!verify_hmac(X509_get_pubkey(ca_cert), hmac, m_init_token)) {
    BaseLogger::getInstance().save_log("HMAC verification failed",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return;
  }

  X509_REQ *csr = bytes_to_x509(data);
  if (!csr) {
    BaseLogger::getInstance().save_log("Failed to convert bytes to X509_REQ",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return;
  }

  X509 *bot_cert = issue_certificate(csr);
  if (!bot_cert) {
    BaseLogger::getInstance().save_log("Failed to issue certificate",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return;
  }

  if (!verify_certificate(bot_cert, ca_cert)) {
    BaseLogger::getInstance().save_log("Certificate verification failed",
                                       LogLevel::ERROR,
                                       ServerInstance::AUTHENTICATOR);
    return;
  }

  std::vector<std::byte> cert_bytes;
  cert_bytes.resize(i2d_X509(bot_cert, nullptr));
  unsigned char *p = cert_bytes.data();
  i2d_X509(bot_cert, &p);

  boost::asio::write(socket, boost::asio::buffer(cert_bytes));
  X509_free(ca_cert);
  X509_free(bot_cert);
  X509_REQ_free(csr);
}