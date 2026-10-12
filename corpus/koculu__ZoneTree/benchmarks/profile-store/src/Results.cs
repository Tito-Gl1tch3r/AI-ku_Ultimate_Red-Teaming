using System.Diagnostics;
using System.Globalization;
using System.Text.Json;

namespace ProfileStore.Benchmark;

public sealed record PhaseResult(
    string Name,
    long Operations,
    double ElapsedMs,
    double OperationsPerSecond,
    string Checksum);

public sealed record BenchmarkWorkloadConfig(
    int Profiles,
    int Parallelism,
    int ReadCount,
    int EmailReadCount,
    int QueryCount,
    int UpdateCount,
    int PostReadCount,
    int PostEmailReadCount,
    int PostQueryCount,
    int QueryLimit,
    int Seed,
    int TimeoutSeconds);

public sealed record BenchmarkResult(
    string Engine,
    string Durability,
    string StartedAtUtc,
    BenchmarkWorkloadConfig Workload,
    IReadOnlyDictionary<string, string> EngineSettings,
    bool Completed,
    string? Status,
    IReadOnlyList<PhaseResult> Phases,
    double RunElapsedMs,
    double? PreReadStabilizeMs,
    double? PostUpdateStabilizeMs,
    double? SettleMs,
    long? StorageSizeBytes,
    double? ReopenMs,
    double? VerifyMs,
    string? VerifyChecksum,
    long? PeakProcessWorkingSetBytes,
    string Environment)
{
  public string? InterruptedPhase { get; init; }
}

