using ZoneTree.Comparers;
using ZoneTree.Hashers;
using ZoneTree.Options;

namespace ZoneTree.UnitTests;

public sealed class MutableSegmentBloomFilterTests
{
  [Test]
  public void FindsInsertedKeysAndRejectsMissingKeys()
  {
    var dataPath = "data/MutableSegmentBloomFilterFindsInsertedKeys";
    DeleteDirectory(dataPath);
    using (var zoneTree = new ZoneTreeFactory<long, long>()
        .Configure(options => options.AllowUnsafeOptionValues = true)
        .SetMutableSegmentMaxItemCount(10_000)
        .SetDataDirectory(dataPath)
        .SetWriteAheadLogDirectory(dataPath)
        .OpenOrCreate())
    {
      for (var i = 1L; i <= 1_000; ++i)
        zoneTree.Upsert(i, i * 2);

      Assert.Multiple(() =>
      {
        for (var i = 1L; i <= 1_000; ++i)
        {
          Assert.That(zoneTree.TryGet(i, out var value), Is.True);
          Assert.That(value, Is.EqualTo(i * 2));
        }

        for (var i = 1_001L; i <= 2_000; ++i)
          Assert.That(zoneTree.TryGet(i, out _), Is.False);
      });
    }

    DeleteDirectory(dataPath);
  }

  [Test]
  public void ConcurrentWritesDoNotCreateFalseNegatives()
  {
    const int itemCount = 100_000;
    var dataPath = "data/MutableSegmentBloomFilterConcurrentWrites";
    DeleteDirectory(dataPath);
    using (var zoneTree = new ZoneTreeFactory<int, int>()
        .Configure(options => options.AllowUnsafeOptionValues = true)
        .SetMutableSegmentMaxItemCount(itemCount + 1)
        .SetDataDirectory(dataPath)
        .SetWriteAheadLogDirectory(dataPath)
        .OpenOrCreate())
    {
      Parallel.For(1, itemCount + 1, i => zoneTree.Upsert(i, i));

      Assert.Multiple(() =>
      {
        for (var i = 1; i <= itemCount; ++i)
        {
          Assert.That(zoneTree.TryGet(i, out var value), Is.True);
          Assert.That(value, Is.EqualTo(i));
        }
      });
    }

    DeleteDirectory(dataPath);
  }

  [Test]
  public void CanDisableBloomFilter()
  {
    var dataPath = "data/MutableSegmentBloomFilterDisabled";
    DeleteDirectory(dataPath);
    using (var zoneTree = new ZoneTreeFactory<int, int>()
        .SetMutableSegmentBloomFilterBitsPerItem(0)
        .SetDataDirectory(dataPath)
        .SetWriteAheadLogDirectory(dataPath)
        .OpenOrCreate())
    {
      zoneTree.Upsert(1, 2);

      Assert.Multiple(() =>
      {
        Assert.That(zoneTree.TryGet(1, out var value), Is.True);
        Assert.That(value, Is.EqualTo(2));
        Assert.That(zoneTree.TryGet(2, out _), Is.False);
      });
    }

    DeleteDirectory(dataPath);
  }

  [Test]
  public void UsesConfiguredHasherForComparerEquivalentKeys()
  {
    var dataPath = "data/MutableSegmentBloomFilterConfiguredHasher";
    var hasher = new TrackingOrdinalIgnoreCaseKeyHasher();
    DeleteDirectory(dataPath);
    using (var zoneTree = new ZoneTreeFactory<string, int>()
        .SetComparer(new StringOrdinalIgnoreCaseComparerAscending())
        .SetKeyHasher(hasher)
        .SetDataDirectory(dataPath)
        .SetWriteAheadLogDirectory(dataPath)
        .OpenOrCreate())
    {
      hasher.Reset();
      zoneTree.Upsert("key", 42);

      Assert.Multiple(() =>
      {
        Assert.That(zoneTree.TryGet("KEY", out var value), Is.True);
        Assert.That(value, Is.EqualTo(42));
        Assert.That(hasher.CallCount, Is.GreaterThanOrEqualTo(2));
      });
    }

    DeleteDirectory(dataPath);
  }

  [Test]
  public void MemoryKeysUseContentHasher()
  {
    var dataPath = "data/MutableSegmentBloomFilterMemoryKeys";
    DeleteDirectory(dataPath);
    using (var zoneTree = new ZoneTreeFactory<Memory<byte>, int>()
        .SetDataDirectory(dataPath)
        .SetWriteAheadLogDirectory(dataPath)
        .OpenOrCreate())
    {
      Memory<byte> storedKey = new byte[] { 1, 2, 3, 4 };
      Memory<byte> equivalentKey = new byte[] { 1, 2, 3, 4 };
      zoneTree.Upsert(storedKey, 42);

      Assert.Multiple(() =>
      {
        Assert.That(zoneTree.TryGet(equivalentKey, out var value), Is.True);
        Assert.That(value, Is.EqualTo(42));
      });
    }

    DeleteDirectory(dataPath);
  }

  static void DeleteDirectory(string dataPath)
  {
    if (Directory.Exists(dataPath))
      Directory.Delete(dataPath, recursive: true);
  }

  sealed class TrackingOrdinalIgnoreCaseKeyHasher : IKeyHasher<string>
  {
    int Calls;

    public int CallCount => Volatile.Read(ref Calls);

    public int GetHashCode(in string key)
    {
      Interlocked.Increment(ref Calls);
      return StringComparer.OrdinalIgnoreCase.GetHashCode(key);
    }

    public void Reset()
    {
      Volatile.Write(ref Calls, 0);
    }
  }
}
