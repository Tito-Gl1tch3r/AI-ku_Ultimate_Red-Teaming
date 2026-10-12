namespace ProfileStore.Benchmark;

public interface IProfileStoreEngine : IAsyncDisposable
{
  string Name { get; }

  string DurabilityDescription { get; }

  bool RequiresReadStabilization { get; }

  Task InitializeAsync(BenchmarkConfig config, bool reset, CancellationToken ct);

  Task<IProfileStoreEngineWorker> CreateWorkerAsync(CancellationToken ct);

  Task StabilizeForReadMeasurementsAsync(CancellationToken ct);

  Task SettleAsync(CancellationToken ct);

  Task<long> CountProfilesAsync(CancellationToken ct);

  Task<long> GetStorageSizeBytesAsync(CancellationToken ct);
}

public interface IProfileStoreEngineWorker : IAsyncDisposable
{
  Task InsertBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct);

  Task<UserProfile?> GetByUserIdAsync(long userId, CancellationToken ct);

  Task<UserProfile?> GetByEmailAsync(string email, CancellationToken ct);

  Task<IReadOnlyList<UserProfile>> QueryCountryStatusAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct);

  Task<IReadOnlyList<long>> ScanCountryStatusIndexAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct);

  Task<IReadOnlyList<UserProfile>> QueryCreatedAtRangeAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct);

  Task<IReadOnlyList<long>> ScanCreatedAtRangeIndexAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct);

  Task<IReadOnlyList<UserProfile>> QueryTopReputationAsync(
      int limit,
      CancellationToken ct);

  Task<IReadOnlyList<long>> ScanTopReputationIndexAsync(
      int limit,
      CancellationToken ct);

  Task UpdateBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct);
}
