package io.vacco.metolithe.id;

/**
 * Sourced from https://github.com/apache/hive/blob/master/storage-api/src/java/org/apache/hive/common/util/Murmur3.java
 */
@SuppressWarnings("fallthrough")
public class MtMurmur3 {

  public static final int DEFAULT_SEED = 104729;

  // Constants for 32 bit variant
  private static final int C1_32 = 0xcc9e2d51;
  private static final int C2_32 = 0x1b873593;
  private static final int R1_32 = 15;
  private static final int R2_32 = 13;
  private static final int M_32 = 5;
  private static final int N_32 = 0xe6546b64;

  // Constants for 128 bit variant
  private static final long C1 = 0x87c37b91114253d5L;
  private static final long C2 = 0x4cf5ad432745937fL;
  private static final int R1 = 31;
  private static final int R2 = 27;
  private static final int M = 5;
  private static final int N1 = 0x52dce729;

  private static int fmix32(int length, int hash) {
    hash ^= length;
    hash ^= (hash >>> 16);
    hash *= 0x85ebca6b;
    hash ^= (hash >>> 13);
    hash *= 0xc2b2ae35;
    hash ^= (hash >>> 16);

    return hash;
  }

  private static int mix32(int k, int hash) {
    k *= C1_32;
    k = Integer.rotateLeft(k, R1_32);
    k *= C2_32;
    hash ^= k;
    return Integer.rotateLeft(hash, R2_32) * M_32 + N_32;
  }

  public static int hash32(byte[] data, int offset, int length, int seed) {
    int hash = seed;
    final int nblocks = length >> 2;

    for (int i = 0; i < nblocks; i++) {
      int i_4 = i << 2;
      int k = (data[offset + i_4] & 0xff)
        | ((data[offset + i_4 + 1] & 0xff) << 8)
        | ((data[offset + i_4 + 2] & 0xff) << 16)
        | ((data[offset + i_4 + 3] & 0xff) << 24);

      hash = mix32(k, hash);
    }

    int idx = nblocks << 2;
    int k1 = 0;
    switch (length - idx) {
      case 3:
        k1 ^= data[offset + idx + 2] << 16;
      case 2:
        k1 ^= data[offset + idx + 1] << 8;
      case 1:
        k1 ^= data[offset + idx];
        k1 *= C1_32;
        k1 = Integer.rotateLeft(k1, R1_32);
        k1 *= C2_32;
        hash ^= k1;
    }

    return fmix32(length, hash);
  }

  public static int hash32(byte[] data, int seed) {
    return hash32(data, 0, data.length, seed);
  }

  private static long fmix64(long h) {
    h ^= (h >>> 33);
    h *= 0xff51afd7ed558ccdL;
    h ^= (h >>> 33);
    h *= 0xc4ceb9fe1a85ec53L;
    h ^= (h >>> 33);
    return h;
  }

  public static long hash64(byte[] data, int offset, int length, int seed) {
    long hash = seed;
    final int nblocks = length >> 3;

    for (int i = 0; i < nblocks; i++) {
      final int i8 = i << 3;
      long k = ((long) data[offset + i8] & 0xff)
        | (((long) data[offset + i8 + 1] & 0xff) << 8)
        | (((long) data[offset + i8 + 2] & 0xff) << 16)
        | (((long) data[offset + i8 + 3] & 0xff) << 24)
        | (((long) data[offset + i8 + 4] & 0xff) << 32)
        | (((long) data[offset + i8 + 5] & 0xff) << 40)
        | (((long) data[offset + i8 + 6] & 0xff) << 48)
        | (((long) data[offset + i8 + 7] & 0xff) << 56);

      k *= C1;
      k = Long.rotateLeft(k, R1);
      k *= C2;
      hash ^= k;
      hash = Long.rotateLeft(hash, R2) * M + N1;
    }

    long k1 = 0;
    int tailStart = nblocks << 3;
    switch (length - tailStart) {
      case 7:
        k1 ^= ((long) data[offset + tailStart + 6] & 0xff) << 48;
      case 6:
        k1 ^= ((long) data[offset + tailStart + 5] & 0xff) << 40;
      case 5:
        k1 ^= ((long) data[offset + tailStart + 4] & 0xff) << 32;
      case 4:
        k1 ^= ((long) data[offset + tailStart + 3] & 0xff) << 24;
      case 3:
        k1 ^= ((long) data[offset + tailStart + 2] & 0xff) << 16;
      case 2:
        k1 ^= ((long) data[offset + tailStart + 1] & 0xff) << 8;
      case 1:
        k1 ^= ((long) data[offset + tailStart] & 0xff);
        k1 *= C1;
        k1 = Long.rotateLeft(k1, R1);
        k1 *= C2;
        hash ^= k1;
    }

    hash ^= length;
    hash = fmix64(hash);

    return hash;
  }
}
