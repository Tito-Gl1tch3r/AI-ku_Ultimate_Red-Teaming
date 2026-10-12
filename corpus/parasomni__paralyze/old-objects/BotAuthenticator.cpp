#include "BotAuthenticator.h"
#include <openssl/hmac.h>
#include <openssl/pem.h>

BotAuthenticator::BotAuthenticator(const std::string &init_token,
                                   const std::string &cert_file,
                                   const std::string &key_file)
    : m_init_token(init_token), m_cert_file(cert_file), m_key_file(key_file) {}

BotAuthenticator::~BotAuthenticator() {}

EVP_PKEY *BotAuthenticator::generate_key_pair() {
  EVP_PKEY *pkey = EVP_PKEY_new();
  RSA *rsa = RSA_new();
  BIGNUM *bn = BN_new();
  BN_set_word(bn, RSA_F4);
  RSA_generate_key_ex(rsa, 2048, bn, nullptr);
  EVP_PKEY_assign_RSA(pkey, rsa);
  BN_free(bn);
  return pkey;
}

X509 *BotAuthenticator::load_certificate(const char *cert_file) {
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

void BotAuthenticator::write_certificate_to_file(X509 *cert) {
  FILE *file = fopen(m_cert_file.c_str(), "w");
  PEM_write_X509(file, cert);
  fclose(file);
}

X509 *BotAuthenticator::bytes_to_x509(const std::vector<std::byte> &data) {
  BIO *bio = BIO_new_mem_buf(data.data(), data.size());
  X509 *cert = PEM_read_bio_X509(bio, nullptr, nullptr, nullptr);
  BIO_free(bio);
  return cert;
}

std::vector<std::byte> BotAuthenticator::X509_REQ_to_bytes(X509_REQ *csr) {
  BIO *bio = BIO_new(BIO_s_mem());
  PEM_write_bio_X509_REQ(bio, csr);
  BUF_MEM *bptr;
  BIO_get_mem_ptr(bio, &bptr);
  std::vector<std::byte> data(bptr->data, bptr->data + bptr->length);
  BIO_free(bio);
  return data;
}

EVP_PKEY *BotAuthenticator::load_private_key(const char *key_file) {
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

X509_REQ *BotAuthenticator::generate_CSR(EVP_PKEY *pkey, const char *CN) {
  X509_REQ *req = X509_REQ_new();
  X509_NAME *name = X509_NAME_new();

  X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                             (const unsigned char *)CN, -1, -1, 0);
  X509_REQ_set_subject_name(req, name);
  X509_REQ_set_pubkey(req, pkey);

  if (!X509_REQ_sign(req, pkey, EVP_sha256())) {
    BotLogger::getInstance().save_log("Failed to sign CSR", LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    X509_REQ_free(req);
    return nullptr;
  }

  X509_NAME_free(name);
  return req;
}

std::vector<unsigned char>
BotAuthenticator::compute_hmac(EVP_PKEY *pkey, const std::string &init_token) {
  unsigned char *key = nullptr;
  size_t key_len = EVP_PKEY_size(pkey);
  key = (unsigned char *)OPENSSL_malloc(key_len);
  EVP_PKEY_get_raw_private_key(pkey, key, &key_len);

  unsigned int len = EVP_MAX_MD_SIZE;
  std::vector<unsigned char> hmac(len);

  HMAC(EVP_sha256(), key, key_len, (const unsigned char *)init_token.c_str(),
       init_token.length(), hmac.data(), &len);
  hmac.resize(len);

  OPENSSL_free(key);
  return hmac;
}

void BotAuthenticator::authenticate(EncryptionStub *crypt_stub,
                                    boost::asio::ip::tcp::socket &socket) {
  BotLogger::getInstance().save_log("Authenticating...", LogLevel::INFO,
                                    BotModules::AUTHENTICATOR);

  BotLogger::getInstance().save_log("Generating key pair...", LogLevel::TRACE,
                                    BotModules::AUTHENTICATOR);
  EVP_PKEY *pkey = generate_key_pair();
  if (!pkey) {
    BotLogger::getInstance().save_log("Key pair generation failed",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    return;
  }

  BotLogger::getInstance().save_log("Generating CSR...", LogLevel::TRACE,
                                    BotModules::AUTHENTICATOR);
  X509_REQ *csr = generate_CSR(pkey, "BotAuthenticator");
  if (!csr) {
    BotLogger::getInstance().save_log("CSR generation failed", LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_PKEY_free(pkey);
    return;
  }

  BotLogger::getInstance().save_log("Computing HMAC...", LogLevel::TRACE,
                                    BotModules::AUTHENTICATOR);
  std::vector<unsigned char> hmac = compute_hmac(pkey, m_init_token);
  if (hmac.empty()) {
    BotLogger::getInstance().save_log(
        "HMAC computation failed", LogLevel::ERROR, BotModules::AUTHENTICATOR);
    X509_REQ_free(csr);
    EVP_PKEY_free(pkey);
    return;
  }

  BotLogger::getInstance().save_log("Sending CSR to server...", LogLevel::TRACE,
                                    BotModules::AUTHENTICATOR);
  BotEssentials::getInstance().send_data_to_server(
      socket, crypt_stub->encrypt(X509_REQ_to_bytes(csr)));
  if (BotEssentials::getInstance().get_commflag_from_server_encrypted(
          socket, crypt_stub) != CommFlags::OK) {
    BotLogger::getInstance().save_log("CSR rejected by server", LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    X509_REQ_free(csr);
    EVP_PKEY_free(pkey);
    return;
  }

  BotLogger::getInstance().save_log("Sending HMAC to server...",
                                    LogLevel::TRACE, BotModules::AUTHENTICATOR);
  BotEssentials::getInstance().send_data_to_server(
      socket,
      crypt_stub->encrypt(
          BotEssentials::getInstance().char_vector_to_byte_vector(hmac)));

  BotLogger::getInstance().save_log("Receiving certificate from server...",
                                    LogLevel::TRACE, BotModules::AUTHENTICATOR);
  std::vector<std::byte> cert_data = crypt_stub->decrypt(
      BotEssentials::getInstance().get_data_from_server(socket));
  X509 *cert = bytes_to_x509(cert_data);
  if (!cert) {
    BotLogger::getInstance().save_log("Certificate loading failed",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    X509_REQ_free(csr);
    EVP_PKEY_free(pkey);
    return;
  } else {
    BotLogger::getInstance().save_log("Certificate loaded successfully",
                                      LogLevel::INFO,
                                      BotModules::AUTHENTICATOR);
    BotLogger::getInstance().save_log("Writing certificate to file...",
                                      LogLevel::TRACE,
                                      BotModules::AUTHENTICATOR);
    write_certificate_to_file(cert);
  }

  BotLogger::getInstance().save_log("Writing private key to file...",
                                    LogLevel::TRACE, BotModules::AUTHENTICATOR);
  FILE *key_file = fopen(m_key_file.c_str(), "w");
  PEM_write_PrivateKey(key_file, pkey, nullptr, nullptr, 0, nullptr, nullptr);
  fclose(key_file);

  BotLogger::getInstance().save_log("Cleaning up...", LogLevel::TRACE,
                                    BotModules::AUTHENTICATOR);
  X509_REQ_free(csr);
  EVP_PKEY_free(pkey);
}

std::vector<std::byte>
BotAuthenticator::sign_message(const std::vector<std::byte> &message) {
  BotLogger::getInstance().save_log("Signing message...", LogLevel::INFO,
                                    BotModules::AUTHENTICATOR);
  EVP_PKEY *pkey = load_private_key(m_key_file.c_str());
  if (!pkey) {
    BotLogger::getInstance().save_log("Private key loading failed",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    return {};
  }

  EVP_MD_CTX *mdctx = EVP_MD_CTX_new();
  if (!mdctx) {
    BotLogger::getInstance().save_log("Failed to create message digest context",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_PKEY_free(pkey);
    return {};
  }

  if (EVP_DigestSignInit(mdctx, nullptr, EVP_sha256(), nullptr, pkey) <= 0) {
    BotLogger::getInstance().save_log("Failed to initialize digest sign",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pkey);
    return {};
  }

  if (EVP_DigestSignUpdate(mdctx, message.data(), message.size()) <= 0) {
    BotLogger::getInstance().save_log("Failed to update digest sign",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pkey);
    return {};
  }

  size_t siglen;
  if (EVP_DigestSignFinal(mdctx, nullptr, &siglen) <= 0) {
    BotLogger::getInstance().save_log("Failed to finalize digest sign",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pkey);
    return {};
  }

  std::vector<unsigned char> sig(siglen);
  if (EVP_DigestSignFinal(mdctx, sig.data(), &siglen) <= 0) {
    BotLogger::getInstance().save_log("Failed to finalize digest sign",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pkey);
    return {};
  }

  EVP_MD_CTX_free(mdctx);
  EVP_PKEY_free(pkey);

  return BotEssentials::getInstance().char_vector_to_byte_vector(sig);
}

bool BotAuthenticator::verify_signature(
    const std::vector<std::byte> &message,
    const std::vector<unsigned char> &signature) {
  X509 *cert = load_certificate(m_cert_file.c_str());
  if (!cert) {
    BotLogger::getInstance().save_log("Certificate loading failed",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    return false;
  }

  EVP_PKEY *pubkey = X509_get_pubkey(cert);
  if (!pubkey) {
    BotLogger::getInstance().save_log(
        "Failed to get public key from certificate", LogLevel::ERROR,
        BotModules::AUTHENTICATOR);
    X509_free(cert);
    return false;
  }

  EVP_MD_CTX *mdctx = EVP_MD_CTX_new();
  if (!mdctx) {
    BotLogger::getInstance().save_log("Failed to create message digest context",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_PKEY_free(pubkey);
    X509_free(cert);
    return false;
  }

  if (EVP_DigestVerifyInit(mdctx, nullptr, EVP_sha256(), nullptr, pubkey) <=
      0) {
    BotLogger::getInstance().save_log("Failed to initialize digest verify",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pubkey);
    X509_free(cert);
    return false;
  }

  if (EVP_DigestVerifyUpdate(mdctx, message.data(), message.size()) <= 0) {
    BotLogger::getInstance().save_log("Failed to update digest verify",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
    EVP_MD_CTX_free(mdctx);
    EVP_PKEY_free(pubkey);
    X509_free(cert);
    return false;
  }

  bool result =
      EVP_DigestVerifyFinal(mdctx, signature.data(), signature.size()) == 1;

  if (!result) {
    BotLogger::getInstance().save_log("Signature verification failed",
                                      LogLevel::ERROR,
                                      BotModules::AUTHENTICATOR);
  } else {
    BotLogger::getInstance().save_log("Signature verification successful",
                                      LogLevel::INFO,
                                      BotModules::AUTHENTICATOR);
  }

  EVP_MD_CTX_free(mdctx);
  EVP_PKEY_free(pubkey);
  X509_free(cert);

  return result;
}