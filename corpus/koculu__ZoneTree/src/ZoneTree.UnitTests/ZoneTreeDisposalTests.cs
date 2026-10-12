using ZoneTree.Core;
using ZoneTree.Options;

namespace ZoneTree.UnitTests;

public sealed class ZoneTreeDisposalTests
{
  [Test]
  public void DisposeSynchronouslyReleasesLiveIteratorResources()
  {
    var dataPath = "data/DisposeSynchronouslyReleasesLiveIteratorResources";
    DeleteDirectory(dataPath);
    var zoneTree = CreateZoneTree(dataPath);
    zoneTree.Upsert(1, 10);
    zoneTree.Maintenance.MoveMutableSegmentForward();
    zoneTree.Maintenance.StartMergeOperation().Join();
    var iterator = (ZoneTreeIterator<int, int>)zoneTree.CreateIterator(
        IteratorType.NoRefresh);

    Assert.That(iterator.Next(), Is.True);
    Assert.That(iterator.DiskSegment, Is.Not.Null);

    zoneTree.Dispose();

    Assert.Multiple(() =>
    {
      Assert.That(iterator.DiskSegment, Is.Null);
      Assert.That(iterator.BottomSegments, Is.Null);
    });

    iterator.Dispose();
    DeleteDirectory(dataPath);
  }

  static IZoneTree<int, int> CreateZoneTree(string dataPath)
  {
    return new ZoneTreeFactory<int, int>()
        .Configure(options => options.AllowUnsafeOptionValues = true)
        .SetDataDirectory(dataPath)
        .SetWriteAheadLogDirectory(dataPath)
        .OpenOrCreate();
  }

  static void DeleteDirectory(string dataPath)
  {
    if (Directory.Exists(dataPath))
      Directory.Delete(dataPath, recursive: true);
  }
}
