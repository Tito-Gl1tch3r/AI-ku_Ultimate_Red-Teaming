#include "CryptSetup.h"
#include <openssl/ec.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rand.h>

bool CryptSetup::setup_encryption_stub(boost::asio::ip::tcp::socket &tcp_socket,
                                       EncryptionStub &stub) {
  BotLogger::getInstance().save_log("Setting up encryption.", LogLevel::INFO);
  BotLogger::getInstance().save_log("Sending CRYPT commflag.", LogLevel::TRACE);
  BotEssentials::getInstance().send_data_to_server(
      tcp_socket,
      BotEssentials::getInstance().commflag_to_byte(CommFlags::CRYPT));
  BotLogger::getInstance().save_log("Receiving OK commflag.", LogLevel::TRACE);
  if (BotEssentials::getInstance().get_commflag_from_server(tcp_socket) !=
      CommFlags::OK) {
    BotLogger::getInstance().save_log(
        "Failed to receive log commflag from server.", LogLevel::ERROR);
    return false;
  }
  BotLogger::getInstance().save_log("Received OK commflag.", LogLevel::TRACE);
  try {
    stub.set_key(setup_encryption_bot(tcp_socket));
    return true;
  } catch (const std::exception &e) {
    BotLogger::getInstance().save_exception(e, LogLevel::FATAL);
    return false;
  }
}

const unsigned char *
CryptSetup::setup_encryption_bot(const boost::asio::ip::tcp::socket &socket) {
  // Generate ECDH key pair
  EC_KEY *ecdh = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
  if (!ecdh || !EC_KEY_generate_key(ecdh)) {
    BotLogger::getInstance().save_log("Failed to generate ECDH key pair",
                                      LogLevel::FATAL);
    return 0;
  }

  // Get client's public key
  const EC_POINT *client_pub_key = EC_KEY_get0_public_key(ecdh);
  if (!client_pub_key) {
    BotLogger::getInstance().save_log("Failed to get client's public key",
                                      LogLevel::FATAL);
    EC_KEY_free(ecdh);
    return 0;
  }

  // Convert client's public key to octet string
  unsigned char client_pub_key_oct[65];
  size_t client_pub_key_oct_len = EC_POINT_point2oct(
      EC_KEY_get0_group(ecdh), client_pub_key, POINT_CONVERSION_UNCOMPRESSED,
      client_pub_key_oct, sizeof(client_pub_key_oct), NULL);
  if (client_pub_key_oct_len == 0) {
    BotLogger::getInstance().save_log(
        "Failed to convert client's public key to octet string",
        LogLevel::FATAL);
    EC_KEY_free(ecdh);
    return 0;
  }

  // Send client's public key to server
  std::vector<std::byte> client_pub_key_vec(
      client_pub_key_oct, client_pub_key_oct + client_pub_key_oct_len);
  if (!BotEssentials::getInstance().send_data_to_server(socket,
                                                        client_pub_key_vec)) {
    EC_KEY_free(ecdh);
    return 0;
  }

  // Receive server's public key
  std::vector<std::byte> server_pub_key_vec =
      BotEssentials::getInstance().get_data_from_server(socket);
  if (server_pub_key_vec.empty()) {
    BotLogger::getInstance().save_log("Failed to receive server's public key",
                                      LogLevel::FATAL);
    EC_KEY_free(ecdh);
    return 0;
  }

  // Convert server's public key from octet string
  const unsigned char *server_pub_key_oct =
      reinterpret_cast<const unsigned char *>(server_pub_key_vec.data());
  EC_POINT *server_pub_key = EC_POINT_new(EC_KEY_get0_group(ecdh));
  if (!server_pub_key || !EC_POINT_oct2point(EC_KEY_get0_group(ecdh),
                                             server_pub_key, server_pub_key_oct,
                                             server_pub_key_vec.size(), NULL)) {
    BotLogger::getInstance().save_log(
        "Failed to convert server's public key from octet string",
        LogLevel::FATAL);
    EC_POINT_free(server_pub_key);
    EC_KEY_free(ecdh);
    return 0;
  }

  // Compute shared secret
  unsigned char shared_secret[32];
  int shared_secret_len = ECDH_compute_key(shared_secret, sizeof(shared_secret),
                                           server_pub_key, ecdh, NULL);
  if (shared_secret_len <= 0) {
    BotLogger::getInstance().save_log("Failed to compute shared secret",
                                      LogLevel::FATAL);
    EC_POINT_free(server_pub_key);
    EC_KEY_free(ecdh);
    return 0;
  }

  // Derive encryption key from shared secret (using a hash function, e.g.,
  // SHA-256)
  unsigned char encryption_key[32];
  if (!EVP_Digest(shared_secret, shared_secret_len, encryption_key, NULL,
                  EVP_sha256(), NULL)) {
    BotLogger::getInstance().save_log(
        "Failed to derive encryption key from shared secret", LogLevel::FATAL);
    EC_POINT_free(server_pub_key);
    EC_KEY_free(ecdh);
    return 0;
  }

  // Clean up
  EC_POINT_free(server_pub_key);
  EC_KEY_free(ecdh);

  // Return the first byte of the encryption key as an example (you should use
  // the full key in practice)
  return &encryption_key[0];
}