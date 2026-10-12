using System.Runtime.CompilerServices;

namespace ZoneTree.Collections;

/// <summary>
/// A fixed-size Bloom filter supporting concurrent readers and writers.
/// </summary>
public sealed class ConcurrentBloomFilter
{
  const long MaximumBitCount = 1L << 30;

  readonly long[] Words;

  readonly ulong WordMask;

  public ConcurrentBloomFilter(
      int expectedItemCount,
      int bitsPerItem)
  {
    var requestedBitCount = Math.Max(
        64L,
        (long)expectedItemCount * bitsPerItem);
    long bitCount = 64;
    while (bitCount < requestedBitCount && bitCount < MaximumBitCount)
      bitCount <<= 1;

    Words = new long[bitCount >> 6];
    WordMask = (ulong)(Words.Length - 1);
  }

  [MethodImpl(MethodImplOptions.AggressiveInlining)]
  public void Add(int hashCode)
  {
    GetWordAndBitMask(hashCode, out var wordIndex, out var bitMask);
    Interlocked.Or(ref Words[wordIndex], bitMask);
  }

  [MethodImpl(MethodImplOptions.AggressiveInlining)]
  public bool MightContain(int hashCode)
  {
    GetWordAndBitMask(hashCode, out var wordIndex, out var bitMask);
    return (Volatile.Read(ref Words[wordIndex]) & bitMask) == bitMask;
  }

  [MethodImpl(MethodImplOptions.AggressiveInlining)]
  void GetWordAndBitMask(int hashCode, out int wordIndex, out long bitMask)
  {
    var hash = Mix(unchecked((uint)hashCode));
    var firstBit = (int)(hash & 63);
    var bitStep = (int)((hash >> 6) & 31) * 2 + 1;
    var secondBit = (firstBit + bitStep) & 63;
    var thirdBit = (secondBit + bitStep) & 63;

    // Keep all probes in one word so publishing them requires one atomic write.
    wordIndex = (int)((hash >> 11) & WordMask);
    bitMask = unchecked((long)(
        (1UL << firstBit) |
        (1UL << secondBit) |
        (1UL << thirdBit)));
  }

  [MethodImpl(MethodImplOptions.AggressiveInlining)]
  static ulong Mix(uint value)
  {
    unchecked
    {
      var hash = (ulong)value + 0x9E3779B97F4A7C15UL;
      hash = (hash ^ (hash >> 30)) * 0xBF58476D1CE4E5B9UL;
      hash = (hash ^ (hash >> 27)) * 0x94D049BB133111EBUL;
      return hash ^ (hash >> 31);
    }
  }
}
