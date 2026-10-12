use aes::Aes256;
use block_modes::block_padding::Pkcs7;
use block_modes::{BlockMode, Cbc};
use rand::Rng;

type Aes256Cbc = Cbc<Aes256, Pkcs7>;

pub struct Encryptor {
    key: [u8; 32],
    iv_pattern: [u8; 16],
}

impl Encryptor {
    pub fn new(key: &str, iv_pattern: [u8; 16]) -> Self {
        // Pad the key to 32 bytes (AES-256 requires a 256-bit key)
        let key_bytes = key.as_bytes();
        let mut padded_key = [0u8; 32];
        let len = key_bytes.len().min(32);
        padded_key[..len].copy_from_slice(&key_bytes[..len]);

        Encryptor {
            key: padded_key,
            iv_pattern,
        }
    }

    pub fn encrypt(&self, plaintext: &str) -> Vec<u8> {
        // Use the IV pattern directly (or modify it as needed)
        let iv = self.iv_pattern;

        let cipher = Aes256Cbc::new_from_slices(&self.key, &iv).expect("Invalid key or IV");
        let ciphertext = cipher.encrypt_vec(plaintext.as_bytes());
        // Combine the IV and the ciphertext for storage or transmission
        let mut encrypted_data = iv.to_vec();
        encrypted_data.extend_from_slice(&ciphertext);

        encrypted_data
    }

    pub fn decrypt(&self, encrypted_data: &[u8]) -> Option<String> {
        let (iv, ciphertext) = encrypted_data.split_at(16);
        let cipher = Aes256Cbc::new_from_slices(&self.key, iv).expect("Invalid key or IV");

        match cipher.decrypt_vec(ciphertext) {
            Ok(decrypted_data) => match String::from_utf8(decrypted_data) {
                Ok(decrypted_str) => Some(decrypted_str),
                Err(_) => None,
            },
            Err(_) => None,
        }
    }
}
