using System.Buffers.Binary;
using System.Text;
using RocksDbSharp;

namespace ProfileStore.Benchmark;

public sealed class RocksDbProfileStore : IProfileStoreEngine, IProfileStoreEngineWorker
{
  static readonly Encoding Encoding = Encoding.UTF8;

  string RootDirectory = "";
  RocksDb? Profiles;
  RocksDb? EmailIndex;
  RocksDb? CountryStatusIndex;
  RocksDb? CreatedAtIndex;
  RocksDb? ReputationIndex;
  WriteOptions? WriteOpts;
  int WriteBufferMb;
  int MaxWriteBufferNumber;
  const string CompressionName = "Zstd";

  public string Name => "RocksDB";

  public string DurabilityDescription =>
      $"WAL enabled; five separate RocksDB instances; no WriteBatch across indexes; compression={CompressionName}; write_buffer_size={WriteBufferMb} MB per database; max_write_buffer_number={MaxWriteBufferNumber}.";

  public bool RequiresReadStabilization => true;

  public Task InitializeAsync(BenchmarkConfig config, bool reset, CancellationToken ct)
  {
    RootDirectory = Path.Combine(config.DataDirectory, "rocksdb");
    WriteBufferMb = config.RocksDbWriteBufferMb;
    MaxWriteBufferNumber = config.RocksDbMaxWriteBufferNumber;
    if (reset && Directory.Exists(RootDirectory))
      Directory.Delete(RootDirectory, true);
    Directory.CreateDirectory(RootDirectory);

    Profiles = OpenDb(Path.Combine(RootDirectory, "profiles"));
    EmailIndex = OpenDb(Path.Combine(RootDirectory, "email-index"));
    CountryStatusIndex = OpenDb(Path.Combine(RootDirectory, "country-status-index"));
    CreatedAtIndex = OpenDb(Path.Combine(RootDirectory, "created-at-index"));
    ReputationIndex = OpenDb(Path.Combine(RootDirectory, "reputation-index"));
    WriteOpts = new WriteOptions().SetSync(false);
    return Task.CompletedTask;
  }

  public Task<IProfileStoreEngineWorker> CreateWorkerAsync(CancellationToken ct) =>
      Task.FromResult<IProfileStoreEngineWorker>(new Worker(this));

