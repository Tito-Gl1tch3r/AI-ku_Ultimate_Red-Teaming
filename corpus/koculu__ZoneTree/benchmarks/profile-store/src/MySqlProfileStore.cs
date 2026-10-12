using MySqlConnector;

namespace ProfileStore.Benchmark;

public sealed class MySqlProfileStore : IProfileStoreEngine, IProfileStoreEngineWorker
{
  MySqlConnection? Connection;
  MySqlCommand? InsertCommand;
  MySqlCommand? UpdateCommand;
  MySqlCommand? SelectByIdCommand;
  MySqlCommand? SelectByEmailCommand;
  MySqlCommand? QueryCountryStatusCommand;
  MySqlCommand? ScanCountryStatusIndexCommand;
  MySqlCommand? QueryCreatedAtRangeCommand;
  MySqlCommand? ScanCreatedAtRangeIndexCommand;
  MySqlCommand? QueryTopReputationCommand;
  MySqlCommand? ScanTopReputationIndexCommand;
  MySqlCommand? CountCommand;
  BenchmarkConfig Config = new();

  public string Name => "MySQL";

  public string DurabilityDescription =>
      "InnoDB; benchmark Docker disables binlog, sets innodb_flush_log_at_trx_commit=2 and sync_binlog=0; native SQL indexes; single-row writes use autocommit.";

  public bool RequiresReadStabilization => false;

  public async Task InitializeAsync(BenchmarkConfig config, bool reset, CancellationToken ct)
  {
    Config = config;
    Connection = new MySqlConnection(ConnectionString(config));
    await OpenWithRetryAsync(Connection, ct);
    if (reset)
      await ExecuteAsync("DROP TABLE IF EXISTS profiles;", ct);
    await CreateSchemaAsync(ct);
    await PrepareCommandsAsync(ct);
  }

  public async Task<IProfileStoreEngineWorker> CreateWorkerAsync(CancellationToken ct)
  {
    var worker = new MySqlProfileStore();
    await worker.InitializeWorkerAsync(Config, ct);
    return worker;
  }

  async Task InitializeWorkerAsync(BenchmarkConfig config, CancellationToken ct)
  {
    Config = config;
    Connection = new MySqlConnection(ConnectionString(config));
    await OpenWithRetryAsync(Connection, ct);
    await PrepareCommandsAsync(ct);
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
    command.Transaction = tx;
    command.CommandText = """
        INSERT INTO profiles
        (user_id, email, country, status, created_at, last_login, reputation, display_name, bio)
        VALUES (@user_id, @email, @country, @status, @created_at, @last_login, @reputation, @display_name, @bio);
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
    SelectByIdCommand!.Parameters["@user_id"].Value = userId;
    return await ReadSingleAsync(SelectByIdCommand, ct);
  }

  public async Task<UserProfile?> GetByEmailAsync(string email, CancellationToken ct)
  {
    SelectByEmailCommand!.Parameters["@email"].Value = email;
    return await ReadSingleAsync(SelectByEmailCommand, ct);
  }

  public async Task<IReadOnlyList<UserProfile>> QueryCountryStatusAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct)
  {
    QueryCountryStatusCommand!.Parameters["@country"].Value = country;
    QueryCountryStatusCommand.Parameters["@status"].Value = status;
    QueryCountryStatusCommand.Parameters["@limit"].Value = limit;
    return await ReadManyAsync(QueryCountryStatusCommand, ct);
  }

  public async Task<IReadOnlyList<long>> ScanCountryStatusIndexAsync(
      string country,
      string status,
      int limit,
      CancellationToken ct)
  {
    ScanCountryStatusIndexCommand!.Parameters["@country"].Value = country;
    ScanCountryStatusIndexCommand.Parameters["@status"].Value = status;
    ScanCountryStatusIndexCommand.Parameters["@limit"].Value = limit;
    return await ReadIdsAsync(ScanCountryStatusIndexCommand, ct);
  }

  public async Task<IReadOnlyList<UserProfile>> QueryCreatedAtRangeAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct)
  {
    QueryCreatedAtRangeCommand!.Parameters["@from"].Value = fromUnixMs;
    QueryCreatedAtRangeCommand.Parameters["@to"].Value = toUnixMs;
    QueryCreatedAtRangeCommand.Parameters["@limit"].Value = limit;
    return await ReadManyAsync(QueryCreatedAtRangeCommand, ct);
  }

  public async Task<IReadOnlyList<long>> ScanCreatedAtRangeIndexAsync(
      long fromUnixMs,
      long toUnixMs,
      int limit,
      CancellationToken ct)
  {
    ScanCreatedAtRangeIndexCommand!.Parameters["@from"].Value = fromUnixMs;
    ScanCreatedAtRangeIndexCommand.Parameters["@to"].Value = toUnixMs;
    ScanCreatedAtRangeIndexCommand.Parameters["@limit"].Value = limit;
    return await ReadIdsAsync(ScanCreatedAtRangeIndexCommand, ct);
  }

  public async Task<IReadOnlyList<UserProfile>> QueryTopReputationAsync(int limit, CancellationToken ct)
  {
    QueryTopReputationCommand!.Parameters["@limit"].Value = limit;
    return await ReadManyAsync(QueryTopReputationCommand, ct);
  }

  public async Task<IReadOnlyList<long>> ScanTopReputationIndexAsync(int limit, CancellationToken ct)
  {
    ScanTopReputationIndexCommand!.Parameters["@limit"].Value = limit;
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
    command.Transaction = tx;
    command.CommandText = """
        UPDATE profiles
        SET status = @status,
            last_login = @last_login,
            reputation = @reputation,
            bio = @bio
        WHERE user_id = @user_id;
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
    return ExecuteAsync("FLUSH TABLES profiles;", ct);
  }

