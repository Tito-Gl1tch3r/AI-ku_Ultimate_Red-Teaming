package com.takuze.mobiletrustlab;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;

final class LabStateStore {
    private static final String PREFS = "integrity_cache";
    private static final String RECORD = "signed_state";
    private static final String KEY_ALIAS = "mobile_trust_lab_hmac";
    private final SharedPreferences preferences;

    LabStateStore(Context context) {
        preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (load() == null) {
            save(new State(100, 1, false, false));
        }
    }

    boolean claimReward() {
        State current = requireState();
        if (current.claimed) {
            return false;
        }
        save(new State(current.balance + 500, current.level, current.premium, true));
        return true;
    }

    void reset() {
        save(new State(100, 1, false, false));
    }

    String snapshot() {
        State state = requireState();
        return "balance: " + state.balance
            + "\nlevel: " + state.level
            + "\npremium: " + state.premium
            + "\nreward claimed: " + state.claimed
            + "\n\nmode: HMAC-protected local cache"
            + "\nproduction authority: trusted service";
    }

    private State requireState() {
        State state = load();
        if (state == null) {
            state = new State(100, 1, false, false);
            save(state);
        }
        return state;
    }

    private State load() {
        try {
            String record = preferences.getString(RECORD, null);
            if (record == null) {
                return null;
            }
            int separator = record.lastIndexOf('.');
            if (separator < 1) {
                return null;
            }
            String payload = record.substring(0, separator);
            String expected = record.substring(separator + 1);
            String actual = sign(payload);
            if (!constantTimeEquals(expected, actual)) {
                return null;
            }
            String[] parts = payload.split("\\|", -1);
            if (parts.length != 4) {
                return null;
            }
            return new State(
                Integer.parseInt(parts[0]),
                Integer.parseInt(parts[1]),
                Boolean.parseBoolean(parts[2]),
                Boolean.parseBoolean(parts[3])
            );
        } catch (Exception ignored) {
            return null;
        }
    }

    private void save(State state) {
        try {
            String payload = state.balance + "|" + state.level + "|" + state.premium + "|" + state.claimed;
            preferences.edit().putString(RECORD, payload + "." + sign(payload)).apply();
        } catch (Exception error) {
            throw new IllegalStateException("Unable to protect local cache", error);
        }
    }

    private String sign(String payload) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(getOrCreateKey());
        byte[] digest = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
        return Base64.encodeToString(digest, Base64.NO_WRAP);
    }

    private SecretKey getOrCreateKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
        keyStore.load(null);
        if (!keyStore.containsAlias(KEY_ALIAS)) {
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_HMAC_SHA256, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY
            ).build());
            generator.generateKey();
        }
        return ((KeyStore.SecretKeyEntry) keyStore.getEntry(KEY_ALIAS, null)).getSecretKey();
    }

    private static boolean constantTimeEquals(String left, String right) {
        byte[] a = left.getBytes(StandardCharsets.UTF_8);
        byte[] b = right.getBytes(StandardCharsets.UTF_8);
        int diff = a.length ^ b.length;
        int length = Math.max(a.length, b.length);
        for (int index = 0; index < length; index++) {
            byte av = index < a.length ? a[index] : 0;
            byte bv = index < b.length ? b[index] : 0;
            diff |= av ^ bv;
        }
        return diff == 0;
    }

    private static final class State {
        final int balance;
        final int level;
        final boolean premium;
        final boolean claimed;

        State(int balance, int level, boolean premium, boolean claimed) {
            this.balance = balance;
            this.level = level;
            this.premium = premium;
            this.claimed = claimed;
        }
    }
}
