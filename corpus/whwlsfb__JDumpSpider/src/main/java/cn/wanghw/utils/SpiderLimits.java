package cn.wanghw.utils;

/**
 * Caps that keep full-heap scans from exhausting the analyzer JVM.
 * Memory-sensitive values are recomputed from {@link Runtime} about every
 * 200ms so tight heaps shrink budgets without querying MXBean on every instance.
 */
public final class SpiderLimits {
    public static final int MAX_TOSTRING_DEPTH = 8;
    public static final int MAX_SUPERCLASS_HOPS = 64;

    private static final int MIN_STRING_CHARS = 16 * 1024;
    private static final int MAX_STRING_CHARS = 2 * 1024 * 1024;
    private static final int DEFAULT_STRING_CHARS = 1024 * 1024;

    private static final int MIN_RESULT_CHARS = 256 * 1024;
    private static final int MAX_RESULT_CHARS = 8 * 1024 * 1024;

    private static final int MIN_INSTANCES_PER_CLASS = 2000;
    private static final int MAX_INSTANCES_PER_CLASS = 200000;

    private static final int MIN_PRIMITIVE_ARRAY_FALLBACK = 1024;
    private static final int MAX_PRIMITIVE_ARRAY_FALLBACK = 65536;

    private static final int MIN_BYTE_ARRAY = 16 * 1024;
    private static final int MAX_BYTE_ARRAY = 1024 * 1024;

    private static final long MB = 1024L * 1024L;
    private static final long REFRESH_INTERVAL_NS = 200L * 1000L * 1000L;

    private static long lastRefreshNs;
    private static long remainingBytes;
    private static long reserveBytes;
    private static int cachedStringChars = DEFAULT_STRING_CHARS;
    private static int cachedResultChars = MAX_RESULT_CHARS;
    private static int cachedInstancesPerClass = MAX_INSTANCES_PER_CLASS;
    private static int cachedPrimitiveArrayFallback = MAX_PRIMITIVE_ARRAY_FALLBACK;
    private static int cachedByteArray = MAX_BYTE_ARRAY;
    private static boolean cachedLowMemory;

    private SpiderLimits() {
    }

    public static int maxStringChars() {
        refreshIfNeeded();
        return cachedStringChars;
    }

    public static int maxResultChars() {
        refreshIfNeeded();
        return cachedResultChars;
    }

    public static int maxInstancesPerClass() {
        refreshIfNeeded();
        return cachedInstancesPerClass;
    }

    public static int maxPrimitiveArrayFallback() {
        refreshIfNeeded();
        return cachedPrimitiveArrayFallback;
    }

    public static int maxByteArray() {
        refreshIfNeeded();
        return cachedByteArray;
    }

    public static boolean lowMemory() {
        refreshIfNeeded();
        return cachedLowMemory;
    }

    public static boolean allowMoreInstances(int visited) {
        return visited < maxInstancesPerClass() && !lowMemory();
    }

    public static synchronized void refresh() {
        refreshNow();
    }

    public static String describe() {
        refreshIfNeeded();
        return "remaining=" + (remainingBytes / MB) + "MB, reserve=" + (reserveBytes / MB)
                + "MB, string=" + cachedStringChars + ", result=" + cachedResultChars
                + ", instances=" + cachedInstancesPerClass;
    }

    private static synchronized void refreshIfNeeded() {
        long now = System.nanoTime();
        if (lastRefreshNs != 0L && now - lastRefreshNs < REFRESH_INTERVAL_NS) {
            return;
        }
        refreshNow();
    }

    private static void refreshNow() {
        Runtime rt = Runtime.getRuntime();
        long max = rt.maxMemory();
        long total = rt.totalMemory();
        long free = rt.freeMemory();
        if (max <= 0L || max == Long.MAX_VALUE) {
            max = Math.max(total, 64L * MB);
        }
        remainingBytes = max - (total - free);
        if (remainingBytes < 0L) {
            remainingBytes = 0L;
        }
        reserveBytes = reserveFor(max);
        long usable = remainingBytes > reserveBytes ? remainingBytes - reserveBytes : 0L;
        long fullUsable = Math.max(max / 3L, 32L * MB);
        cachedLowMemory = remainingBytes < reserveBytes;
        cachedStringChars = scale(MIN_STRING_CHARS, DEFAULT_STRING_CHARS, usable, fullUsable);
        if (cachedStringChars > MAX_STRING_CHARS) {
            cachedStringChars = MAX_STRING_CHARS;
        }
        cachedResultChars = scale(MIN_RESULT_CHARS, MAX_RESULT_CHARS, usable, fullUsable);
        cachedInstancesPerClass = scale(MIN_INSTANCES_PER_CLASS, MAX_INSTANCES_PER_CLASS, usable, fullUsable);
        cachedPrimitiveArrayFallback = scale(MIN_PRIMITIVE_ARRAY_FALLBACK, MAX_PRIMITIVE_ARRAY_FALLBACK, usable, fullUsable);
        cachedByteArray = scale(MIN_BYTE_ARRAY, MAX_BYTE_ARRAY, usable, fullUsable);
        lastRefreshNs = System.nanoTime();
    }

    private static long reserveFor(long maxHeap) {
        long reserve = maxHeap / 8L;
        if (reserve < 24L * MB) {
            reserve = 24L * MB;
        }
        if (reserve > 128L * MB) {
            reserve = 128L * MB;
        }
        if (reserve > maxHeap / 2L) {
            reserve = maxHeap / 3L;
        }
        return reserve;
    }

    private static int scale(int min, int maxVal, long usable, long fullUsable) {
        if (usable <= 0L) {
            return min;
        }
        if (usable >= fullUsable) {
            return maxVal;
        }
        return min + (int) (((long) (maxVal - min) * usable) / fullUsable);
    }
}
