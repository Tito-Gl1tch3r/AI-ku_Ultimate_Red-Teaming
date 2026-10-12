package cn.wanghw.utils;

import cn.wanghw.IHeapHolder;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;

/**
 * Shared helpers for both heap backends. Reflection is cached so the
 * package-private getChars/getBytes on PrimitiveArrayDump stay usable
 * without pulling every array element into a List of Strings.
 */
public final class HeapHolderSupport {
    private static final Class[] INT_INT = new Class[]{Integer.TYPE, Integer.TYPE};
    private static final Class[] NO_ARGS = new Class[0];
    private static final HashMap methodCache = new HashMap();

    private HeapHolderSupport() {
    }

    public static Iterator instancesIterator(Object javaClass) {
        if (javaClass == null) {
            return Collections.EMPTY_LIST.iterator();
        }
        Object it = invoke(javaClass, "getInstancesIterator", NO_ARGS, null);
        if (it instanceof Iterator) {
            return (Iterator) it;
        }
        Object list = invoke(javaClass, "getInstances", NO_ARGS, null);
        if (list instanceof List) {
            return ((List) list).iterator();
        }
        return Collections.EMPTY_LIST.iterator();
    }

    public static void closeQuietly(Object obj) {
        if (obj == null) {
            return;
        }
        invoke(obj, "close", NO_ARGS, null);
    }

    public static String truncate(String text) {
        if (text == null) {
            return "";
        }
        int maxChars = SpiderLimits.maxStringChars();
        if (text.length() <= maxChars) {
            return text;
        }
        return text.substring(0, maxChars) + "...";
    }

    public static int toInt(Object obj, int def) {
        if (obj instanceof Number) {
            return ((Number) obj).intValue();
        }
        return def;
    }

    public static int arrayLength(Object array) {
        if (array == null) {
            return -1;
        }
        Object len = invoke(array, "getLength", NO_ARGS, null);
        if (len instanceof Integer) {
            return ((Integer) len).intValue();
        }
        return -1;
    }

    public static String javaClassName(Object instance) {
        if (instance == null) {
            return null;
        }
        Object javaClass = invoke(instance, "getJavaClass", NO_ARGS, null);
        Object name = invoke(javaClass, "getName", NO_ARGS, null);
        return name == null ? null : name.toString();
    }

    public static int estimateCharLength(Object valueArray, Object coderObj, Object offsetObj, Object countObj) {
        if (valueArray == null) {
            return 0;
        }
        int arrLen = arrayLength(valueArray);
        if (arrLen < 0) {
            return -1;
        }
        int off = toInt(offsetObj, 0);
        if (off < 0) {
            off = 0;
        }
        int raw = countObj != null ? toInt(countObj, arrLen) : arrLen - off;
        if (raw < 0) {
            raw = 0;
        }
        int coder = toInt(coderObj, 0);
        String type = javaClassName(valueArray);
        if ("byte[]".equals(type) && coder == 1) {
            return raw / 2;
        }
        return raw;
    }

    public static String decodeArraySlice(Object valueArray, Object coderObj, Object offsetObj, int maxChars) {
        if (valueArray == null || maxChars <= 0) {
            return null;
        }
        int off = toInt(offsetObj, 0);
        if (off < 0) {
            off = 0;
        }
        int arrLen = arrayLength(valueArray);
        if (arrLen <= 0) {
            return "";
        }
        String type = javaClassName(valueArray);
        int coder = toInt(coderObj, 0);
        if ("char[]".equals(type)) {
            int take = maxChars;
            if (off + take > arrLen) {
                take = arrLen - off;
            }
            if (take <= 0) {
                return "";
            }
            char[] chars = getChars(valueArray, off, take);
            return chars == null ? null : new String(chars);
        }
        if ("byte[]".equals(type)) {
            int byteTake = coder == 1 ? maxChars * 2 : maxChars;
            if (off + byteTake > arrLen) {
                byteTake = arrLen - off;
            }
            if (byteTake <= 0) {
                return "";
            }
            byte[] bytes = getBytes(valueArray, off, byteTake);
            if (bytes == null) {
                return null;
            }
            return coder == 1 ? utf16le(bytes) : latin1(bytes);
        }
        return null;
    }

    public static char[] getChars(Object array, int offset, int length) {
        if (array == null || length <= 0) {
            return new char[0];
        }
        Object result = invoke(array, "getChars", INT_INT,
                new Object[]{Integer.valueOf(offset), Integer.valueOf(length)});
        if (result instanceof char[]) {
            return (char[]) result;
        }
        return charsFromValues(array, offset, length);
    }

