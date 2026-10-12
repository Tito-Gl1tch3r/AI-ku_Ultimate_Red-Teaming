using System.Globalization;

namespace ZoneTree.FasterBench;

public sealed record BenchmarkConfig
{
  public int Records { get; init; } = 1_000_000;

  public int Reads { get; init; } = 1_000_000;

  public int Iterations { get; init; } = 3;

  public int WarmupRecords { get; init; } = 20_000;

  public int[] Parallelism { get; init; } = [1, 16];

  public string[] Engines { get; init; } = ["zonetree", "faster"];

  public string DataDirectory { get; init; } = "data";

  public int FasterIndexSize { get; init; } = 1 << 20;

  public int FasterMemoryBits { get; init; } = 30;

  public int Seed { get; init; } = 570123434;

  public static BenchmarkConfig Parse(string[] args)
  {
    var config = new BenchmarkConfig();
    for (var i = 0; i < args.Length; ++i)
    {
      var option = args[i].ToLowerInvariant();
      string Next() => i + 1 < args.Length
          ? args[++i]
          : throw new ArgumentException($"Missing value for {args[i]}.");

      config = option switch
      {
        "--records" => config with { Records = ParseCount(Next()) },
        "--reads" => config with { Reads = ParseCount(Next()) },
        "--iterations" => config with { Iterations = int.Parse(Next(), CultureInfo.InvariantCulture) },
        "--warmup" => config with { WarmupRecords = ParseCount(Next()) },
        "--parallelism" => config with { Parallelism = ParseIntList(Next()) },
        "--engine" or "--engines" => config with { Engines = ParseStringList(Next()) },
        "--data" => config with { DataDirectory = Next() },
        "--faster-index-size" => config with { FasterIndexSize = ParseCount(Next()) },
        "--faster-memory-bits" => config with { FasterMemoryBits = int.Parse(Next(), CultureInfo.InvariantCulture) },
        "--seed" => config with { Seed = int.Parse(Next(), CultureInfo.InvariantCulture) },
        "--help" or "-h" => throw new HelpRequestedException(),
        _ => throw new ArgumentException($"Unknown option: {args[i]}")
      };
    }

    Validate(config);
    return config with { DataDirectory = Path.GetFullPath(config.DataDirectory) };
  }

  static void Validate(BenchmarkConfig config)
  {
    if (config.Records < 1)
      throw new ArgumentOutOfRangeException(nameof(Records));
    if (config.Reads < 1)
      throw new ArgumentOutOfRangeException(nameof(Reads));
    if (config.Iterations < 1)
      throw new ArgumentOutOfRangeException(nameof(Iterations));
    if (config.WarmupRecords < 0)
      throw new ArgumentOutOfRangeException(nameof(WarmupRecords));
    if (config.FasterIndexSize < 1)
      throw new ArgumentOutOfRangeException(nameof(FasterIndexSize));
    if ((config.FasterIndexSize & (config.FasterIndexSize - 1)) != 0)
      throw new ArgumentException(
          "FASTER index size must be a power of two.",
          nameof(FasterIndexSize));
    if (config.FasterMemoryBits is < 20 or > 40)
      throw new ArgumentOutOfRangeException(nameof(FasterMemoryBits));
    if (config.Parallelism.Length == 0 || config.Parallelism.Any(x => x < 1))
      throw new ArgumentOutOfRangeException(nameof(Parallelism));
    if (config.Engines.Length == 0 || config.Engines.Any(x => x is not "zonetree" and not "faster"))
      throw new ArgumentException("Engines must contain zonetree and/or faster.", nameof(Engines));
  }

  static int[] ParseIntList(string value) =>
      value.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
          .Select(x => int.Parse(x, CultureInfo.InvariantCulture))
          .Distinct()
          .ToArray();

  static string[] ParseStringList(string value) =>
      value.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
          .Select(x => x.ToLowerInvariant())
          .Distinct()
          .ToArray();

  static int ParseCount(string value)
  {
    value = value.Trim();
    var multiplier = 1L;
    if (value.EndsWith("K", StringComparison.OrdinalIgnoreCase))
    {
      multiplier = 1_000;
      value = value[..^1];
    }
    else if (value.EndsWith("M", StringComparison.OrdinalIgnoreCase))
    {
      multiplier = 1_000_000;
      value = value[..^1];
    }

    var result = checked(long.Parse(value, CultureInfo.InvariantCulture) * multiplier);
    return checked((int)result);
  }
}

public sealed class HelpRequestedException : Exception;