public static class ResultWriter
{
  public static async Task WriteAsync(
      IReadOnlyList<BenchmarkResult> results,
      string outputDirectory,
      CancellationToken ct)
  {
    outputDirectory = GetProfileOutputDirectory(
        outputDirectory,
        results[0].Workload.Profiles,
        results[0].Workload.Parallelism);
    Directory.CreateDirectory(outputDirectory);
    var stamp = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
    var jsonPath = Path.Combine(outputDirectory, $"profile-store-{stamp}.json");
    var markdownPath = Path.Combine(outputDirectory, $"profile-store-{stamp}.md");
    var charts = await BenchmarkChartWriter.WriteAsync(results, outputDirectory, stamp, ct);

    var json = JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true });
    await File.WriteAllTextAsync(jsonPath, json, ct);
    await WriteMarkdownAsync(results, markdownPath, charts, ct);

    Console.WriteLine($"Wrote {jsonPath}");
    Console.WriteLine($"Wrote {markdownPath}");
    foreach (var chart in charts)
      Console.WriteLine($"Wrote {Path.Combine(outputDirectory, chart.FileName)}");
  }

  public static string GetProfileOutputDirectory(
      string outputDirectory,
      int profiles,
      int parallelism = 1)
  {
    var directory = $"profiles-{profiles.ToString(CultureInfo.InvariantCulture)}";
    if (parallelism > 1)
      directory += $"-p{parallelism.ToString(CultureInfo.InvariantCulture)}";
    return Path.Combine(outputDirectory, directory);
  }

  public static Task WriteMarkdownAsync(
      IReadOnlyList<BenchmarkResult> results,
      string markdownPath,
      IReadOnlyList<ChartArtifact> charts,
      CancellationToken ct)
  {
    return File.WriteAllTextAsync(markdownPath, ToMarkdown(results, charts), ct);
  }

  static string ToMarkdown(IReadOnlyList<BenchmarkResult> results, IReadOnlyList<ChartArtifact> charts)
  {
    var first = results[0];
    var writer = new StringWriter();
    writer.WriteLine($"# Benchmark {FormatProfileCount(first.Workload.Profiles)} Profiles{FormatParallelismTitle(GetParallelism(first.Workload))}{FormatTitleOsSuffix(results)}");
    writer.WriteLine();
    writer.WriteLine("## Charts");
    writer.WriteLine();
    foreach (var chart in charts)
    {
      writer.WriteLine($"### {chart.Title}");
      writer.WriteLine();
      writer.WriteLine($"![{chart.Title}]({chart.FileName})");
      writer.WriteLine();
    }
    writer.WriteLine("## Total By Engine");
    writer.WriteLine();
    writer.WriteLine("| Engine | Status | Run time | Completed phase time | Pre-read stabilize | Post-update stabilize | Settle | Reopen | Verify | Storage | Process peak memory | Final checksum |");
    writer.WriteLine("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |");
    foreach (var result in results)
    {
      var total = result.Phases.Sum(x => x.ElapsedMs);
      writer.WriteLine($"| {result.Engine} | {FormatStatus(result)} | {FormatMilliseconds(result.RunElapsedMs)} | {FormatMilliseconds(total)} | {FormatMilliseconds(result.PreReadStabilizeMs)} | {FormatMilliseconds(result.PostUpdateStabilizeMs)} | {FormatMilliseconds(result.SettleMs)} | {FormatMilliseconds(result.ReopenMs)} | {FormatMilliseconds(result.VerifyMs)} | {FormatBytes(result.StorageSizeBytes)} | {FormatBytes(result.PeakProcessWorkingSetBytes)} | {FormatChecksum(result.VerifyChecksum)} |");
    }
    writer.WriteLine();
    writer.WriteLine("## Correctness");
    writer.WriteLine();
    writer.WriteLine(FormatCorrectnessSummary(results));
    writer.WriteLine();
    writer.WriteLine("## Interpretation Notes");
    writer.WriteLine();
    foreach (var note in CreateInterpretationNotes(results))
      writer.WriteLine($"* {note}");
    writer.WriteLine();
    WriteWriteReadiness(writer, results);
    writer.WriteLine("## Phase Results");
    writer.WriteLine();
    foreach (var result in results)
    {
      writer.WriteLine($"### {result.Engine}");
      writer.WriteLine();
      if (!string.IsNullOrWhiteSpace(result.InterruptedPhase))
      {
        writer.WriteLine($"Interrupted: {result.InterruptedPhase}");
        writer.WriteLine();
      }
      writer.WriteLine("| Phase | Operations | Time | Throughput | Checksum |");
      writer.WriteLine("| --- | ---: | ---: | ---: | --- |");
      foreach (var phase in result.Phases)
      {
        writer.WriteLine($"| {phase.Name} | {FormatInteger(phase.Operations)} | {FormatMilliseconds(phase.ElapsedMs)} | {FormatInteger(phase.OperationsPerSecond)}/s | `{phase.Checksum}` |");
      }
      writer.WriteLine();
    }
    writer.WriteLine("## Configuration");
    writer.WriteLine();
    writer.WriteLine($"* Profiles: {FormatInteger(first.Workload.Profiles)}");
    writer.WriteLine($"* Parallelism: {FormatInteger(GetParallelism(first.Workload))}");
    writer.WriteLine("* Profile writes: individual operations");
    writer.WriteLine($"* UserId reads: {FormatInteger(first.Workload.ReadCount)}");
    writer.WriteLine($"* Email lookups: {FormatInteger(first.Workload.EmailReadCount)}");
    writer.WriteLine($"* Query count: {FormatInteger(first.Workload.QueryCount)}");
    writer.WriteLine($"* Profile updates: {FormatInteger(first.Workload.UpdateCount)}");
    writer.WriteLine($"* Post-update UserId reads: {FormatInteger(first.Workload.PostReadCount)}");
    writer.WriteLine($"* Post-update email lookups: {FormatInteger(first.Workload.PostEmailReadCount)}");
    writer.WriteLine($"* Post-update query count: {FormatInteger(first.Workload.PostQueryCount)}");
    writer.WriteLine($"* Query limit: {FormatInteger(first.Workload.QueryLimit)}");
    writer.WriteLine($"* Seed: {first.Workload.Seed}");
    writer.WriteLine(first.Workload.TimeoutSeconds > 0
        ? $"* Timeout: {FormatInteger(first.Workload.TimeoutSeconds)} seconds per engine"
        : "* Timeout: disabled");
    writer.WriteLine();
    writer.WriteLine("## Environment");
    writer.WriteLine();
    writer.WriteLine(first.Environment);
    writer.WriteLine();
    writer.WriteLine("## Engine Settings");
    writer.WriteLine();
    foreach (var result in results)
    {
      writer.WriteLine($"### {result.Engine}");
      writer.WriteLine();
      if (result.EngineSettings.Count == 0)
      {
        writer.WriteLine("* n/a");
      }
      else
      {
        foreach (var setting in result.EngineSettings)
          writer.WriteLine($"* {setting.Key}: {setting.Value}");
      }
      writer.WriteLine();
    }
    writer.WriteLine("## Durability Settings");
    writer.WriteLine();
    foreach (var result in results)
      writer.WriteLine($"* {result.Engine}: {result.Durability}");
    return writer.ToString();
  }

  static void WriteWriteReadiness(StringWriter writer, IReadOnlyList<BenchmarkResult> results)
  {
    var rows = results
        .Select(CreateWriteReadinessRow)
        .Where(row => row.Insert != null || row.Update != null)
        .ToArray();
    if (rows.Length == 0)
      return;

    writer.WriteLine("## Write Readiness");
    writer.WriteLine();
    writer.WriteLine("| Engine | Insert | Pre-read stabilize | Insert + stabilize | Insert ready throughput | Update | Post-update stabilize | Update + stabilize | Update ready throughput |");
    writer.WriteLine("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |");
    foreach (var row in rows)
    {
      writer.WriteLine($"| {row.Engine} | {FormatMilliseconds(row.Insert?.ElapsedMs)} | {FormatMilliseconds(row.PreReadStabilizeMs)} | {FormatMilliseconds(row.InsertReadyMs)} | {FormatThroughput(row.InsertReadyThroughput)} | {FormatMilliseconds(row.Update?.ElapsedMs)} | {FormatMilliseconds(row.PostUpdateStabilizeMs)} | {FormatMilliseconds(row.UpdateReadyMs)} | {FormatThroughput(row.UpdateReadyThroughput)} |");
    }
    writer.WriteLine();
  }

  static WriteReadinessRow CreateWriteReadinessRow(BenchmarkResult result)
  {
    var insert = result.Phases.FirstOrDefault(x => x.Name == "insert profiles");
    var update = result.Phases.FirstOrDefault(x => x.Name == "update profiles");
    var insertReadyMs = AddStabilizeMs(insert, result.PreReadStabilizeMs);
    var updateReadyMs = AddStabilizeMs(update, result.PostUpdateStabilizeMs);
    return new WriteReadinessRow(
        result.Engine,
        insert,
        result.PreReadStabilizeMs,
        insertReadyMs,
        CalculateThroughput(insert?.Operations, insertReadyMs),
        update,
        result.PostUpdateStabilizeMs,
        updateReadyMs,
        CalculateThroughput(update?.Operations, updateReadyMs));
  }

  static double? AddStabilizeMs(PhaseResult? phase, double? stabilizeMs) =>
      phase == null ? null : phase.ElapsedMs + (stabilizeMs ?? 0);

  static double? CalculateThroughput(long? operations, double? elapsedMs)
  {
    if (!operations.HasValue || !elapsedMs.HasValue || elapsedMs.Value <= 0)
      return null;
    return operations.Value / (elapsedMs.Value / 1000);
  }

  static IReadOnlyList<string> CreateInterpretationNotes(IReadOnlyList<BenchmarkResult> results)
  {
    var engines = results.Select(x => x.Engine).ToHashSet(StringComparer.OrdinalIgnoreCase);
    var notes = new List<string>
    {
      "This benchmark measures live single-operation profile inserts, updates, reads, and indexed queries."
    };

    if (engines.Contains("ZoneTree") && engines.Contains("RocksDB"))
    {
      notes.Add(
          "ZoneTree and RocksDB secondary indexes are maintained by the benchmark application using separate stores.");
    }
    else if (engines.Contains("ZoneTree"))
    {
      notes.Add(
          "ZoneTree secondary indexes are maintained by the benchmark application using separate ZoneTree instances.");
    }
    else if (engines.Contains("RocksDB"))
    {
      notes.Add(
          "RocksDB secondary indexes are maintained by the benchmark application using separate RocksDB databases.");
    }

    if (engines.Contains("SQLite") && engines.Contains("MySQL"))
      notes.Add("SQLite and MySQL maintain secondary indexes inside the database engine.");
    else if (engines.Contains("SQLite"))
      notes.Add("SQLite maintains secondary indexes inside the database engine.");
    else if (engines.Contains("MySQL"))
      notes.Add("MySQL maintains secondary indexes inside the database engine.");

    if (engines.Contains("MySQL"))
      notes.Add("MySQL is measured as a client/server database over TCP.");
    if (engines.Any(engine => !engine.Equals("MySQL", StringComparison.OrdinalIgnoreCase)))
      notes.Add("Embedded engines run in the benchmark process.");

    notes.Add(
        "Completed phase time is the sum of measured workload phases. Run time also includes initialization, stabilization, settle/checkpoint, reopen, verification, and reporting overhead.");
    notes.Add(
        "The write throughput chart includes raw write phases and derived write-readiness bars that add the following stabilization phase.");
    notes.Add("Storage is measured after each engine settles or checkpoints its data.");

    if (engines.Contains("MySQL"))
    {
      notes.Add(
          "Process peak memory is measured for the benchmark process. For MySQL, this excludes MySQL server/container memory.");
    }
    else
    {
      notes.Add("Process peak memory is measured for the benchmark process.");
    }

    if (results.Any(x => !x.Completed))
    {
      notes.Add(
          "Timeout results include only completed phases, and checksum comparison is performed only across completed engines.");
    }

    return notes;
  }

  public static string FormatBytes(long bytes)
  {
    string[] units = ["B", "KB", "MB", "GB", "TB"];
    var value = (double)bytes;
    var unit = 0;
    while (value >= 1024 && unit < units.Length - 1)
    {
      value /= 1024;
      unit++;
    }
    return $"{value.ToString("N1", CultureInfo.InvariantCulture)} {units[unit]}";
  }

  public static string FormatBytes(long? bytes) =>
      bytes.HasValue ? FormatBytes(bytes.Value) : "n/a";

  static string FormatMilliseconds(double? milliseconds) =>
      milliseconds.HasValue ? $"{FormatInteger(milliseconds.Value)} ms" : "n/a";

  static string FormatThroughput(double? operationsPerSecond) =>
      operationsPerSecond.HasValue ? $"{FormatInteger(operationsPerSecond.Value)}/s" : "n/a";

  static string FormatInteger(double value) =>
      FormatInteger((long)Math.Round(value, MidpointRounding.AwayFromZero));

  static string FormatInteger(long value) =>
      value.ToString("N0", CultureInfo.InvariantCulture).Replace(",", "_");

  static string FormatProfileCount(int value)
  {
    if (value >= 1_000_000 && value % 1_000_000 == 0)
      return $"{value / 1_000_000}M";
    if (value >= 1_000 && value % 1_000 == 0)
      return $"{value / 1_000}K";
    return FormatInteger(value);
  }

  static string FormatParallelismTitle(int value) =>
      value > 1 ? $" / P{value.ToString(CultureInfo.InvariantCulture)}" : "";

  static int GetParallelism(BenchmarkWorkloadConfig workload) =>
      workload.Parallelism <= 0 ? 1 : workload.Parallelism;

  static string FormatTitleOsSuffix(IReadOnlyList<BenchmarkResult> results)
  {
    var suffix = GetTitleOsName(results[0].Environment);
    return suffix == null ? "" : $" - {suffix}";
  }

  static string? GetTitleOsName(string environment)
  {
    var osLine = environment
        .Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries)
        .FirstOrDefault(line => line.StartsWith("* OS:", StringComparison.OrdinalIgnoreCase));
    if (osLine == null)
      return null;

    var os = osLine["* OS:".Length..].Trim();
    if (os.Contains("Windows", StringComparison.OrdinalIgnoreCase))
      return "Windows";
    if (os.Contains("Ubuntu", StringComparison.OrdinalIgnoreCase)
        || os.Contains("Linux", StringComparison.OrdinalIgnoreCase)
        || os.Contains("Debian", StringComparison.OrdinalIgnoreCase)
        || os.Contains("Fedora", StringComparison.OrdinalIgnoreCase)
        || os.Contains("Red Hat", StringComparison.OrdinalIgnoreCase)
        || os.Contains("CentOS", StringComparison.OrdinalIgnoreCase))
      return "Linux";
    if (os.Contains("macOS", StringComparison.OrdinalIgnoreCase)
        || os.Contains("OSX", StringComparison.OrdinalIgnoreCase)
        || os.Contains("Darwin", StringComparison.OrdinalIgnoreCase))
      return "macOS";
    return null;
  }

  static string FormatChecksum(string? checksum) =>
      checksum == null ? "n/a" : $"`{checksum}`";

  static string FormatCorrectnessSummary(IReadOnlyList<BenchmarkResult> results)
  {
    var completed = results.Where(x => x.Completed).ToArray();
    var incomplete = results.Where(x => !x.Completed).Select(x => x.Engine).ToArray();
    if (completed.Length > 1)
    {
      var summary = $"Checksum validation passed across completed engines: {string.Join(", ", completed.Select(x => x.Engine))}.";
      if (incomplete.Length > 0)
        summary += $" Incomplete engines excluded: {string.Join(", ", incomplete)}.";
      return summary;
    }
    if (completed.Length == 1)
    {
      var summary = $"Single completed engine: {completed[0].Engine}; checksums were recorded but not compared with another completed engine.";
      if (incomplete.Length > 0)
        summary += $" Incomplete engines excluded: {string.Join(", ", incomplete)}.";
      return summary;
    }
    return "No engine completed; checksum comparison was not possible.";
  }

  static string FormatStatus(BenchmarkResult result)
  {
    if (result.Completed)
      return "Completed";
    if (string.IsNullOrWhiteSpace(result.InterruptedPhase))
      return result.Status ?? "Incomplete";
    return $"{result.Status ?? "Incomplete"}; interrupted: {result.InterruptedPhase}";
  }

  sealed record WriteReadinessRow(
      string Engine,
      PhaseResult? Insert,
      double? PreReadStabilizeMs,
      double? InsertReadyMs,
      double? InsertReadyThroughput,
      PhaseResult? Update,
      double? PostUpdateStabilizeMs,
      double? UpdateReadyMs,
      double? UpdateReadyThroughput);
}

public static class Timing
{
  public static async Task<(double elapsedMs, T result)> MeasureAsync<T>(Func<Task<T>> action)
  {
    var sw = Stopwatch.StartNew();
    var result = await action();
    sw.Stop();
    return (sw.Elapsed.TotalMilliseconds, result);
  }
}