    public static byte[] getBytes(Object array, int offset, int length) {
        if (array == null || length <= 0) {
            return new byte[0];
        }
        Object result = invoke(array, "getBytes", INT_INT,
                new Object[]{Integer.valueOf(offset), Integer.valueOf(length)});
        if (result instanceof byte[]) {
            return (byte[]) result;
        }
        return bytesFromValues(array, offset, length);
    }

    public static List<String> findFieldsByKeywords(IHeapHolder heapHolder, Object clazz, List keywordList) {
        List<String> fieldList = new LinkedList<String>();
        if (heapHolder == null || clazz == null || keywordList == null) {
            return fieldList;
        }
        HashSet seen = new HashSet();
        int hops = 0;
        while (clazz != null && hops++ < SpiderLimits.MAX_SUPERCLASS_HOPS) {
            String cn = heapHolder.getClassName(clazz);
            if (cn == null || Object.class.getName().equals(cn)) {
                break;
            }
            if (!seen.add(cn)) {
                break;
            }
            if (heapHolder.isArray(clazz)) {
                break;
            }
            List fields = heapHolder.getFields(clazz);
            if (fields != null) {
                for (int i = 0; i < fields.size(); i++) {
                    String name = heapHolder.getFieldName(fields.get(i));
                    if (name == null) {
                        continue;
                    }
                    String lower = name.toLowerCase();
                    for (int k = 0; k < keywordList.size(); k++) {
                        if (lower.indexOf(String.valueOf(keywordList.get(k))) >= 0) {
                            fieldList.add(name);
                            break;
                        }
                    }
                }
            }
            clazz = heapHolder.getSuperClass(clazz);
        }
        return fieldList;
    }

    private static char[] charsFromValues(Object array, int offset, int length) {
        List values = valuesIfSmall(array);
        if (values == null) {
            return null;
        }
        int end = Math.min(offset + length, values.size());
        if (offset < 0) {
            offset = 0;
        }
        if (end < offset) {
            return new char[0];
        }
        char[] chars = new char[end - offset];
        for (int i = offset; i < end; i++) {
            Object v = values.get(i);
            if (v != null) {
                String s = v.toString();
                if (s.length() > 0) {
                    chars[i - offset] = s.charAt(0);
                }
            }
        }
        return chars;
    }

    private static byte[] bytesFromValues(Object array, int offset, int length) {
        List values = valuesIfSmall(array);
        if (values == null) {
            return null;
        }
        int end = Math.min(offset + length, values.size());
        if (offset < 0) {
            offset = 0;
        }
        if (end < offset) {
            return new byte[0];
        }
        byte[] bytes = new byte[end - offset];
        for (int i = offset; i < end; i++) {
            Object v = values.get(i);
            if (v != null) {
                try {
                    bytes[i - offset] = (byte) Integer.parseInt(v.toString());
                } catch (NumberFormatException ignored) {
                }
            }
        }
        return bytes;
    }

    private static List valuesIfSmall(Object array) {
        int arrLen = arrayLength(array);
        if (arrLen < 0 || arrLen > SpiderLimits.maxPrimitiveArrayFallback()) {
            return null;
        }
        Object values = invoke(array, "getValues", NO_ARGS, null);
        return values instanceof List ? (List) values : null;
    }

    private static String latin1(byte[] bytes) {
        char[] chars = new char[bytes.length];
        for (int i = 0; i < bytes.length; i++) {
            chars[i] = (char) (bytes[i] & 0xff);
        }
        return new String(chars);
    }

    private static String utf16le(byte[] bytes) {
        int n = bytes.length / 2;
        char[] chars = new char[n];
        for (int i = 0; i < n; i++) {
            chars[i] = (char) ((bytes[i * 2] & 0xff) | ((bytes[i * 2 + 1] & 0xff) << 8));
        }
        return new String(chars);
    }

    private static Object invoke(Object target, String name, Class[] params, Object[] args) {
        if (target == null) {
            return null;
        }
        Method method = findMethod(target, name, params);
        if (method == null) {
            return null;
        }
        try {
            return method.invoke(target, args);
        } catch (Throwable ignored) {
            return null;
        }
    }

    private static synchronized Method findMethod(Object target, String name, Class[] params) {
        Class cls = target.getClass();
        String key = cls.getName() + "#" + name + "#" + params.length;
        if (methodCache.containsKey(key)) {
            return (Method) methodCache.get(key);
        }
        Method method = null;
        try {
            method = cls.getMethod(name, params);
            method.setAccessible(true);
        } catch (Throwable ignored) {
            try {
                method = cls.getDeclaredMethod(name, params);
                method.setAccessible(true);
            } catch (Throwable ignored2) {
            }
        }
        methodCache.put(key, method);
        return method;
    }
}
