using System.Diagnostics;
using System.Reflection;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text.Json;
using ProfileStore.Benchmark;

try
{
  if (args is ["--render-charts", var renderJsonReportPath])
  {
    await RenderChartsAsync(renderJsonReportPath, CancellationToken.None);
    return;
  }
  if (args is ["--render-markdown", var renderMarkdownJsonReportPath])
  {
    await RenderMarkdownAsync(renderMarkdownJsonReportPath, CancellationToken.None);
    return;
  }
  if (args is ["--render-reference-reports"])
  {
    await RenderReferenceReportsAsync(referenceDirectory: null, CancellationToken.None);
    return;
  }
  if (args is ["--render-reference-reports", var referenceDirectory])
  {
    await RenderReferenceReportsAsync(referenceDirectory, CancellationToken.None);
    return;
  }

  var config = BenchmarkConfig.Parse(args);
  ApplyCleanup(config);
  var engines = BenchmarkRunner.ExpandEngines(config.Engine);

  if (config.ChildRun)
  {
    var childConfig = config.ForProfileCount(config.Profiles).ForParallelism(config.Parallelism);
    var result = await new BenchmarkRunner(childConfig).RunSingleAsync(CancellationToken.None);
    if (config.ResultFile != null)
    {
      var directory = Path.GetDirectoryName(config.ResultFile);
      if (!string.IsNullOrWhiteSpace(directory))
        Directory.CreateDirectory(directory);
      var json = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
      await File.WriteAllTextAsync(config.ResultFile, json, CancellationToken.None);
    }
    else
    {
      await ResultWriter.WriteAsync([result], config.OutputDirectory, CancellationToken.None);
    }
    return;
  }

  foreach (var profileCount in config.ProfileCounts)
  {
    var profileConfig = config.ForProfileCount(profileCount);
    foreach (var parallelism in config.ParallelismLevels)
      await RunProfileCountAsync(profileConfig.ForParallelism(parallelism), engines, CancellationToken.None);
  }
}
catch (HelpRequestedException)
{
  PrintHelp();
}
catch (Exception ex)
{
  Console.Error.WriteLine(ex);
  Environment.ExitCode = 1;
}

static void PrintHelp()
{
  Console.WriteLine("""
      Profile Store Benchmark

      Options:
        --engine zonetree|rocksdb|sqlite|mysql|all|comma,list
        --profiles <count|count,list>
        --parallelism <count|count,list>
        --read-count <count>
        --email-read-count <count>
        --query-count <count>
        --update-count <count>
        --post-read-count <count>
        --post-email-read-count <count>
        --post-query-count <count>
        --query-limit <count>
        --seed <int>
        --timeout-seconds <seconds>
        --output <directory>
        --data <directory>
        --zonetree-mutable-segment-max-item-count <count>
        --zonetree-block-cache-lifetime-minutes <minutes>
        --zonetree-sparse-array-step-size <count>
        --zonetree-key-cache-size <count>
        --zonetree-value-cache-size <count>
        --zonetree-iterator-prefetch-size <count>
        --sqlite-cache-mb <mb>
        --sqlite-mmap-mb <mb>
        --rocksdb-write-buffer-mb <mb>
        --rocksdb-max-write-buffer-number <count>
        --clean
        --clean-data
        --clean-results
        --mysql-host <host>
        --mysql-port <port>
        --mysql-database <database>
        --mysql-user <user>
        --mysql-password <password>
        --render-charts <profile-store-report.json>
        --render-markdown <profile-store-report.json>
        --render-reference-reports [reference-directory]
        --update-latest

      Example:
        dotnet run --project src/ProfileStore.Benchmark.csproj -c Release -- --engine zonetree,rocksdb,sqlite --profiles 100K,1M --parallelism 1,4,8
      """);
}

static async Task RunProfileCountAsync(
    BenchmarkConfig config,
    IReadOnlyList<string> engines,
    CancellationToken ct)
{
  IReadOnlyList<BenchmarkResult> results;
  if (engines.Count == 1)
    results = [await new BenchmarkRunner(config).RunSingleAsync(ct)];
  else
    results = await RunChildProcessesAsync(config, engines, ct);

  ValidateChecksums(results);
  await ResultWriter.WriteAsync(results, config.OutputDirectory, ct);
  if (config.UpdateLatest)
    await UpdateLatestAsync(results, ct);
}

