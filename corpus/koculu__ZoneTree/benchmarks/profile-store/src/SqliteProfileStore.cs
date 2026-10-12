using Microsoft.Data.Sqlite;

namespace ProfileStore.Benchmark;

public sealed class SqliteProfileStore : IProfileStoreEngine, IProfileStoreEngineWorker
{
  string DatabasePath = "";
  SqliteConnection? Connection;
  SqliteCommand? InsertCommand;
  SqliteCommand? UpdateCommand;
  SqliteCommand? SelectByIdCommand;
  SqliteCommand? SelectByEmailCommand;
  SqliteCommand? QueryCountryStatusCommand;
  SqliteCommand? ScanCountryStatusIndexCommand;
  SqliteCommand? QueryCreatedAtRangeCommand;
  SqliteCommand? ScanCreatedAtRangeIndexCommand;
  SqliteCommand? QueryTopReputationCommand;
  SqliteCommand? ScanTopReputationIndexCommand;
  SqliteCommand? CountCommand;
  int CacheMb;
  int MmapMb;

  public string Name => "SQLite";

  public string DurabilityDescription =>
      $"WAL journal mode; synchronous=NORMAL; cache={CacheMb} MB; mmap={MmapMb} MB; native SQL indexes; single-row writes use autocommit.";

  public bool RequiresReadStabilization => false;

  public async Task InitializeAsync(BenchmarkConfig config, bool reset, CancellationToken ct)
  {
    var directory = Path.Combine(config.DataDirectory, "sqlite");
    Directory.CreateDirectory(directory);
    DatabasePath = Path.Combine(directory, "profiles.db");
    if (reset && File.Exists(DatabasePath))
      File.Delete(DatabasePath);

    Connection = new SqliteConnection($"Data Source={DatabasePath}");
    await Connection.OpenAsync(ct);
    await ExecuteAsync("PRAGMA journal_mode=WAL;", ct);
    await ExecuteAsync("PRAGMA synchronous=NORMAL;", ct);
    await ExecuteAsync("PRAGMA busy_timeout=60000;", ct);
    CacheMb = config.SqliteCacheMb;
    MmapMb = config.SqliteMmapMb;
    if (CacheMb > 0)
      await ExecuteAsync($"PRAGMA cache_size=-{CacheMb * 1024L};", ct);
    if (MmapMb > 0)
      await ExecuteAsync($"PRAGMA mmap_size={MmapMb * 1024L * 1024L};", ct);
    await ExecuteAsync("PRAGMA temp_store=MEMORY;", ct);
    await CreateSchemaAsync(ct);
    PrepareCommands();
  }

  public async Task<IProfileStoreEngineWorker> CreateWorkerAsync(CancellationToken ct)
  {
    var worker = new SqliteProfileStore();
    await worker.InitializeWorkerAsync(DatabasePath, CacheMb, MmapMb, ct);
    return worker;
  }

  async Task InitializeWorkerAsync(
      string databasePath,
      int cacheMb,
      int mmapMb,
      CancellationToken ct)
  {
    DatabasePath = databasePath;
    CacheMb = cacheMb;
    MmapMb = mmapMb;
    Connection = new SqliteConnection($"Data Source={DatabasePath}");
    await Connection.OpenAsync(ct);
    await ExecuteAsync("PRAGMA journal_mode=WAL;", ct);
    await ExecuteAsync("PRAGMA synchronous=NORMAL;", ct);
    await ExecuteAsync("PRAGMA busy_timeout=60000;", ct);
    if (CacheMb > 0)
      await ExecuteAsync($"PRAGMA cache_size=-{CacheMb * 1024L};", ct);
    if (MmapMb > 0)
      await ExecuteAsync($"PRAGMA mmap_size={MmapMb * 1024L * 1024L};", ct);
    await ExecuteAsync("PRAGMA temp_store=MEMORY;", ct);
    PrepareCommands();
  }

