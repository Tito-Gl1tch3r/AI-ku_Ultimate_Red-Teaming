package org.ryuu.gdx.mmkv.preferences.android;

import com.badlogic.gdx.Preferences;
import com.tencent.mmkv.MMKV;

import java.util.Map;

public class MMKVPreferences implements Preferences {
    private final MMKV mmkv;

    public MMKVPreferences(String name) {
        mmkv = MMKV.mmkvWithID(name, MMKV.MULTI_PROCESS_MODE);
    }

    @Override
    public Preferences putBoolean(String key, boolean val) {
        mmkv.putBoolean(key, val);
        return this;
    }

    @Override
    public Preferences putInteger(String key, int val) {
        mmkv.putInt(key, val);
        return this;
    }

    @Override
    public Preferences putLong(String key, long val) {
        mmkv.putLong(key, val);
        return this;
    }

    @Override
    public Preferences putFloat(String key, float val) {
        mmkv.putFloat(key, val);
        return this;
    }

    @Override
    public Preferences putString(String key, String val) {
        mmkv.putString(key, val);
        return this;
    }

    @Override
    public Preferences put(Map<String, ?> vals) {
        for (Map.Entry<String, ?> val : vals.entrySet()) {
            if (val.getValue() instanceof Boolean) {
                putBoolean(val.getKey(), (Boolean) val.getValue());
            } else if (val.getValue() instanceof Integer) {
                putInteger(val.getKey(), (Integer) val.getValue());
            } else if (val.getValue() instanceof Long) {
                putLong(val.getKey(), (Long) val.getValue());
            } else if (val.getValue() instanceof String) {
                putString(val.getKey(), (String) val.getValue());
            } else if (val.getValue() instanceof Float) {
                putFloat(val.getKey(), (Float) val.getValue());
            }
        }
        return this;
    }

    @Override
    public boolean getBoolean(String key) {
        return false;
    }

    @Override
    public int getInteger(String key) {
        return mmkv.getInt(key, 0);
    }

    @Override
    public long getLong(String key) {
        return mmkv.getLong(key, 0L);
    }

    @Override
    public float getFloat(String key) {
        return mmkv.getFloat(key, 0.0f);
    }

    @Override
    public String getString(String key) {
        return mmkv.getString(key, "");
    }

    @Override
    public boolean getBoolean(String key, boolean defValue) {
        return mmkv.getBoolean(key, false);
    }

    @Override
    public int getInteger(String key, int defValue) {
        return mmkv.getInt(key, defValue);
    }

    @Override
    public long getLong(String key, long defValue) {
        return mmkv.getLong(key, defValue);
    }

    @Override
    public float getFloat(String key, float defValue) {
        return mmkv.getFloat(key, defValue);
    }

    @Override
    public String getString(String key, String defValue) {
        return mmkv.getString(key, defValue);
    }

    /**
     * @deprecated Intentionally Not Supported. <br>
     * Use allKeys() instead, getAll() not implement because type-erasure inside mmkv
     */
    @Deprecated
    @Override
    public Map<String, ?> get() {
        return mmkv.getAll();
    }

    @Override
    public boolean contains(String key) {
        return mmkv.contains(key);
    }

    @Override
    public void clear() {
        mmkv.clear();
    }

    @Override
    public void remove(String key) {
        mmkv.remove(key);
    }

    /**
     * @deprecated MMKV don't need to flush
     */
    @Deprecated
    @Override
    public void flush() {
    }
}
