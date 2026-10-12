package com.takuze.mobiletrustlab;

import android.content.Context;
import android.content.SharedPreferences;

final class LabStateStore {
    private static final String PREFS = "player_state";
    private static final String WALLET_BALANCE = "wallet_balance";
    private static final String PLAYER_LEVEL = "player_level";
    private static final String PREMIUM_ENTITLEMENT = "premium_entitlement";
    private static final String REWARD_CLAIMED = "reward_claimed";
    private final SharedPreferences preferences;

    LabStateStore(Context context) {
        preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (!preferences.contains(WALLET_BALANCE)) {
            reset();
        }
    }

    boolean claimReward() {
        if (preferences.getBoolean(REWARD_CLAIMED, false)) {
            return false;
        }
        int balance = preferences.getInt(WALLET_BALANCE, 100);
        preferences.edit()
            .putInt(WALLET_BALANCE, balance + 500)
            .putBoolean(REWARD_CLAIMED, true)
            .apply();
        return true;
    }

    void reset() {
        preferences.edit()
            .putInt(WALLET_BALANCE, 100)
            .putInt(PLAYER_LEVEL, 1)
            .putBoolean(PREMIUM_ENTITLEMENT, false)
            .putBoolean(REWARD_CLAIMED, false)
            .apply();
    }

    String snapshot() {
        return "balance: " + preferences.getInt(WALLET_BALANCE, 0)
            + "\nlevel: " + preferences.getInt(PLAYER_LEVEL, 0)
            + "\npremium: " + preferences.getBoolean(PREMIUM_ENTITLEMENT, false)
            + "\nreward claimed: " + preferences.getBoolean(REWARD_CLAIMED, false)
            + "\n\nmode: client-authoritative preferences";
    }
}