  public async Task InsertBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct)
  {
    if (profiles.Count == 1)
    {
      SetProfileParameters(InsertCommand!, profiles[0]);
      await InsertCommand!.ExecuteNonQueryAsync(ct);
      return;
    }

    await using var tx = await Connection!.BeginTransactionAsync(ct);
    await using var command = Connection.CreateCommand();
    command.Transaction = (SqliteTransaction)tx;
    command.CommandText = """
        INSERT INTO profiles
        (user_id, email, country, status, created_at, last_login, reputation, display_name, bio)
        VALUES ($user_id, $email, $country, $status, $created_at, $last_login, $reputation, $display_name, $bio);
        """;
    AddProfileParameters(command);
    foreach (var profile in profiles)
    {
      ct.ThrowIfCancellationRequested();
      SetProfileParameters(command, profile);
      await command.ExecuteNonQueryAsync(ct);
    }
    await tx.CommitAsync(ct);
  }

  public async Task<UserProfile?> GetByUserIdAsync(long userId, CancellationToken ct)
  {
    SelectByIdCommand!.Parameters["$user_id"].Value = userId;
    return await ReadSingleAsync(SelectByIdCommand, ct);
  }

  public async Task<UserProfile?> GetByEmailAsync(string email, CancellationToken ct)
  {
    SelectByEmailCommand!.Parameters["$email"].Value = email;
    return await ReadSingleAsync(SelectByEmailCommand, ct);
  }

  public async Task<IReadOnlyList<UserProfile>> QueryCountryStatusAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct)
  {
    QueryCountryStatusCommand!.Parameters["$country"].Value = country;
    QueryCountryStatusCommand.Parameters["$status"].Value = status;
    QueryCountryStatusCommand.Parameters["$limit"].Value = limit;
    return await ReadManyAsync(QueryCountryStatusCommand, ct);
  }

  public async Task<IReadOnlyList<long>> ScanCountryStatusIndexAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct)
  {
    ScanCountryStatusIndexCommand!.Parameters["$country"].Value = country;
    ScanCountryStatusIndexCommand.Parameters["$status"].Value = status;
    ScanCountryStatusIndexCommand.Parameters["$limit"].Value = limit;
    return await ReadIdsAsync(ScanCountryStatusIndexCommand, ct);
  }

  public async Task<IReadOnlyList<UserProfile>> QueryCreatedAtRangeAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct)
  {
    QueryCreatedAtRangeCommand!.Parameters["$from"].Value = fromUnixMs;
    QueryCreatedAtRangeCommand.Parameters["$to"].Value = toUnixMs;
    QueryCreatedAtRangeCommand.Parameters["$limit"].Value = limit;
    return await ReadManyAsync(QueryCreatedAtRangeCommand, ct);
  }

  public async Task<IReadOnlyList<long>> ScanCreatedAtRangeIndexAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct)
  {
    ScanCreatedAtRangeIndexCommand!.Parameters["$from"].Value = fromUnixMs;
    ScanCreatedAtRangeIndexCommand.Parameters["$to"].Value = toUnixMs;
    ScanCreatedAtRangeIndexCommand.Parameters["$limit"].Value = limit;
    return await ReadIdsAsync(ScanCreatedAtRangeIndexCommand, ct);
  }

  public async Task<IReadOnlyList<UserProfile>> QueryTopReputationAsync(int limit, CancellationToken ct)
  {
    QueryTopReputationCommand!.Parameters["$limit"].Value = limit;
    return await ReadManyAsync(QueryTopReputationCommand, ct);
  }

  public async Task<IReadOnlyList<long>> ScanTopReputationIndexAsync(int limit, CancellationToken ct)
  {
    ScanTopReputationIndexCommand!.Parameters["$limit"].Value = limit;
    return await ReadIdsAsync(ScanTopReputationIndexCommand, ct);
  }

  public async Task UpdateBatchAsync(IReadOnlyList<UserProfile> profiles, CancellationToken ct)
  {
    if (profiles.Count == 1)
    {
      SetProfileUpdateParameters(UpdateCommand!, profiles[0]);
      await UpdateCommand!.ExecuteNonQueryAsync(ct);
      return;
    }

    await using var tx = await Connection!.BeginTransactionAsync(ct);
    await using var command = Connection.CreateCommand();
    command.Transaction = (SqliteTransaction)tx;
    command.CommandText = """
        UPDATE profiles
        SET status = $status,
            last_login = $last_login,
            reputation = $reputation,
            bio = $bio
        WHERE user_id = $user_id;
        """;
    AddProfileUpdateParameters(command);
    foreach (var profile in profiles)
    {
      ct.ThrowIfCancellationRequested();
      SetProfileUpdateParameters(command, profile);
      await command.ExecuteNonQueryAsync(ct);
    }
    await tx.CommitAsync(ct);
  }

  public Task StabilizeForReadMeasurementsAsync(CancellationToken ct) =>
      Task.CompletedTask;

  public Task SettleAsync(CancellationToken ct)
  {
    return ExecuteAsync("PRAGMA wal_checkpoint(TRUNCATE);", ct);
  }

  public async Task<long> CountProfilesAsync(CancellationToken ct)
  {
    return (long)(await CountCommand!.ExecuteScalarAsync(ct) ?? 0L);
  }

  public Task<long> GetStorageSizeBytesAsync(CancellationToken ct)
  {
    var directory = Path.GetDirectoryName(DatabasePath)!;
    var size = Directory.EnumerateFiles(directory, "*", SearchOption.TopDirectoryOnly)
        .Sum(file => new FileInfo(file).Length);
    return Task.FromResult(size);
  }

  public async ValueTask DisposeAsync()
  {
    InsertCommand?.Dispose();
    UpdateCommand?.Dispose();
    SelectByIdCommand?.Dispose();
    SelectByEmailCommand?.Dispose();
    QueryCountryStatusCommand?.Dispose();
    ScanCountryStatusIndexCommand?.Dispose();
    QueryCreatedAtRangeCommand?.Dispose();
    ScanCreatedAtRangeIndexCommand?.Dispose();
    QueryTopReputationCommand?.Dispose();
    ScanTopReputationIndexCommand?.Dispose();
    CountCommand?.Dispose();
    if (Connection != null)
      await Connection.DisposeAsync();
  }

  const string SelectColumns = """
      SELECT user_id, email, country, status, created_at, last_login, reputation, display_name, bio
      FROM profiles
      """;

  async Task CreateSchemaAsync(CancellationToken ct)
  {
    await ExecuteAsync("""
        CREATE TABLE IF NOT EXISTS profiles (
          user_id INTEGER PRIMARY KEY,
          email TEXT NOT NULL UNIQUE,
          country TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          last_login INTEGER NOT NULL,
          reputation INTEGER NOT NULL,
          display_name TEXT NOT NULL,
          bio TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_profiles_country_status ON profiles(country, status, user_id);
        CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at, user_id);
        CREATE INDEX IF NOT EXISTS idx_profiles_reputation ON profiles(reputation DESC, user_id);
        """, ct);
  }

  void PrepareCommands()
  {
    InsertCommand = Connection!.CreateCommand();
    InsertCommand.CommandText = """
        INSERT INTO profiles
        (user_id, email, country, status, created_at, last_login, reputation, display_name, bio)
        VALUES ($user_id, $email, $country, $status, $created_at, $last_login, $reputation, $display_name, $bio);
        """;
    AddProfileParameters(InsertCommand);
    InsertCommand.Prepare();

    UpdateCommand = Connection.CreateCommand();
    UpdateCommand.CommandText = """
        UPDATE profiles
        SET status = $status,
            last_login = $last_login,
            reputation = $reputation,
            bio = $bio
        WHERE user_id = $user_id;
        """;
    AddProfileUpdateParameters(UpdateCommand);
    UpdateCommand.Prepare();

    SelectByIdCommand = Connection.CreateCommand();
    SelectByIdCommand.CommandText = SelectColumns + " WHERE user_id = $user_id;";
    SelectByIdCommand.Parameters.Add("$user_id", SqliteType.Integer);
    SelectByIdCommand.Prepare();

    SelectByEmailCommand = Connection.CreateCommand();
    SelectByEmailCommand.CommandText = SelectColumns + " WHERE email = $email;";
    SelectByEmailCommand.Parameters.Add("$email", SqliteType.Text);
    SelectByEmailCommand.Prepare();

    QueryCountryStatusCommand = Connection.CreateCommand();
    QueryCountryStatusCommand.CommandText = SelectColumns + """
         WHERE country = $country AND status = $status
         ORDER BY user_id
         LIMIT $limit;
        """;
    QueryCountryStatusCommand.Parameters.Add("$country", SqliteType.Text);
    QueryCountryStatusCommand.Parameters.Add("$status", SqliteType.Text);
    QueryCountryStatusCommand.Parameters.Add("$limit", SqliteType.Integer);
    QueryCountryStatusCommand.Prepare();

    ScanCountryStatusIndexCommand = Connection.CreateCommand();
    ScanCountryStatusIndexCommand.CommandText = """
        SELECT user_id FROM profiles
        WHERE country = $country AND status = $status
        ORDER BY user_id
        LIMIT $limit;
        """;
    ScanCountryStatusIndexCommand.Parameters.Add("$country", SqliteType.Text);
    ScanCountryStatusIndexCommand.Parameters.Add("$status", SqliteType.Text);
    ScanCountryStatusIndexCommand.Parameters.Add("$limit", SqliteType.Integer);
    ScanCountryStatusIndexCommand.Prepare();

    QueryCreatedAtRangeCommand = Connection.CreateCommand();
    QueryCreatedAtRangeCommand.CommandText = SelectColumns + """
         WHERE created_at >= $from AND created_at <= $to
         ORDER BY created_at, user_id
         LIMIT $limit;
        """;
    QueryCreatedAtRangeCommand.Parameters.Add("$from", SqliteType.Integer);
    QueryCreatedAtRangeCommand.Parameters.Add("$to", SqliteType.Integer);
    QueryCreatedAtRangeCommand.Parameters.Add("$limit", SqliteType.Integer);
    QueryCreatedAtRangeCommand.Prepare();

    ScanCreatedAtRangeIndexCommand = Connection.CreateCommand();
    ScanCreatedAtRangeIndexCommand.CommandText = """
        SELECT user_id FROM profiles
        WHERE created_at >= $from AND created_at <= $to
        ORDER BY created_at, user_id
        LIMIT $limit;
        """;
    ScanCreatedAtRangeIndexCommand.Parameters.Add("$from", SqliteType.Integer);
    ScanCreatedAtRangeIndexCommand.Parameters.Add("$to", SqliteType.Integer);
    ScanCreatedAtRangeIndexCommand.Parameters.Add("$limit", SqliteType.Integer);
    ScanCreatedAtRangeIndexCommand.Prepare();

    QueryTopReputationCommand = Connection.CreateCommand();
    QueryTopReputationCommand.CommandText = SelectColumns + " ORDER BY reputation DESC, user_id LIMIT $limit;";
    QueryTopReputationCommand.Parameters.Add("$limit", SqliteType.Integer);
    QueryTopReputationCommand.Prepare();

    ScanTopReputationIndexCommand = Connection.CreateCommand();
    ScanTopReputationIndexCommand.CommandText = "SELECT user_id FROM profiles ORDER BY reputation DESC, user_id LIMIT $limit;";
    ScanTopReputationIndexCommand.Parameters.Add("$limit", SqliteType.Integer);
    ScanTopReputationIndexCommand.Prepare();

    CountCommand = Connection.CreateCommand();
    CountCommand.CommandText = "SELECT COUNT(*) FROM profiles;";
    CountCommand.Prepare();
  }

  async Task ExecuteAsync(string sql, CancellationToken ct)
  {
    await using var command = Connection!.CreateCommand();
    command.CommandText = sql;
    await command.ExecuteNonQueryAsync(ct);
  }

  static void AddProfileParameters(SqliteCommand command)
  {
    command.Parameters.Add("$user_id", SqliteType.Integer);
    command.Parameters.Add("$email", SqliteType.Text);
    command.Parameters.Add("$country", SqliteType.Text);
    command.Parameters.Add("$status", SqliteType.Text);
    command.Parameters.Add("$created_at", SqliteType.Integer);
    command.Parameters.Add("$last_login", SqliteType.Integer);
    command.Parameters.Add("$reputation", SqliteType.Integer);
    command.Parameters.Add("$display_name", SqliteType.Text);
    command.Parameters.Add("$bio", SqliteType.Text);
  }

  static void SetProfileParameters(SqliteCommand command, UserProfile profile)
  {
    command.Parameters["$user_id"].Value = profile.UserId;
    command.Parameters["$email"].Value = profile.Email;
    command.Parameters["$country"].Value = profile.Country;
    command.Parameters["$status"].Value = profile.Status;
    command.Parameters["$created_at"].Value = profile.CreatedAtUnixMs;
    command.Parameters["$last_login"].Value = profile.LastLoginUnixMs;
    command.Parameters["$reputation"].Value = profile.Reputation;
    command.Parameters["$display_name"].Value = profile.DisplayName;
    command.Parameters["$bio"].Value = profile.Bio;
  }

  static void AddProfileUpdateParameters(SqliteCommand command)
  {
    command.Parameters.Add("$user_id", SqliteType.Integer);
    command.Parameters.Add("$status", SqliteType.Text);
    command.Parameters.Add("$last_login", SqliteType.Integer);
    command.Parameters.Add("$reputation", SqliteType.Integer);
    command.Parameters.Add("$bio", SqliteType.Text);
  }

  static void SetProfileUpdateParameters(SqliteCommand command, UserProfile profile)
  {
    command.Parameters["$user_id"].Value = profile.UserId;
    command.Parameters["$status"].Value = profile.Status;
    command.Parameters["$last_login"].Value = profile.LastLoginUnixMs;
    command.Parameters["$reputation"].Value = profile.Reputation;
    command.Parameters["$bio"].Value = profile.Bio;
  }

  static async Task<UserProfile?> ReadSingleAsync(SqliteCommand command, CancellationToken ct)
  {
    await using var reader = await command.ExecuteReaderAsync(ct);
    return await reader.ReadAsync(ct) ? ReadProfile(reader) : null;
  }

  static async Task<IReadOnlyList<UserProfile>> ReadManyAsync(SqliteCommand command, CancellationToken ct)
  {
    var result = new List<UserProfile>();
    await using var reader = await command.ExecuteReaderAsync(ct);
    while (await reader.ReadAsync(ct))
      result.Add(ReadProfile(reader));
    return result;
  }

  static async Task<IReadOnlyList<long>> ReadIdsAsync(SqliteCommand command, CancellationToken ct)
  {
    var result = new List<long>();
    await using var reader = await command.ExecuteReaderAsync(ct);
    while (await reader.ReadAsync(ct))
      result.Add(reader.GetInt64(0));
    return result;
  }

  static UserProfile ReadProfile(SqliteDataReader reader)
  {
    return new UserProfile(
        reader.GetInt64(0),
        reader.GetString(1),
        reader.GetString(2),
        reader.GetString(3),
        reader.GetInt64(4),
        reader.GetInt64(5),
        reader.GetInt32(6),
        reader.GetString(7),
        reader.GetString(8));
  }
}
