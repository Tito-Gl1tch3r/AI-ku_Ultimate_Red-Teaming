package utils

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"io"
	"os"
)

func getEncryptionKey() ([]byte, error) {
	key := os.Getenv("ENCRYPTION_KEY")
	if len(key) != 32 {
		return nil, errors.New("ENCRYPTION_KEY must be 32 bytes (256 bit)")
	}
	return []byte(key), nil
}

func EncryptFile(content []byte) ([]byte, []byte, error) {
	key, err := getEncryptionKey()
	if err != nil {
		return nil, nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, nil, err
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return nil, nil, err
	}

	nonce := make([]byte, aesGCM.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, nil, err
	}

	encrypted := aesGCM.Seal(nil, nonce, content, nil)
	return encrypted, nonce, nil
}

func DecryptFile(encrypted, nonce []byte) ([]byte, error) {
	key, err := getEncryptionKey()
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	plaintext, err := aesGCM.Open(nil, nonce, encrypted, nil)
	if err != nil {
		return nil, err
	}

	return plaintext, nil
}

func EncodeNonce(nonce []byte) string {
	return hex.EncodeToString(nonce)
}

func DecodeNonce(nonceHex string) ([]byte, error) {
	return hex.DecodeString(nonceHex)
}
