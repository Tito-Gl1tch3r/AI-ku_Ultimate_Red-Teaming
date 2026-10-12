using ZoneTree.Segments.Block;

namespace ZoneTree.Collections;

public delegate int ReadEntriesDelegate<TKey, TValue>(
    long startIndex,
    int count,
    TKey[] keys,
    TValue[] values,
    int destinationIndex,
    BlockPin blockPin);

public sealed class PrefetchingSeekableIterator<TKey, TValue> : ISeekableIterator<TKey, TValue>
{
  readonly IIndexedReader<TKey, TValue> IndexedReader;

  readonly ReadEntriesDelegate<TKey, TValue> ReadEntries;

  readonly long Length;

  readonly int PrefetchSize;

  readonly BlockPin blockPin = new();

  readonly TKey[] keys;

  readonly TValue[] values;

  long position = -1;

  long bufferStart = -1;

  int bufferLength;

  bool fillBackwards;

  public TKey CurrentKey
  {
    get
    {
      EnsureHasCurrent();
      EnsureBufferContainsPosition();
      return keys[(int)(position - bufferStart)];
    }
  }

  public TValue CurrentValue
  {
    get
    {
      EnsureHasCurrent();
      EnsureBufferContainsPosition();
      return values[(int)(position - bufferStart)];
    }
  }

  public bool HasCurrent => position >= 0 && position < Length;

  public bool IsBeginningOfAPart => IndexedReader.IsBeginningOfAPart(position);

  public bool IsEndOfAPart => IndexedReader.IsEndOfAPart(position);

  /// <summary>
  /// All Indexed Readers are always fully frozen.
  /// </summary>
  public bool IsFullyFrozen => true;

  public PrefetchingSeekableIterator(
      IIndexedReader<TKey, TValue> indexedReader,
      ReadEntriesDelegate<TKey, TValue> readEntries,
      int prefetchSize,
      bool contributeToTheBlockCache = false)
  {
    IndexedReader = indexedReader;
    ReadEntries = readEntries;
    Length = indexedReader.Length;
    PrefetchSize = prefetchSize;
    keys = new TKey[prefetchSize];
    values = new TValue[prefetchSize];
    blockPin.ContributeToTheBlockCache = contributeToTheBlockCache;
  }

  public bool Next()
  {
    if (position >= Length - 1)
      return false;
    ++position;
    fillBackwards = false;
    return true;
  }

  public bool Prev()
  {
    if (position < 1)
      return false;
    --position;
    fillBackwards = true;
    return true;
  }

  public bool SeekBegin()
  {
    position = 0;
    fillBackwards = false;
    return HasCurrent;
  }

  public bool SeekEnd()
  {
    position = Length - 1;
    fillBackwards = true;
    return HasCurrent;
  }

  public bool SeekToLastSmallerOrEqualElement(in TKey key)
  {
    position = IndexedReader.GetLastSmallerOrEqualPosition(key);
    fillBackwards = true;
    return HasCurrent;
  }

  public bool SeekToFirstGreaterOrEqualElement(in TKey key)
  {
    position = IndexedReader.GetFirstGreaterOrEqualPosition(key);
    fillBackwards = false;
    return HasCurrent;
  }

  public void Skip(long offset)
  {
    position += offset;
    fillBackwards = offset < 0;
  }

  public int GetPartIndex() => IndexedReader.GetPartIndex(position);

  void EnsureHasCurrent()
  {
    if (!HasCurrent)
      throw new IndexOutOfRangeException("Iterator is not in a valid position. Have you forgotten to call Next() or Prev()?");
  }

  void EnsureBufferContainsPosition()
  {
    if (position >= bufferStart && position < bufferStart + bufferLength)
      return;

    var start = fillBackwards
        ? Math.Max(0, position - PrefetchSize + 1)
        : position;
    var count = (int)Math.Min(PrefetchSize, Length - start);
    bufferLength = ReadEntries(
        start,
        count,
        keys,
        values,
        0,
        blockPin);
    bufferStart = start;

    if (position < bufferStart || position >= bufferStart + bufferLength)
      throw new IndexOutOfRangeException("Iterator is not in a valid position.");
  }
}