  public async Task<long> CountProfilesAsync(CancellationToken ct)
  {
    return Convert.ToInt64(await CountCommand!.ExecuteScalarAsync(ct));
  }

  public async Task<long> GetStorageSizeBytesAsync(CancellationToken ct)
  {
    await ExecuteAsync("ANALYZE TABLE profiles;", ct);
    await using var command = Connection!.CreateCommand();
    command.CommandText = """
        SELECT COALESCE(SUM(data_length + index_length), 0)
        FROM information_schema.tables
        WHERE table_schema = @schema AND table_name = 'profiles';
        """;
    command.Parameters.AddWithValue("@schema", Config.MySqlDatabase);
    return Convert.ToInt64(await command.ExecuteScalarAsync(ct));
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

  static string ConnectionString(BenchmarkConfig config)
  {
    return $"Server={config.MySqlHost};Port={config.MySqlPort};Database={config.MySqlDatabase};User ID={config.MySqlUser};Password={config.MySqlPassword};SslMode=None;AllowPublicKeyRetrieval=True;";
  }

  static async Task OpenWithRetryAsync(MySqlConnection connection, CancellationToken ct)
  {
    Exception? last = null;
    for (var attempt = 0; attempt < 60; attempt++)
    {
      try
      {
        await connection.OpenAsync(ct);
        return;
      }
      catch (Exception ex) when (!ct.IsCancellationRequested)
      {
        last = ex;
        await Task.Delay(TimeSpan.FromSeconds(1), ct);
      }
    }
    throw new InvalidOperationException("Could not connect to MySQL.", last);
  }

  async Task CreateSchemaAsync(CancellationToken ct)
  {
    await ExecuteAsync("""
        CREATE TABLE IF NOT EXISTS profiles (
          user_id BIGINT NOT NULL PRIMARY KEY,
          email VARCHAR(255) NOT NULL UNIQUE,
          country VARCHAR(8) NOT NULL,
          status VARCHAR(16) NOT NULL,
          created_at BIGINT NOT NULL,
          last_login BIGINT NOT NULL,
          reputation INT NOT NULL,
          display_name VARCHAR(255) NOT NULL,
          bio TEXT NOT NULL,
          INDEX idx_profiles_country_status(country, status, user_id),
          INDEX idx_profiles_created_at(created_at, user_id),
          INDEX idx_profiles_reputation(reputation DESC, user_id)
        ) ENGINE=InnoDB;
        """, ct);
  }

  async Task PrepareCommandsAsync(CancellationToken ct)
  {
    InsertCommand = Connection!.CreateCommand();
    InsertCommand.CommandText = """
        INSERT INTO profiles
        (user_id, email, country, status, created_at, last_login, reputation, display_name, bio)
        VALUES (@user_id, @email, @country, @status, @created_at, @last_login, @reputation, @display_name, @bio);
        """;
    AddProfileParameters(InsertCommand);
    await InsertCommand.PrepareAsync(ct);

    UpdateCommand = Connection.CreateCommand();
    UpdateCommand.CommandText = """
        UPDATE profiles
        SET status = @status,
            last_login = @last_login,
            reputation = @reputation,
            bio = @bio
        WHERE user_id = @user_id;
        """;
    AddProfileUpdateParameters(UpdateCommand);
    await UpdateCommand.PrepareAsync(ct);

    SelectByIdCommand = Connection.CreateCommand();
    SelectByIdCommand.CommandText = SelectColumns + " WHERE user_id = @user_id;";
    SelectByIdCommand.Parameters.Add("@user_id", MySqlDbType.Int64);
    await SelectByIdCommand.PrepareAsync(ct);

    SelectByEmailCommand = Connection.CreateCommand();
    SelectByEmailCommand.CommandText = SelectColumns + " WHERE email = @email;";
    SelectByEmailCommand.Parameters.Add("@email", MySqlDbType.VarChar);
    await SelectByEmailCommand.PrepareAsync(ct);

    QueryCountryStatusCommand = Connection.CreateCommand();
    QueryCountryStatusCommand.CommandText = SelectColumns + """
         WHERE country = @country AND status = @status
         ORDER BY user_id
         LIMIT @limit;
        """;
    QueryCountryStatusCommand.Parameters.Add("@country", MySqlDbType.VarChar);
    QueryCountryStatusCommand.Parameters.Add("@status", MySqlDbType.VarChar);
    QueryCountryStatusCommand.Parameters.Add("@limit", MySqlDbType.Int32);
    await QueryCountryStatusCommand.PrepareAsync(ct);

    ScanCountryStatusIndexCommand = Connection.CreateCommand();
    ScanCountryStatusIndexCommand.CommandText = """
        SELECT user_id FROM profiles
        WHERE country = @country AND status = @status
        ORDER BY user_id
        LIMIT @limit;
        """;
    ScanCountryStatusIndexCommand.Parameters.Add("@country", MySqlDbType.VarChar);
    ScanCountryStatusIndexCommand.Parameters.Add("@status", MySqlDbType.VarChar);
    ScanCountryStatusIndexCommand.Parameters.Add("@limit", MySqlDbType.Int32);
    await ScanCountryStatusIndexCommand.PrepareAsync(ct);

    QueryCreatedAtRangeCommand = Connection.CreateCommand();
    QueryCreatedAtRangeCommand.CommandText = SelectColumns + """
         WHERE created_at >= @from AND created_at <= @to
         ORDER BY created_at, user_id
         LIMIT @limit;
        """;
    QueryCreatedAtRangeCommand.Parameters.Add("@from", MySqlDbType.Int64);
    QueryCreatedAtRangeCommand.Parameters.Add("@to", MySqlDbType.Int64);
    QueryCreatedAtRangeCommand.Parameters.Add("@limit", MySqlDbType.Int32);
    await QueryCreatedAtRangeCommand.PrepareAsync(ct);

    ScanCreatedAtRangeIndexCommand = Connection.CreateCommand();
    ScanCreatedAtRangeIndexCommand.CommandText = """
        SELECT user_id FROM profiles
        WHERE created_at >= @from AND created_at <= @to
        ORDER BY created_at, user_id
        LIMIT @limit;
        """;
    ScanCreatedAtRangeIndexCommand.Parameters.Add("@from", MySqlDbType.Int64);
    ScanCreatedAtRangeIndexCommand.Parameters.Add("@to", MySqlDbType.Int64);
    ScanCreatedAtRangeIndexCommand.Parameters.Add("@limit", MySqlDbType.Int32);
    await ScanCreatedAtRangeIndexCommand.PrepareAsync(ct);

    QueryTopReputationCommand = Connection.CreateCommand();
    QueryTopReputationCommand.CommandText = SelectColumns + " ORDER BY reputation DESC, user_id LIMIT @limit;";
    QueryTopReputationCommand.Parameters.Add("@limit", MySqlDbType.Int32);
    await QueryTopReputationCommand.PrepareAsync(ct);

    ScanTopReputationIndexCommand = Connection.CreateCommand();
    ScanTopReputationIndexCommand.CommandText = "SELECT user_id FROM profiles ORDER BY reputation DESC, user_id LIMIT @limit;";
    ScanTopReputationIndexCommand.Parameters.Add("@limit", MySqlDbType.Int32);
    await ScanTopReputationIndexCommand.PrepareAsync(ct);

    CountCommand = Connection.CreateCommand();
    CountCommand.CommandText = "SELECT COUNT(*) FROM profiles;";
    await CountCommand.PrepareAsync(ct);
  }

  async Task ExecuteAsync(string sql, CancellationToken ct)
  {
    await using var command = Connection!.CreateCommand();
    command.CommandText = sql;
    await command.ExecuteNonQueryAsync(ct);
  }

  static void AddProfileParameters(MySqlCommand command)
  {
    command.Parameters.Add("@user_id", MySqlDbType.Int64);
    command.Parameters.Add("@email", MySqlDbType.VarChar);
    command.Parameters.Add("@country", MySqlDbType.VarChar);
    command.Parameters.Add("@status", MySqlDbType.VarChar);
    command.Parameters.Add("@created_at", MySqlDbType.Int64);
    command.Parameters.Add("@last_login", MySqlDbType.Int64);
    command.Parameters.Add("@reputation", MySqlDbType.Int32);
    command.Parameters.Add("@display_name", MySqlDbType.VarChar);
    command.Parameters.Add("@bio", MySqlDbType.Text);
  }

  static void SetProfileParameters(MySqlCommand command, UserProfile profile)
  {
    command.Parameters["@user_id"].Value = profile.UserId;
    command.Parameters["@email"].Value = profile.Email;
    command.Parameters["@country"].Value = profile.Country;
    command.Parameters["@status"].Value = profile.Status;
    command.Parameters["@created_at"].Value = profile.CreatedAtUnixMs;
    command.Parameters["@last_login"].Value = profile.LastLoginUnixMs;
    command.Parameters["@reputation"].Value = profile.Reputation;
    command.Parameters["@display_name"].Value = profile.DisplayName;
    command.Parameters["@bio"].Value = profile.Bio;
  }

  static void AddProfileUpdateParameters(MySqlCommand command)
  {
    command.Parameters.Add("@user_id", MySqlDbType.Int64);
    command.Parameters.Add("@status", MySqlDbType.VarChar);
    command.Parameters.Add("@last_login", MySqlDbType.Int64);
    command.Parameters.Add("@reputation", MySqlDbType.Int32);
    command.Parameters.Add("@bio", MySqlDbType.Text);
  }

  static void SetProfileUpdateParameters(MySqlCommand command, UserProfile profile)
  {
    command.Parameters["@user_id"].Value = profile.UserId;
    command.Parameters["@status"].Value = profile.Status;
    command.Parameters["@last_login"].Value = profile.LastLoginUnixMs;
    command.Parameters["@reputation"].Value = profile.Reputation;
    command.Parameters["@bio"].Value = profile.Bio;
  }

  static async Task<UserProfile?> ReadSingleAsync(MySqlCommand command, CancellationToken ct)
  {
    await using var reader = await command.ExecuteReaderAsync(ct);
    return await reader.ReadAsync(ct) ? ReadProfile(reader) : null;
  }

  static async Task<IReadOnlyList<UserProfile>> ReadManyAsync(MySqlCommand command, CancellationToken ct)
  {
    var result = new List<UserProfile>();
    await using var reader = await command.ExecuteReaderAsync(ct);
    while (await reader.ReadAsync(ct))
      result.Add(ReadProfile(reader));
    return result;
  }

  static async Task<IReadOnlyList<long>> ReadIdsAsync(MySqlCommand command, CancellationToken ct)
  {
    var result = new List<long>();
    await using var reader = await command.ExecuteReaderAsync(ct);
    while (await reader.ReadAsync(ct))
      result.Add(reader.GetInt64(0));
    return result;
  }

  static UserProfile ReadProfile(MySqlDataReader reader)
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
