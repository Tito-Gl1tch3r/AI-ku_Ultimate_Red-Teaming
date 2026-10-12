package zink;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.HashMap;

public class Authorize {
    static public enum Action {SAVE, FIND, DELETE};

    final private HashMap<String, String> mApiKeys;
    final private boolean mSaveRestricted;
    final private boolean mFindRestricted;
    final private String mApiDeleteKey;

    public Authorize(JsonObject jAuthConfig, boolean pSaveRestricted, boolean pFindRestricted) {
        mApiKeys = new HashMap<>();
        mSaveRestricted = pSaveRestricted;
        mFindRestricted = pFindRestricted;
        mApiDeleteKey = jAuthConfig.get("delete-key").getAsString();
        JsonArray jApiKeys = jAuthConfig.get("api-keys").getAsJsonArray();
        if (jApiKeys != null) {
            for (int i = 0; i < jApiKeys.size(); i++) {
                JsonObject jUserKey = jApiKeys.get(i).getAsJsonObject();
                mApiKeys.put(jUserKey.get("key").getAsString(), jUserKey.get("key").getAsString());
            }
        }
    }

    public int size() {
        return mApiKeys.size();
    }

    public boolean isFindRestricted() {
        return mFindRestricted;
    }
    public boolean isSaveRestricted() {
        return mSaveRestricted;
    }

    public boolean validate(String pKey, Action pAction ) {
        if (((pAction == Action.SAVE) && (mSaveRestricted)) || ((pAction == Action.FIND) && (mFindRestricted))) {
            return mApiKeys.containsKey(pKey);
        } else if (pAction == Action.DELETE) {
            return ((mApiDeleteKey.contentEquals(pKey)) && (mApiDeleteKey != null));
        }
        return false;
    }
}