  public Task InsertBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct)
  {
    foreach (var profile in profiles)
    {
      ct.ThrowIfCancellationRequested();
      var userId = UserIdValue(profile.UserId);
      Profiles!.Put(UserIdKey(profile.UserId), Bytes(ProfileCodec.Serialize(profile)), null, WriteOpts);
      EmailIndex!.Put(Bytes(profile.Email), userId, null, WriteOpts);
      CountryStatusIndex!.Put(Bytes(ProfileKeys.CountryStatus(profile)), userId, null, WriteOpts);
      CreatedAtIndex!.Put(Bytes(ProfileKeys.CreatedAt(profile)), userId, null, WriteOpts);
      ReputationIndex!.Put(Bytes(ProfileKeys.Reputation(profile)), userId, null, WriteOpts);
    }
    return Task.CompletedTask;
  }

  public Task<UserProfile?> GetByUserIdAsync(long userId, CancellationToken ct)
  {
    var value = Profiles!.Get(UserIdKey(userId), null, null);
    return Task.FromResult(value == null ? null : ProfileCodec.Deserialize(Encoding.GetString(value)));
  }

  public Task<UserProfile?> GetByEmailAsync(string email, CancellationToken ct)
  {
    var value = EmailIndex!.Get(Bytes(email), null, null);
    if (value == null)
      return Task.FromResult<UserProfile?>(null);
    return GetByUserIdAsync(ParseUserId(value), ct);
  }

  public Task<IReadOnlyList<UserProfile>> QueryCountryStatusAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct)
  {
    var prefix = ProfileKeys.CountryStatusPrefix(country, status);
    return Task.FromResult(ScanStringIndex(CountryStatusIndex!, prefix, key => key.StartsWith(prefix, StringComparison.Ordinal), limit, ct));
  }

  public Task<IReadOnlyList<long>> ScanCountryStatusIndexAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct)
  {
    var prefix = ProfileKeys.CountryStatusPrefix(country, status);
    return Task.FromResult(ScanStringIndexValues(CountryStatusIndex!, prefix, key => key.StartsWith(prefix, StringComparison.Ordinal), limit, ct));
  }

  public Task<IReadOnlyList<UserProfile>> QueryCreatedAtRangeAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct)
  {
    var start = ProfileKeys.CreatedAt(fromUnixMs, 0);
    var end = ProfileKeys.CreatedAt(toUnixMs, long.MaxValue);
    return Task.FromResult(ScanStringIndex(CreatedAtIndex!, start, key => string.CompareOrdinal(key, end) <= 0, limit, ct));
  }

  public Task<IReadOnlyList<long>> ScanCreatedAtRangeIndexAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct)
  {
    var start = ProfileKeys.CreatedAt(fromUnixMs, 0);
    var end = ProfileKeys.CreatedAt(toUnixMs, long.MaxValue);
    return Task.FromResult(ScanStringIndexValues(CreatedAtIndex!, start, key => string.CompareOrdinal(key, end) <= 0, limit, ct));
  }

  public Task<IReadOnlyList<UserProfile>> QueryTopReputationAsync(int limit, CancellationToken ct)
  {
    return Task.FromResult(ScanStringIndex(ReputationIndex!, "", _ => true, limit, ct));
  }

  public Task<IReadOnlyList<long>> ScanTopReputationIndexAsync(int limit, CancellationToken ct)
  {
    return Task.FromResult(ScanStringIndexValues(ReputationIndex!, "", _ => true, limit, ct));
  }

  public async Task UpdateBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct)
  {
    foreach (var profile in profiles)
    {
      ct.ThrowIfCancellationRequested();
      var old = await GetByUserIdAsync(profile.UserId, ct)
          ?? throw new InvalidOperationException($"Missing profile {profile.UserId}");

      CountryStatusIndex!.Remove(Bytes(ProfileKeys.CountryStatus(old)), null, WriteOpts);
      ReputationIndex!.Remove(Bytes(ProfileKeys.Reputation(old)), null, WriteOpts);
      Profiles!.Put(UserIdKey(profile.UserId), Bytes(ProfileCodec.Serialize(profile)), null, WriteOpts);
      CountryStatusIndex.Put(Bytes(ProfileKeys.CountryStatus(profile)), UserIdValue(profile.UserId), null, WriteOpts);
      ReputationIndex.Put(Bytes(ProfileKeys.Reputation(profile)), UserIdValue(profile.UserId), null, WriteOpts);
    }
  }

  public Task StabilizeForReadMeasurementsAsync(CancellationToken ct) =>
      SettleAsync(ct);

  public Task SettleAsync(CancellationToken ct)
  {
    foreach (var db in new[] { Profiles, EmailIndex, CountryStatusIndex, CreatedAtIndex, ReputationIndex })
    {
      ct.ThrowIfCancellationRequested();
      db!.CompactRange((byte[]?)null, null, null);
    }
    return Task.CompletedTask;
  }

  public Task<long> CountProfilesAsync(CancellationToken ct)
  {
    long count = 0;
    using var iterator = Profiles!.NewIterator(null);
    for (iterator.SeekToFirst(); iterator.Valid(); iterator.Next())
    {
      ct.ThrowIfCancellationRequested();
      count++;
    }
    return Task.FromResult(count);
  }

  public Task<long> GetStorageSizeBytesAsync(CancellationToken ct)
  {
    return Task.FromResult(Directory.Exists(RootDirectory) ? GetDirectorySize(RootDirectory) : 0L);
  }

  public ValueTask DisposeAsync()
  {
    Profiles?.Dispose();
    EmailIndex?.Dispose();
    CountryStatusIndex?.Dispose();
    CreatedAtIndex?.Dispose();
    ReputationIndex?.Dispose();
    return ValueTask.CompletedTask;
  }

  RocksDb OpenDb(string path)
  {
    Directory.CreateDirectory(path);
    var options = new DbOptions()
        .SetCreateIfMissing(true)
        .IncreaseParallelism(Environment.ProcessorCount)
        .SetWriteBufferSize((ulong)WriteBufferMb * 1024UL * 1024UL)
        .SetMaxWriteBufferNumber(MaxWriteBufferNumber)
        .SetCompression(Compression.Zstd)
        .OptimizeLevelStyleCompaction((ulong)WriteBufferMb * 1024UL * 1024UL);
    return RocksDb.Open(options, path);
  }

  bool TryGetProfile(long userId, out UserProfile profile)
  {
    var value = Profiles!.Get(UserIdKey(userId), null, null);
    if (value != null)
    {
      profile = ProfileCodec.Deserialize(Encoding.GetString(value));
      return true;
    }
    profile = null!;
    return false;
  }

  IReadOnlyList<UserProfile> ScanStringIndex(
      RocksDb index,
      string startKey,
      Func<string, bool> keepGoing,
      int limit,
      CancellationToken ct)
  {
    var results = new List<UserProfile>(limit);
    using var iterator = index.NewIterator(null);
    if (startKey.Length == 0)
      iterator.SeekToFirst();
    else
      iterator.Seek(startKey);

    while (results.Count < limit && iterator.Valid())
    {
      ct.ThrowIfCancellationRequested();
      var key = iterator.StringKey();
      if (!keepGoing(key))
        break;
      if (TryGetProfile(ParseUserId(iterator.Value()), out var profile))
        results.Add(profile);
      iterator.Next();
    }
    return results;
  }

  IReadOnlyList<long> ScanStringIndexValues(
      RocksDb index,
      string startKey,
      Func<string, bool> keepGoing,
      int limit,
      CancellationToken ct)
  {
    var results = new List<long>(limit);
    using var iterator = index.NewIterator(null);
    if (startKey.Length == 0)
      iterator.SeekToFirst();
    else
      iterator.Seek(startKey);

    while (results.Count < limit && iterator.Valid())
    {
      ct.ThrowIfCancellationRequested();
      var key = iterator.StringKey();
      if (!keepGoing(key))
        break;
      results.Add(ParseUserId(iterator.Value()));
      iterator.Next();
    }
    return results;
  }

  static byte[] UserIdKey(long userId) =>
      UserIdValue(userId);

  static byte[] UserIdValue(long userId) =>
      WriteSortableInt64(userId);

  static long ParseUserId(byte[] value)
  {
    if (value.Length != sizeof(long))
      throw new FormatException($"Expected an 8-byte Int64 value, but received {value.Length} bytes.");
    return BinaryPrimitives.ReadInt64BigEndian(value);
  }

  static byte[] WriteSortableInt64(long value)
  {
    var bytes = new byte[sizeof(long)];
    BinaryPrimitives.WriteInt64BigEndian(bytes, value);
    return bytes;
  }

  static byte[] Bytes(string value) =>
      Encoding.GetBytes(value);

  static long GetDirectorySize(string path)
  {
    return Directory.EnumerateFiles(path, "*", SearchOption.AllDirectories)
        .Sum(file => new FileInfo(file).Length);
  }

  sealed class Worker(RocksDbProfileStore store) : IProfileStoreEngineWorker
  {
    public Task InsertBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct) =>
        store.InsertBatchAsync(profiles, ct);

    public Task<UserProfile?> GetByUserIdAsync(long userId, CancellationToken ct) =>
        store.GetByUserIdAsync(userId, ct);

    public Task<UserProfile?> GetByEmailAsync(string email, CancellationToken ct) =>
        store.GetByEmailAsync(email, ct);

    public Task<IReadOnlyList<UserProfile>> QueryCountryStatusAsync(
        string country,
        string status,
        int limit,
        CancellationToken ct) =>
        store.QueryCountryStatusAsync(country, status, limit, ct);

    public Task<IReadOnlyList<long>> ScanCountryStatusIndexAsync(
        string country,
        string status,
        int limit,
        CancellationToken ct) =>
        store.ScanCountryStatusIndexAsync(country, status, limit, ct);

    public Task<IReadOnlyList<UserProfile>> QueryCreatedAtRangeAsync(
        long fromUnixMs,
        long toUnixMs,
        int limit,
        CancellationToken ct) =>
        store.QueryCreatedAtRangeAsync(fromUnixMs, toUnixMs, limit, ct);

    public Task<IReadOnlyList<long>> ScanCreatedAtRangeIndexAsync(
        long fromUnixMs,
        long toUnixMs,
        int limit,
        CancellationToken ct) =>
        store.ScanCreatedAtRangeIndexAsync(fromUnixMs, toUnixMs, limit, ct);

    public Task<IReadOnlyList<UserProfile>> QueryTopReputationAsync(int limit, CancellationToken ct) =>
        store.QueryTopReputationAsync(limit, ct);

    public Task<IReadOnlyList<long>> ScanTopReputationIndexAsync(int limit, CancellationToken ct) =>
        store.ScanTopReputationIndexAsync(limit, ct);

    public Task UpdateBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct) =>
        store.UpdateBatchAsync(profiles, ct);

    public ValueTask DisposeAsync() => ValueTask.CompletedTask;
  }
}
