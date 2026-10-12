package com.codehack.JungleConfig.Core.Implim;

import com.codehack.JungleConfig.Core.ConverterInterface;
import com.codehack.JungleConfig.Core.IOHandlerInterface;
import com.codehack.JungleConfig.Core.Implim.NativeConverter;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.util.Base64;

public class NativeEncryptedConverter extends NativeConverter implements ConverterInterface {

    private static final int KEY_LENGTH = 256;          // AES-256
    private static final int GCM_IV_LENGTH = 12;        // 96 bits = 12 bytes (recommended for GCM)
    private static final int SALT_LENGTH = 16;          // 128-bit salt
    private static final int PBKDF2_ITERATIONS = 100_000;

    private final char[] password;

    public NativeEncryptedConverter(IOHandlerInterface ioHandler, String password) {
        super(ioHandler);
        this.password = password.toCharArray(); // safer than keeping String
    }

    @Override
    protected String preProcess(String encryptedData) {
        if (encryptedData == null || encryptedData.isEmpty()) {
            return ""; // empty config
        }
        try {
            byte[] decoded = Base64.getDecoder().decode(encryptedData);
            if (decoded.length < SALT_LENGTH + GCM_IV_LENGTH + 1) {
                throw new IllegalArgumentException("Invalid encrypted data format");
            }

            byte[] salt = new byte[SALT_LENGTH];
            byte[] iv = new byte[GCM_IV_LENGTH];
            byte[] ciphertext = new byte[decoded.length - SALT_LENGTH - GCM_IV_LENGTH];

            System.arraycopy(decoded, 0, salt, 0, SALT_LENGTH);
            System.arraycopy(decoded, SALT_LENGTH, iv, 0, GCM_IV_LENGTH);
            System.arraycopy(decoded, SALT_LENGTH + GCM_IV_LENGTH, ciphertext, 0, ciphertext.length);

            SecretKey key = deriveKey(salt);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            GCMParameterSpec gcmSpec = new GCMParameterSpec(128, iv);
            cipher.init(Cipher.DECRYPT_MODE, key, gcmSpec);

            byte[] plaintext = cipher.doFinal(ciphertext);
            return new String(plaintext, java.nio.charset.StandardCharsets.UTF_8);

        } catch (Exception e) {
            throw new RuntimeException("Failed to decrypt config. Wrong password or corrupted data.", e);
        }
    }

    @Override
    protected String preWrite(String plaintextData) {
        try {
            byte[] salt = new byte[SALT_LENGTH];
            new SecureRandom().nextBytes(salt);

            SecretKey key = deriveKey(salt);
            byte[] iv = new byte[GCM_IV_LENGTH];
            new SecureRandom().nextBytes(iv);

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            GCMParameterSpec gcmSpec = new GCMParameterSpec(128, iv);
            cipher.init(Cipher.ENCRYPT_MODE, key, gcmSpec);

            byte[] plaintext = plaintextData.getBytes(java.nio.charset.StandardCharsets.UTF_8);
            byte[] ciphertext = cipher.doFinal(plaintext);

            // Format: [salt][iv][ciphertext]
            byte[] output = new byte[SALT_LENGTH + GCM_IV_LENGTH + ciphertext.length];
            System.arraycopy(salt, 0, output, 0, SALT_LENGTH);
            System.arraycopy(iv, 0, output, SALT_LENGTH, GCM_IV_LENGTH);
            System.arraycopy(ciphertext, 0, output, SALT_LENGTH + GCM_IV_LENGTH, ciphertext.length);

            return Base64.getEncoder().encodeToString(output);

        } catch (Exception e) {
            throw new RuntimeException("Failed to encrypt config.", e);
        }
    }

    private SecretKey deriveKey(byte[] salt) throws Exception {
        PBEKeySpec spec = new PBEKeySpec(password, salt, PBKDF2_ITERATIONS, KEY_LENGTH);
        SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
        byte[] keyBytes = factory.generateSecret(spec).getEncoded();
        return new SecretKeySpec(keyBytes, "AES");
    }

    // Optional: clear password from memory (best-effort)
    public void clearPassword() {
        java.util.Arrays.fill(password, ' ');
    }
}