static void ApplyCleanup(BenchmarkConfig config)
{
  if (config.ChildRun)
    return;
  if (config.CleanData)
    DeleteDirectory(config.DataDirectory);
  if (config.CleanResults)
    DeleteDirectory(config.OutputDirectory);
}

static void DeleteDirectory(string path)
{
  if (Directory.Exists(path))
    Directory.Delete(path, recursive: true);
}

static async Task RenderChartsAsync(string jsonReportPath, CancellationToken ct)
{
  var report = await ReadReportAsync(jsonReportPath, ct);
  var charts = await BenchmarkChartWriter.WriteAsync(
      report.Results,
      report.Directory,
      report.Stamp,
      report.FilePrefix,
      ct);
  await ResultWriter.WriteMarkdownAsync(report.Results, report.MarkdownPath, charts, ct);
  foreach (var chart in charts)
    Console.WriteLine($"Wrote {Path.Combine(report.Directory, chart.FileName)}");
  Console.WriteLine($"Wrote {report.MarkdownPath}");
}

static async Task RenderMarkdownAsync(string jsonReportPath, CancellationToken ct)
{
  var report = await ReadReportAsync(jsonReportPath, ct);
  var charts = BenchmarkChartWriter.GetChartArtifacts(report.FilePrefix)
      .Where(chart => File.Exists(Path.Combine(report.Directory, chart.FileName)))
      .ToArray();
  await ResultWriter.WriteMarkdownAsync(report.Results, report.MarkdownPath, charts, ct);
  Console.WriteLine($"Wrote {report.MarkdownPath}");
}

static async Task RenderReferenceReportsAsync(string? referenceDirectory, CancellationToken ct)
{
  referenceDirectory ??= Path.Combine(FindBenchmarkDirectory(), "reference");
  if (!Directory.Exists(referenceDirectory))
    throw new DirectoryNotFoundException($"Reference directory was not found: {referenceDirectory}");

  var jsonReportPaths = Directory
      .EnumerateFiles(referenceDirectory, "latest.json", SearchOption.AllDirectories)
      .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
      .ToArray();

  if (jsonReportPaths.Length == 0)
  {
    Console.WriteLine($"No latest.json files found under {referenceDirectory}");
    return;
  }

  foreach (var jsonReportPath in jsonReportPaths)
  {
    var report = await ReadReportAsync(jsonReportPath, ct);
    foreach (var staleChart in Directory.GetFiles(report.Directory, "latest-*.svg"))
      File.Delete(staleChart);

    var charts = await BenchmarkChartWriter.WriteAsync(
        report.Results,
        report.Directory,
        "latest",
        "latest",
        ct);
    await ResultWriter.WriteMarkdownAsync(report.Results, report.MarkdownPath, charts, ct);
    Console.WriteLine($"Wrote {report.MarkdownPath}");
    foreach (var chart in charts)
      Console.WriteLine($"Wrote {Path.Combine(report.Directory, chart.FileName)}");
  }
}

static async Task<(string Directory, string FileName, string Stamp, string FilePrefix, string MarkdownPath, IReadOnlyList<BenchmarkResult> Results)> ReadReportAsync(
    string jsonReportPath,
    CancellationToken ct)
{
  var directory = Path.GetDirectoryName(jsonReportPath);
  if (string.IsNullOrWhiteSpace(directory))
    directory = Directory.GetCurrentDirectory();
  var fileName = Path.GetFileNameWithoutExtension(jsonReportPath);
  var stamp = fileName.StartsWith("profile-store-", StringComparison.Ordinal)
      ? fileName["profile-store-".Length..]
      : fileName;
  var filePrefix = fileName.StartsWith("profile-store-", StringComparison.Ordinal)
      ? fileName
      : stamp;
  var json = await File.ReadAllTextAsync(jsonReportPath, ct);
  var results = JsonSerializer.Deserialize<IReadOnlyList<BenchmarkResult>>(json)
      ?? throw new InvalidOperationException($"Could not read benchmark results from {jsonReportPath}.");
  var markdownPath = Path.Combine(directory, $"{fileName}.md");
  return (directory, fileName, stamp, filePrefix, markdownPath, results);
}

