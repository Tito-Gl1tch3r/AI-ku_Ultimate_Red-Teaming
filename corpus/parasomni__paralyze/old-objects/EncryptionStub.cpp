#include "EncryptionStub.h"
#include <cstring>
#include <iostream>
#include <openssl/aes.h>
#include <openssl/rand.h>

EncryptionStub::EncryptionStub(const unsigned char *key)
    : m_block_size(AES_BLOCK_SIZE) {
  memcpy(m_key, key, 32);
}

void EncryptionStub::set_key(const unsigned char *key) {
  memcpy(m_key, key, 32);
}

std::vector<std::byte>
EncryptionStub::encrypt(const std::vector<std::byte> &plaintext) {
  unsigned char iv[AES_BLOCK_SIZE];
  RAND_bytes(iv, AES_BLOCK_SIZE);

  AES_KEY encryptKey;
  AES_set_encrypt_key(m_key, 256, &encryptKey);

  // Padding
  int padding_length = m_block_size - (plaintext.size() % m_block_size);
  std::vector<std::byte> padded_plaintext = plaintext;
  padded_plaintext.insert(padded_plaintext.end(), padding_length,
                          std::byte(padding_length));

  std::vector<std::byte> ciphertext(padded_plaintext.size() + AES_BLOCK_SIZE);
  std::memcpy(ciphertext.data(), iv, AES_BLOCK_SIZE); // Store IV in ciphertext

  unsigned char *encrypted_text =
      reinterpret_cast<unsigned char *>(ciphertext.data() + AES_BLOCK_SIZE);

  AES_cbc_encrypt(
      reinterpret_cast<const unsigned char *>(padded_plaintext.data()),
      encrypted_text, padded_plaintext.size(), &encryptKey, iv, AES_ENCRYPT);

  return ciphertext;
}

std::vector<std::byte>
EncryptionStub::decrypt(const std::vector<std::byte> &ciphertext) {
  unsigned char iv[AES_BLOCK_SIZE];
  std::memcpy(iv, ciphertext.data(), AES_BLOCK_SIZE); // Extract IV

  AES_KEY decryptKey;
  AES_set_decrypt_key(m_key, 256, &decryptKey);

  std::vector<std::byte> decrypted_text(ciphertext.size() - AES_BLOCK_SIZE);
  AES_cbc_encrypt(reinterpret_cast<const unsigned char *>(ciphertext.data() +
                                                          AES_BLOCK_SIZE),
                  reinterpret_cast<unsigned char *>(decrypted_text.data()),
                  decrypted_text.size(), &decryptKey, iv, AES_DECRYPT);

  // Remove padding
  int padding_length = static_cast<int>(decrypted_text.back());
  decrypted_text.resize(decrypted_text.size() - padding_length);

  return decrypted_text;
}
