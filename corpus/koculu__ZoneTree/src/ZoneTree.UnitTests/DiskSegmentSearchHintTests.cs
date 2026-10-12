using ZoneTree.Collections;
using ZoneTree.Comparers;
using ZoneTree.Hashers;
using ZoneTree.Options;
using ZoneTree.Segments.Block;
using ZoneTree.Segments.Disk;
using ZoneTree.Serializers;

namespace ZoneTree.UnitTests;

public sealed class DiskSegmentSearchHintTests
{
  [Test]
  public void DefaultPrefetchSizeIs16()
  {
    Assert.That(DiskSegmentDefaultValues.SearchHintPrefetchSize, Is.EqualTo(16));
    Assert.That(new DiskSegmentOptions().SearchHintPrefetchSize, Is.EqualTo(16));
  }

  [Test]
  public void ZeroDisablesSearchHintPrefetch()
  {
    using var segment = CreateSegment(0);

    AssertGet(segment, 0);
    AssertGet(segment, 1);
    AssertGet(segment, 2);

    Assert.That(segment.ReadEntriesCounts, Is.Empty);
  }

  [TestCase(1)]
  [TestCase(7)]
  [TestCase(16)]
  public void ConfiguredSizeControlsForwardPrefetch(int prefetchSize)
  {
    using var segment = CreateSegment(prefetchSize, 64);

    AssertGet(segment, 0);
    AssertGet(segment, 1);
    AssertGet(segment, 2);

    Assert.That(segment.ReadEntriesCounts, Is.EqualTo(new[] { prefetchSize }));
    AssertGet(segment, 3);
    if (prefetchSize > 1)
      Assert.That(segment.ReadEntriesCounts, Has.Count.EqualTo(1));
  }

  [Test]
  public void PrefetchIsClippedAtSegmentBoundary()
  {
    using var segment = CreateSegment(64, 5);

    AssertGet(segment, 2);
    AssertGet(segment, 3);
    AssertGet(segment, 4);

    Assert.That(segment.ReadEntriesCounts, Is.EqualTo(new[] { 1 }));
  }

  [Test]
  public void ReverseSearchPrefetchesConfiguredWindow()
  {
    using var segment = CreateSegment(4, 16);

    AssertGet(segment, 9);
    AssertGet(segment, 8);
    AssertGet(segment, 7);
    AssertGet(segment, 6);

    Assert.That(segment.ReadEntriesCounts, Is.EqualTo(new[] { 4 }));
  }

  [Test]
  public void NonSequentialSearchesDoNotPrefetch()
  {
    using var segment = CreateSegment(16, 64);

    AssertGet(segment, 0);
    AssertGet(segment, 2);
    AssertGet(segment, 4);
    AssertGet(segment, 6);

    Assert.That(segment.ReadEntriesCounts, Is.Empty);
  }

  [Test]
  public void PrefetchReleasesPinnedBlocks()
  {
    using var segment = CreateSegment(16, 64);

    AssertGet(segment, 0);
    AssertGet(segment, 1);
    AssertGet(segment, 2);

    Assert.That(segment.LastBlockPin, Is.Not.Null);
    Assert.That(segment.LastBlockPin.Device1, Is.Null);
    Assert.That(segment.LastBlockPin.Device2, Is.Null);
  }

  [Test]
  public void FailedPrefetchReleasesPinnedBlocks()
  {
    using var segment = CreateSegment(16, 64);
    segment.ThrowFromReadEntries = true;

    AssertGet(segment, 0);
    AssertGet(segment, 1);
    Assert.Throws<InvalidOperationException>(() => TryGet(segment, 2, out _));

    Assert.That(segment.LastBlockPin, Is.Not.Null);
    Assert.That(segment.LastBlockPin.Device1, Is.Null);
    Assert.That(segment.LastBlockPin.Device2, Is.Null);
  }

  static void AssertGet(TestDiskSegment segment, int key)
  {
    Assert.That(TryGet(segment, key, out var value), Is.True);
    Assert.That(value, Is.EqualTo(key + 100));
  }

  static bool TryGet(TestDiskSegment segment, int key, out int value)
  {
    var keyHashProvider = new KeyHashProvider<int>();
    return segment.TryGet(key, out value, ref keyHashProvider);
  }

  static TestDiskSegment CreateSegment(
      int searchHintPrefetchSize,
      int length = 32)
  {
    var options = new ZoneTreeOptions<int, int>
    {
      Comparer = new Int32ComparerAscending(),
      KeySerializer = new Int32Serializer(),
      ValueSerializer = new Int32Serializer(),
      DiskSegmentOptions = new DiskSegmentOptions
      {
        SearchHintPrefetchSize = searchHintPrefetchSize
      }
    };
    return new TestDiskSegment(options, length);
  }

  sealed class TestDiskSegment : DiskSegment<int, int>
  {
    public readonly List<int> ReadEntriesCounts = [];

    public BlockPin LastBlockPin;

    public bool ThrowFromReadEntries;

    public override int ReadBufferCount => 0;

    public TestDiskSegment(
        ZoneTreeOptions<int, int> options,
        int length) : base(1, options)
    {
      Length = length;
    }

    protected override int ReadKey(long index, BlockPin blockPin)
    {
      return checked((int)index);
    }

    protected override int ReadValue(long index, BlockPin blockPin)
    {
      return checked((int)index + 100);
    }

    public override int ReadEntries(
        long startIndex,
        int count,
        int[] keys,
        int[] values,
        int destinationIndex,
        BlockPin blockPin)
    {
      if (startIndex < 0 || startIndex >= Length || count <= 0)
        return 0;

      count = (int)Math.Min(count, Length - startIndex);
      ReadEntriesCounts.Add(count);
      LastBlockPin = blockPin;
      blockPin?.SetDevice1(new DecompressedBlock(
          0,
          Memory<byte>.Empty,
          CompressionMethod.None,
          0));
      blockPin?.SetDevice2(new DecompressedBlock(
          1,
          Memory<byte>.Empty,
          CompressionMethod.None,
          0));
      if (ThrowFromReadEntries)
        throw new InvalidOperationException("Test read failure.");
      for (var i = 0; i < count; ++i)
      {
        var key = checked((int)startIndex + i);
        keys[destinationIndex + i] = key;
        values[destinationIndex + i] = key + 100;
      }
      return count;
    }

    protected override void DeleteDevices()
    {
    }

    public override int ReleaseReadBuffers(long ticks)
    {
      return 0;
    }

    public override void SetDefaultSparseArray(
        IReadOnlyList<SparseArrayEntry<int, int>> defaultSparseArray)
    {
      SparseArray = defaultSparseArray;
    }
  }
}
