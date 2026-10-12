package cn.wanghw.utils;

import java.util.HashMap;

public class HashMapUtils {
    public static String dumpString(HashMap<String, String> hashMap) {
        return dumpString(hashMap, true);
    }

    public static String dumpString(HashMap<String, String> hashMap, boolean oneline) {
        return dumpString(hashMap, oneline, true, false);
    }

    public static String dumpString(HashMap<String, String> hashMap, boolean oneline, boolean newLine, boolean ignoreNull) {
        if (hashMap == null || hashMap.isEmpty()) {
            return "";
        }
        StringBuilder result = new StringBuilder();
        Object[] allKey = hashMap.keySet().toArray();
        for (int i = 0; i < allKey.length; i++) {
            if (allKey[i] == null) {
                continue;
            }
            String key = allKey[i].toString();
            String val = hashMap.get(key);
            if (ignoreNull && (val == null || val.equals(""))) {
                continue;
            }
            if (val != null && val.length() > SpiderLimits.maxStringChars()) {
                val = val.substring(0, SpiderLimits.maxStringChars()) + "...";
            }
            if (SpiderLimits.lowMemory() || result.length() >= SpiderLimits.maxResultChars()) {
                result.append("... truncated");
                break;
            }
            result.append(key).append(" = ").append(val);
            result.append(oneline ? (i + 1 == allKey.length ? "" : ", ") : "\r\n");
        }
        if (result.length() >= 2 && result.charAt(result.length() - 2) == ',' && result.charAt(result.length() - 1) == ' ') {
            result.setLength(result.length() - 2);
        }
        if (result.length() > 0 && oneline && newLine) {
            result.append("\r\n");
        }
        return result.toString();
    }

}
