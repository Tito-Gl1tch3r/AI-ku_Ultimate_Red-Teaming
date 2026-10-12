package com.six2dez.burp.aiagent.config

import burp.api.montoya.persistence.Preferences
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.mockito.kotlin.any
import org.mockito.kotlin.mock
import org.mockito.kotlin.whenever
import java.util.Base64
import java.util.logging.Handler
import java.util.logging.Level
import java.util.logging.LogRecord
import java.util.logging.Logger

class SecretCipherTest {
    @Test
    fun encrypt_producesCiphertextThatIsNotPlaintext() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        val plaintext = "sk-test-key-123"
        val encrypted = cipher.encrypt(plaintext)
        assertNotEquals(plaintext, encrypted)
        assertTrue(encrypted.startsWith("ENC1:"), "ciphertext must carry the ENC1: prefix")
    }

    @Test
    fun decrypt_ofEncrypt_returnsOriginalValue() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        val plaintext = "sk-test-key-123"
        assertEquals(plaintext, cipher.decrypt(cipher.encrypt(plaintext)))
    }

    @Test
    fun encrypt_twiceProducesDifferentCiphertextDueToFreshIv() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        val first = cipher.encrypt("x")
        val second = cipher.encrypt("x")
        assertNotEquals(first, second, "IV must be fresh per call, so ciphertexts differ")
    }

    @Test
    fun decrypt_ofEnc1ValueWithBadGcmTag_returnsEmptyStringFailSoft() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        // A syntactically valid ENC1: prefix but with a corrupted/wrong-key envelope.
        val corrupted = "ENC1:" + Base64.getEncoder().encodeToString(ByteArray(32) { 0x00 })
        assertEquals("", cipher.decrypt(corrupted), "bad GCM tag must fail soft to empty string")
    }

    @Test
    fun decrypt_ofNonEnc1Value_returnsInputUnchanged() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        // Plaintext migration-compat path: non-prefixed values pass through unchanged.
        assertEquals("plain-legacy-key", cipher.decrypt("plain-legacy-key"))
    }

    @Test
    fun masterKey_generatedOnFirstUseAndReusedAfterwards() {
        val prefs = InMemoryPrefs()
        // First cipher generates and stores a key.
        whenever(prefs.mock.getString(any())).thenAnswer { invocation ->
            prefs.strings[invocation.getArgument(0)]
        }
        val first = SecretCipher(prefs.mock)
        val encrypted = first.encrypt("payload")
        val storedKey = prefs.strings[SecretCipher.MASTER_KEY_PREF_KEY]
        assertNotNull(storedKey, "a master key must be generated and stored on first use")

        // A second cipher over the same prefs must reuse the stored key and decrypt the value.
        val second = SecretCipher(prefs.mock)
        assertEquals("payload", second.decrypt(encrypted), "stored key must be reused deterministically")
    }

    @Test
    fun construction_succeedsHeadless_noHeadlessException() {
        val previous = System.getProperty("java.awt.headless")
        System.setProperty("java.awt.headless", "true")
        try {
            val cipher = SecretCipher(InMemoryPrefs().mock)
            // Exercise the full path under headless to be certain no AWT is touched.
            assertEquals("ok", cipher.decrypt(cipher.encrypt("ok")))
        } finally {
            if (previous == null) System.clearProperty("java.awt.headless") else System.setProperty("java.awt.headless", previous)
        }
    }

    /**
     * WR-01 regression: two [SecretCipher] instances over the same [Preferences] store must
     * converge on the same master key. Instance A encrypts; instance B (sharing prefs) must
     * successfully decrypt the ciphertext. The cross-instance [BOOTSTRAP_LOCK] guard ensures this
     * even on a fresh install where no key exists yet.
     */
    @Test
    fun twoInstancesOverSamePrefs_secondAdoptsFirstKey_roundTripSucceeds() {
        val prefs = InMemoryPrefs()
        val instanceA = SecretCipher(prefs.mock)
        val ciphertext = instanceA.encrypt("cross-instance-secret")
        // Instance B is constructed after A has written the key to prefs.
        val instanceB = SecretCipher(prefs.mock)
        assertEquals(
            "cross-instance-secret",
            instanceB.decrypt(ciphertext),
            "instance B must adopt the key stored by instance A — no divergent in-memory key",
        )
    }

    /**
     * WR-02 regression: an ENC1: envelope whose version byte does not match [ENVELOPE_VERSION]
     * must fail-soft to "" rather than misparse the IV and attempt GCM decryption.
     */
    @Test
    fun decrypt_unknownEnvelopeVersion_returnsEmptyStringFailSoft() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        // Build a well-formed Base64 payload but with version byte 0x02 (unknown future version).
        val fakeEnvelope = ByteArray(1 + 12 + 32)
        fakeEnvelope[0] = 0x02 // wrong version
        val corrupted =
            "ENC1:" +
                java.util.Base64
                    .getEncoder()
                    .encodeToString(fakeEnvelope)
        assertEquals("", cipher.decrypt(corrupted), "unknown envelope version must fail soft to empty string")
    }

    /**
     * The empty envelope: `"ENC1:"` with nothing after it. Base64-decodes to a zero-length array, so
     * the version-byte read would be an index-out-of-bounds if the emptiness check were removed.
     * Fail-soft to "" is the contract, and this is the arm that proves the check is load-bearing.
     */
    @Test
    fun decrypt_ofEnc1ValueWithEmptyEnvelope_returnsEmptyStringFailSoft() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        assertEquals("", cipher.decrypt("ENC1:"), "an empty envelope must fail soft to empty string")
    }

    @Test
    fun decrypt_ofEnc1ValueThatIsNotValidBase64_returnsEmptyStringFailSoft() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        assertEquals(
            "",
            cipher.decrypt("ENC1:!!!not-base64!!!"),
            "an undecodable payload must fail soft to empty string, never throw to the caller",
        )
    }

    /**
     * The master key is resolved lazily and once. Two encrypts on the SAME instance must both round
     * trip, which is the observable form of "the lazy bootstrap did not re-key between calls".
     */
    @Test
    fun twoEncryptsOnOneInstance_bothRoundTrip() {
        val cipher = SecretCipher(InMemoryPrefs().mock)
        val first = cipher.encrypt("first-secret")
        val second = cipher.encrypt("second-secret")
        assertEquals("first-secret", cipher.decrypt(first))
        assertEquals("second-secret", cipher.decrypt(second))
    }

    @Test
    fun decrypt_failure_logsOnlyPrefKeyName_neverRawValue() {
        val logger = Logger.getLogger(SecretCipher::class.java.name)
        val captured = mutableListOf<String>()
        val handler =
            object : Handler() {
                override fun publish(record: LogRecord) {
                    captured.add(record.message)
                }

                override fun flush() {
                    // INTENTIONAL: the capture list needs no flushing; records are appended in publish().
                }

                override fun close() {
                    // INTENTIONAL: nothing to release; the handler holds no resource beyond the list.
                }
            }
        handler.level = Level.ALL
        logger.addHandler(handler)
        val previousLevel = logger.level
        logger.level = Level.ALL
        try {
            val cipher = SecretCipher(InMemoryPrefs().mock)
            val secretValue = "super-secret-token-value-DO-NOT-LOG"
            // Build a corrupted ENC1: envelope so decrypt fails and logs.
            val corrupted = "ENC1:" + Base64.getEncoder().encodeToString(ByteArray(40) { 0x7F })
            cipher.decrypt(corrupted, "ollama.apiKey")
            assertTrue(captured.isNotEmpty(), "a decrypt failure must emit a log record")
            val joined = captured.joinToString("\n")
            assertTrue(joined.contains("ollama.apiKey"), "log must include the preference key name")
            assertFalse(joined.contains(secretValue), "log must never include raw secret material")
        } finally {
            logger.removeHandler(handler)
            logger.level = previousLevel
        }
    }

    /**
     * Minimal in-memory [Preferences] mock mirroring the helper used in
     * AgentSettingsMigrationTest, scoped to the getString/setString surface SecretCipher needs.
     */
    private class InMemoryPrefs {
        val strings = mutableMapOf<String, String>()
        val mock: Preferences =
            mock<Preferences>().also { prefs ->
                whenever(prefs.getString(any())).thenAnswer { invocation ->
                    strings[invocation.getArgument(0)]
                }
                whenever(prefs.setString(any(), any())).thenAnswer { invocation ->
                    strings[invocation.getArgument(0)] = invocation.getArgument(1)
                    null
                }
            }
    }
}