static async Task UpdateLatestAsync(IReadOnlyList<BenchmarkResult> results, CancellationToken ct)
{
  if (results.Count == 0)
    throw new InvalidOperationException("Benchmark results are empty.");

  var profileDirectory = ResultWriter.GetProfileOutputDirectory(
      "",
      results[0].Workload.Profiles,
      results[0].Workload.Parallelism);
  var referenceDirectory = Path.Combine(
      FindBenchmarkDirectory(),
      "reference",
      GetReferencePlatformDirectoryName(),
      profileDirectory);
  Directory.CreateDirectory(referenceDirectory);

  foreach (var staleChart in Directory.GetFiles(referenceDirectory, "latest-*.svg"))
    File.Delete(staleChart);

  var charts = await BenchmarkChartWriter.WriteAsync(
      results,
      referenceDirectory,
      "latest",
      "latest",
      ct);

  var latestJsonPath = Path.Combine(referenceDirectory, "latest.json");
  var latestMarkdownPath = Path.Combine(referenceDirectory, "latest.md");
  var formattedJson = JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true });
  await File.WriteAllTextAsync(latestJsonPath, formattedJson, ct);
  await ResultWriter.WriteMarkdownAsync(results, latestMarkdownPath, charts, ct);

  Console.WriteLine($"Wrote {latestJsonPath}");
  Console.WriteLine($"Wrote {latestMarkdownPath}");
  foreach (var chart in charts)
    Console.WriteLine($"Wrote {Path.Combine(referenceDirectory, chart.FileName)}");
}

static string FindBenchmarkDirectory()
{
  var currentDirectory = Directory.GetCurrentDirectory();
  var direct = Path.Combine(currentDirectory, "src", "ProfileStore.Benchmark.csproj");
  if (File.Exists(direct))
    return currentDirectory;

  var fromRepoRoot = Path.Combine(currentDirectory, "benchmarks", "profile-store", "src", "ProfileStore.Benchmark.csproj");
  if (File.Exists(fromRepoRoot))
    return Path.Combine(currentDirectory, "benchmarks", "profile-store");

  var directory = new DirectoryInfo(currentDirectory);
  while (directory != null)
  {
    var candidate = Path.Combine(directory.FullName, "src", "ProfileStore.Benchmark.csproj");
    if (File.Exists(candidate))
      return directory.FullName;
    directory = directory.Parent;
  }

  throw new InvalidOperationException(
      "Could not locate benchmarks/profile-store. Run from the repository root or benchmarks/profile-store directory.");
}

static string GetReferencePlatformDirectoryName()
{
  if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
    return "win";
  if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
    return "linux";
  if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
    return "macos";
  return "unknown";
}

static async Task<IReadOnlyList<BenchmarkResult>> RunChildProcessesAsync(
    BenchmarkConfig config,
    IReadOnlyList<string> engines,
    CancellationToken ct)
{
  var runDirectory = Path.Combine(
      ResultWriter.GetProfileOutputDirectory(config.OutputDirectory, config.Profiles, config.Parallelism),
      ".runs",
      DateTime.UtcNow.ToString("yyyyMMdd-HHmmss"));
  Directory.CreateDirectory(runDirectory);

  var assemblyPath = Assembly.GetEntryAssembly()?.Location
      ?? throw new InvalidOperationException("Could not resolve benchmark assembly path.");

  var results = new List<BenchmarkResult>();
  foreach (var engine in engines)
  {
    var resultPath = Path.Combine(runDirectory, $"{engine}.json");
    var psi = new ProcessStartInfo("dotnet")
    {
      UseShellExecute = false,
      WorkingDirectory = Directory.GetCurrentDirectory()
    };
    psi.ArgumentList.Add(assemblyPath);
    foreach (var arg in config.ToArguments(engine, childRun: true, resultPath))
      psi.ArgumentList.Add(arg);

    using var process = Process.Start(psi)
        ?? throw new InvalidOperationException($"Could not start child process for {engine}.");
    var childExited = await WaitForChildAsync(process, config, ct);
    if (!childExited)
    {
      TryKill(process);
      results.Add(CreateTimedOutChildResult(engine, config));
      continue;
    }
    if (process.ExitCode != 0)
      throw new InvalidOperationException($"{engine} child process failed with exit code {process.ExitCode}.");
    if (!File.Exists(resultPath))
      throw new InvalidOperationException($"{engine} child process did not write {resultPath}.");

    var json = await File.ReadAllTextAsync(resultPath, ct);
    var result = JsonSerializer.Deserialize<BenchmarkResult>(json)
        ?? throw new InvalidOperationException($"Could not read child result {resultPath}.");
    results.Add(result);
  }
  return results;
}

