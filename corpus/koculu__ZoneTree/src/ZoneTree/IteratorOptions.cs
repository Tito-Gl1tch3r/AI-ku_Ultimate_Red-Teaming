using ZoneTree.Options;

namespace ZoneTree;

/// <summary>
/// Configures runtime iterator behavior.
/// </summary>
public sealed class IteratorOptions
{
  /// <summary>
  /// Defines iterator refresh and snapshot behavior.
  /// Default value is <see cref="IteratorType.AutoRefresh"/>.
  /// </summary>
  public IteratorType IteratorType { get; set; } = IteratorType.AutoRefresh;

  /// <summary>
  /// If true, deleted records are included in iteration.
  /// </summary>
  public bool IncludeDeletedRecords { get; set; }

  /// <summary>
  /// If true, disk segment reads performed by the iterator contribute to the
  /// block cache.
  /// </summary>
  public bool ContributeToTheBlockCache { get; set; }

  /// <summary>
  /// Gets or sets the number of sequential disk-segment records the iterator
  /// may prefetch at once. Values less than two disable prefetching.
  /// Default value is 0.
  /// </summary>
  public int DiskSegmentPrefetchSize { get; set; } =
      IteratorDefaultValues.DiskSegmentPrefetchSize;
}
