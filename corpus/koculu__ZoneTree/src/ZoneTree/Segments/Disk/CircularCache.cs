using System;
using System.Numerics;
using System.Runtime.CompilerServices;

namespace ZoneTree.Segments.Disk;

public sealed class CircularCache<TDataType>
{
  const ulong HashMultiplier = 0x9E3779B97F4A7C15UL;

  public sealed class CacheAndCacheSize
  {
    public int CacheSize;
    public CachedRecord[] circularBuffer;
    internal int HashShift;
  }

  public sealed class CachedRecord
  {
    public long Index;
    public TDataType Record;
    public long LastAccess;
    public bool IsExpired(long ticks) => LastAccess < ticks;
  }

  CacheAndCacheSize Cache;

  public int RecordLifeTimeInMillisecond { get; set; } = 10000;

  public CircularCache(int cacheSize, int recordLifeTimeInMillisecond)
  {
    RecordLifeTimeInMillisecond = recordLifeTimeInMillisecond;
    Cache = new CacheAndCacheSize()
    {
      CacheSize = cacheSize,
      circularBuffer = new CachedRecord[cacheSize],
      HashShift = GetHashShift(cacheSize)
    };
  }

  public bool TryGet(long index, out TDataType key)
  {
    var cache = Cache;
    var cacheSize = cache.CacheSize;
    if (cacheSize < 1)
    {
      key = default;
      return false;
    }
    var circularBuffer = cache.circularBuffer;
    var circularIndex = GetSlotIndex(index, cache);
    var cacheRecord = circularBuffer[circularIndex];
    if (cacheRecord != null && cacheRecord.Index == index)
    {
      key = cacheRecord.Record;
      cacheRecord.LastAccess = Environment.TickCount64;
      return true;
    }
    key = default;
    return false;
  }

  public bool TryAdd(long index, ref TDataType key)
  {
    var cache = Cache;
    var cacheSize = cache.CacheSize;
    if (cacheSize < 1) return false;
    var circularBuffer = cache.circularBuffer;
    var circularIndex = GetSlotIndex(index, cache);
    var cachedRecord = new CachedRecord
    {
      Index = index,
      Record = key,
      LastAccess = Environment.TickCount64,
    };
    circularBuffer[circularIndex] = cachedRecord;
    return true;
  }

  public int ReleaseInactiveCacheRecords()
  {
    var ticks = Environment.TickCount64 - RecordLifeTimeInMillisecond;
    var circularBuffer = Cache.circularBuffer;
    var len = circularBuffer.Length;
    var totalReleasedRecords = 0;
    for (var i = 0; i < len; ++i)
    {
      var cacheRecord = circularBuffer[i];
      if (cacheRecord == null || !cacheRecord.IsExpired(ticks)) continue;
      circularBuffer[i] = null;
      ++totalReleasedRecords;
    }
    return totalReleasedRecords;
  }

  public void Clear()
  {
    var circularBuffer = Cache.circularBuffer;
    var len = circularBuffer.Length;
    for (var i = 0; i < len; ++i)
    {
      circularBuffer[i] = null;
    }
  }

  [MethodImpl(MethodImplOptions.AggressiveInlining)]
  static int GetSlotIndex(long index, CacheAndCacheSize cache)
  {
    var hash = unchecked((ulong)index * HashMultiplier);
    var hashShift = cache.HashShift;
    if (hashShift != 0)
      return (int)(hash >> hashShift);
    if (cache.CacheSize == 1)
      return 0;
    return (int)Math.BigMul(
        hash,
        (ulong)(uint)cache.CacheSize,
        out _);
  }

  static int GetHashShift(int cacheSize)
  {
    return cacheSize > 1 && BitOperations.IsPow2((uint)cacheSize)
        ? 64 - BitOperations.Log2((uint)cacheSize)
        : 0;
  }
}