static async Task<bool> WaitForChildAsync(
    Process process,
    BenchmarkConfig config,
    CancellationToken ct)
{
  if (config.TimeoutSeconds <= 0)
  {
    await process.WaitForExitAsync(ct);
    return true;
  }

  var waitTask = process.WaitForExitAsync(ct);
  var timeout = TimeSpan.FromSeconds(config.TimeoutSeconds + 30);
  var completed = await Task.WhenAny(waitTask, Task.Delay(timeout, ct));
  if (completed != waitTask)
    return false;

  await waitTask;
  return true;
}

static void TryKill(Process process)
{
  try
  {
    if (!process.HasExited)
      process.Kill(entireProcessTree: true);
  }
  catch (InvalidOperationException)
  {
  }
}

static BenchmarkResult CreateTimedOutChildResult(string engine, BenchmarkConfig config)
{
  var engineName = engine switch
  {
    "zonetree" => "ZoneTree",
    "rocksdb" => "RocksDB",
    "sqlite" => "SQLite",
    "mysql" => "MySQL",
    _ => engine
  };
  return new BenchmarkResult(
      engineName,
      "Not available.",
      DateTime.UtcNow.ToString("O"),
      CreateWorkloadConfig(config),
      BenchmarkRunner.CreateEngineSettings(engineName, config),
      Completed: false,
      Status: $"Timed out after {config.TimeoutSeconds:N0} seconds; child process did not write a partial result",
      Phases: [],
      RunElapsedMs: TimeSpan.FromSeconds(config.TimeoutSeconds + 30).TotalMilliseconds,
      PreReadStabilizeMs: null,
      PostUpdateStabilizeMs: null,
      SettleMs: null,
      StorageSizeBytes: null,
      ReopenMs: null,
      VerifyMs: null,
      VerifyChecksum: null,
      PeakProcessWorkingSetBytes: null,
      Environment: BenchmarkRunner.GetEnvironment(initialProcessWorkingSetBytes: null));
}

static BenchmarkWorkloadConfig CreateWorkloadConfig(BenchmarkConfig config)
{
  return new BenchmarkWorkloadConfig(
      config.Profiles,
      config.Parallelism,
      config.ReadCount,
      config.EmailReadCount,
      config.QueryCount,
      config.UpdateCount,
      config.PostReadCount,
      config.PostEmailReadCount,
      config.PostQueryCount,
      config.QueryLimit,
      config.Seed,
      config.TimeoutSeconds);
}

static void ValidateChecksums(IReadOnlyList<BenchmarkResult> results)
{
  var completed = results.Where(x => x.Completed).ToArray();
  if (completed.Length <= 1)
    return;

  var expected = completed[0];
  foreach (var result in completed.Skip(1))
  {
    if (result.Phases.Count != expected.Phases.Count)
      throw new InvalidOperationException($"Phase count mismatch between {expected.Engine} and {result.Engine}.");

    for (var i = 0; i < expected.Phases.Count; i++)
    {
      var left = expected.Phases[i];
      var right = result.Phases[i];
      if (left.Name != right.Name)
        throw new InvalidOperationException($"Phase name mismatch: {left.Name} vs {right.Name}.");
      if (left.Checksum != right.Checksum)
      {
        throw new InvalidOperationException(
            $"Checksum mismatch in phase '{left.Name}': {expected.Engine}={left.Checksum}, {result.Engine}={right.Checksum}.");
      }
    }

    if (expected.VerifyChecksum != result.VerifyChecksum)
    {
      throw new InvalidOperationException(
          $"Verify checksum mismatch: {expected.Engine}={expected.VerifyChecksum}, {result.Engine}={result.VerifyChecksum}.");
    }
  }
}
