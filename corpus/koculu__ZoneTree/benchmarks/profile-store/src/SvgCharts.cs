using System.Globalization;
using System.Net;
using System.Text;

namespace ProfileStore.Benchmark;

public sealed record ChartArtifact(string Title, string FileName);

public sealed class SvgChartBuilder(int width, int height, string title, string subtitle = "")
{
  public const double MarginLeft = 48;
  public const double TitleY = 44;
  public const double SubtitleY = 72;
  public const double ContentTop = 112;

  readonly StringBuilder Body = new();
  readonly Dictionary<string, string> Colors = new(StringComparer.OrdinalIgnoreCase)
  {
    ["ZoneTree"] = "#16a34a",
    ["RocksDB"] = "#7c3aed",
    ["SQLite"] = "#dc2626",
    ["MySQL"] = "#2563eb"
  };
  readonly string[] Palette =
  [
    "#ea580c",
    "#0891b2",
    "#4f46e5",
    "#65a30d"
  ];

  int ColorIndex;

  public string ColorFor(string key)
  {
    if (Colors.TryGetValue(key, out var color))
      return color;
    color = Palette[ColorIndex % Palette.Length];
    Colors[key] = color;
    ColorIndex++;
    return color;
  }

  public void Text(
      double x,
      double y,
      string text,
      int size = 13,
      string fill = "#111827",
      string anchor = "start",
      string weight = "400")
  {
    Body.Append(CultureInfo.InvariantCulture, $"<text x=\"{x:0.##}\" y=\"{y:0.##}\" font-size=\"{size}\" fill=\"{fill}\" text-anchor=\"{anchor}\" font-weight=\"{weight}\">{Escape(text)}</text>");
  }

  public void Rect(double x, double y, double rectWidth, double rectHeight, string fill, double radius = 0, string stroke = "")
  {
    var strokePart = string.IsNullOrEmpty(stroke) ? "" : $" stroke=\"{stroke}\"";
    Body.Append(CultureInfo.InvariantCulture, $"<rect x=\"{x:0.##}\" y=\"{y:0.##}\" width=\"{Math.Max(0, rectWidth):0.##}\" height=\"{Math.Max(0, rectHeight):0.##}\" rx=\"{radius:0.##}\" fill=\"{fill}\"{strokePart}/>");
  }

  public void Line(double x1, double y1, double x2, double y2, string stroke = "#e5e7eb", double strokeWidth = 1)
  {
    Body.Append(CultureInfo.InvariantCulture, $"<line x1=\"{x1:0.##}\" y1=\"{y1:0.##}\" x2=\"{x2:0.##}\" y2=\"{y2:0.##}\" stroke=\"{stroke}\" stroke-width=\"{strokeWidth:0.##}\"/>");
  }

  public string Build()
  {
    var titleBlock = new StringBuilder();
    titleBlock.Append(CultureInfo.InvariantCulture, $"<text x=\"{MarginLeft:0}\" y=\"{TitleY:0}\" font-size=\"24\" font-weight=\"800\" fill=\"#111827\">{Escape(title)}</text>");
    if (!string.IsNullOrWhiteSpace(subtitle))
      titleBlock.Append(CultureInfo.InvariantCulture, $"<text x=\"{MarginLeft:0}\" y=\"{SubtitleY:0}\" font-size=\"13\" fill=\"#6b7280\">{Escape(subtitle)}</text>");

    return $$"""
        <svg xmlns="http://www.w3.org/2000/svg" width="{{width}}" height="{{height}}" viewBox="0 0 {{width}} {{height}}" role="img" aria-label="{{Escape(title)}}">
          <style>
            text { font-family: Inter, Segoe UI, Arial, sans-serif; }
          </style>
          <rect width="100%" height="100%" fill="#ffffff"/>
          {{titleBlock}}
          {{Body}}
        </svg>
        """;
  }

  static string Escape(string value) =>
      WebUtility.HtmlEncode(value);
}

public static class BenchmarkChartWriter
{
  public static IReadOnlyList<ChartArtifact> GetChartArtifacts(string filePrefix) =>
  [
    new ChartArtifact("Execution Time", $"{filePrefix}-execution-time.svg"),
    new ChartArtifact("Write Throughput", $"{filePrefix}-write-throughput.svg"),
    new ChartArtifact("Lookup Throughput", $"{filePrefix}-lookup-throughput.svg"),
    new ChartArtifact("Index Scan Throughput", $"{filePrefix}-index-scan-throughput.svg"),
    new ChartArtifact("Query Throughput", $"{filePrefix}-query-throughput.svg"),
    new ChartArtifact("Resource Footprint", $"{filePrefix}-resources.svg")
  ];

  public static async Task<IReadOnlyList<ChartArtifact>> WriteAsync(
      IReadOnlyList<BenchmarkResult> results,
      string outputDirectory,
      string stamp,
      string filePrefix,
      CancellationToken ct)
  {
    if (string.IsNullOrWhiteSpace(filePrefix))
      filePrefix = $"profile-store-{stamp}";

    var artifacts = GetChartArtifacts(filePrefix);
    var charts = new (ChartArtifact Artifact, string Svg)[]
    {
      (artifacts[0], CreateExecutionTime(results)),
      (artifacts[1], CreateWriteThroughput(results)),
      (artifacts[2], CreatePhaseThroughput(
          results,
          "Lookup Throughput",
          $"Grouped bars show relative throughput for point and email lookups{FormatParallelism(results)}; tallest bar per phase is 100%",
          ["read by user id", "lookup by email", "post-update read by user id", "post-update lookup by email"])),
      (artifacts[3], CreatePhaseThroughput(
          results,
          "Index Scan Throughput",
          $"Grouped bars show relative throughput for index-only scans{FormatParallelism(results)}; tallest bar per phase is 100%",
          ["scan country/status index", "scan created-at index", "scan top reputation index", "post-update scan country/status index", "post-update scan top reputation index"])),
      (artifacts[4], CreatePhaseThroughput(
          results,
          "Query Throughput",
          $"Grouped bars show relative throughput for indexed queries that fetch profiles{FormatParallelism(results)}; tallest bar per phase is 100%",
          ["query country/status", "query created-at range", "query top reputation", "post-update query country/status", "post-update query top reputation"])),
      (artifacts[5], CreateResources(results))
    };

    foreach (var chart in charts)
      await File.WriteAllTextAsync(Path.Combine(outputDirectory, chart.Artifact.FileName), chart.Svg, ct);
    return charts.Select(x => x.Artifact).ToArray();
  }

  public static Task<IReadOnlyList<ChartArtifact>> WriteAsync(
      IReadOnlyList<BenchmarkResult> results,
      string outputDirectory,
      string stamp,
      CancellationToken ct) =>
      WriteAsync(results, outputDirectory, stamp, $"profile-store-{stamp}", ct);

  static string CreateExecutionTime(IReadOnlyList<BenchmarkResult> results)
  {
    var complete = results
        .Select(result => new
        {
          result.Engine,
          PhaseMs = result.Phases.Sum(phase => phase.ElapsedMs),
          RunMs = result.RunElapsedMs,
          ColorKey = result.Engine
        })
        .Where(x => x.PhaseMs > 0)
        .OrderBy(x => x.PhaseMs)
        .ToArray();

    var fastest = Math.Max(1, complete.FirstOrDefault()?.PhaseMs ?? 1);
    var chart = new SvgChartBuilder(
        1360,
        174 + complete.Length * 62,
        "Profile Store Execution Time",
        $"{FormatCount(results[0].Workload.Profiles)} live profiles{FormatParallelism(results)}; completed phase time normalized to the fastest engine");

    const double headerY = SvgChartBuilder.ContentTop;
    const double firstRowY = headerY + 34;
    chart.Text(48, headerY, "Engine", 12, "#6b7280", weight: "700");
    chart.Text(338, headerY, "Relative throughput", 12, "#6b7280", weight: "700");
    chart.Text(930, headerY, "Delta", 12, "#6b7280", weight: "700");
    chart.Text(1_060, headerY, "Phase time", 12, "#6b7280", weight: "700");
    chart.Text(1_210, headerY, "Run time", 12, "#6b7280", weight: "700");

    for (var i = 0; i < complete.Length; i++)
    {
      var item = complete[i];
      var y = firstRowY + i * 62;
      var color = chart.ColorFor(item.ColorKey);
      var score = fastest / item.PhaseMs;
      var slower = item.PhaseMs / fastest;
      chart.Line(48, y + 24, 1_300, y + 24, "#f3f4f6");
      chart.Text(48, y, item.Engine, 17, "#111827", weight: "800");
      chart.Rect(338, y - 15, 540, 22, "#eef2f7", 11);
      chart.Rect(338, y - 15, Math.Max(8, 540 * score), 22, color, 11);
      chart.Text(930, y + 1, i == 0 ? "1.00x" : $"{slower.ToString("0.0", CultureInfo.InvariantCulture)}x", 13, "#374151", weight: "800");
      chart.Text(1_060, y + 1, FormatMs(item.PhaseMs), 14, "#111827", weight: "700");
      chart.Text(1_210, y + 1, FormatMs(item.RunMs), 14, "#4b5563");
    }

    chart.Text(338, firstRowY + complete.Length * 62 + 24, "Relative throughput is normalized to the fastest completed engine. Time columns remain absolute.", 12, "#6b7280");
    return chart.Build();
  }

  static string CreateWriteThroughput(IReadOnlyList<BenchmarkResult> results)
  {
    return CreateDataPointThroughput(
        results.Select(result =>
        {
          var points = new List<ThroughputDataPoint>();
          AddWritePhase(
              points,
              result,
              "insert profiles",
              "insert",
              "insert + stabilize",
              result.PreReadStabilizeMs);
          AddWritePhase(
              points,
              result,
              "update profiles",
              "update",
              "update + stabilize",
              result.PostUpdateStabilizeMs);
          return (result.Engine, Points: (IReadOnlyList<ThroughputDataPoint>)points);
        }).ToArray(),
        "Write Throughput",
        $"Raw write throughput{FormatParallelism(results)} and throughput after the following stabilization phase; tallest bar per group is 100%",
        ["insert", "insert + stabilize", "update", "update + stabilize"]);
  }

  static void AddWritePhase(
      List<ThroughputDataPoint> points,
      BenchmarkResult result,
      string phaseName,
      string rawLabel,
      string stabilizedLabel,
      double? stabilizeMs)
  {
    var phase = result.Phases.FirstOrDefault(p => p.Name == phaseName);
    if (phase == null)
      return;

    points.Add(new ThroughputDataPoint(rawLabel, phase.OperationsPerSecond));
    var readyMs = phase.ElapsedMs + (stabilizeMs ?? 0);
    if (readyMs > 0)
      points.Add(new ThroughputDataPoint(stabilizedLabel, phase.Operations / (readyMs / 1000)));
  }

  static string CreatePhaseThroughput(
      IReadOnlyList<BenchmarkResult> results,
      string title,
      string subtitle,
      IReadOnlyList<string> phaseNames)
  {
    return CreateDataPointThroughput(
        results.Select(result => (
            result.Engine,
            Points: (IReadOnlyList<ThroughputDataPoint>)result.Phases
                .Select(phase => new ThroughputDataPoint(phase.Name, phase.OperationsPerSecond))
                .ToArray()))
        .ToArray(),
        title,
        subtitle,
        phaseNames);
  }

  static string CreateDataPointThroughput(
      IReadOnlyList<(string Engine, IReadOnlyList<ThroughputDataPoint> Points)> results,
      string title,
      string subtitle,
      IReadOnlyList<string> phaseNames)
  {
    var available = results.SelectMany(r => r.Points.Select(p => p.Name)).ToHashSet(StringComparer.Ordinal);
    var phases = phaseNames.Where(available.Contains).ToArray();
    var engines = results.Select(r => r.Engine).ToArray();
    const double left = SvgChartBuilder.MarginLeft;
    const double chartTop = 144;
    const double plotHeight = 190;
    const double baseline = chartTop + plotHeight;
    const double groupWidth = 150;
    const double barWidth = 18;
    const double barGap = 7;
    const double groupGap = 30;
    var chartWidth = (int)Math.Max(760, left * 2 + phases.Length * groupWidth + Math.Max(0, phases.Length - 1) * groupGap);
    var chart = new SvgChartBuilder(
        chartWidth,
        420,
        title,
        subtitle);

    var legendX = left;
    for (var c = 0; c < engines.Length; c++)
    {
      var x = legendX + c * 150;
      chart.Rect(x, SvgChartBuilder.ContentTop - 11, 14, 14, chart.ColorFor(engines[c]), 3);
      chart.Text(x + 22, SvgChartBuilder.ContentTop + 1, engines[c], 13, "#111827", weight: "700");
    }

    chart.Line(left, baseline, chartWidth - left, baseline, "#d1d5db", 1);
    chart.Line(left, chartTop + plotHeight * 0.5, chartWidth - left, chartTop + plotHeight * 0.5, "#f3f4f6", 1);
    chart.Text(chartWidth - left, chartTop + plotHeight * 0.5 - 6, "50%", 11, "#9ca3af", "end");
    chart.Text(chartWidth - left, chartTop - 6, "100%", 11, "#9ca3af", "end");

    for (var r = 0; r < phases.Length; r++)
    {
      var phase = phases[r];
      var row = results
          .Select(result => new
          {
            result.Engine,
            Phase = result.Points.FirstOrDefault(p => p.Name == phase)
          })
          .ToArray();
      var max = Math.Max(1, row.Max(x => x.Phase?.OperationsPerSecond ?? 0));
      var groupX = left + r * (groupWidth + groupGap);
      var barsWidth = engines.Length * barWidth + Math.Max(0, engines.Length - 1) * barGap;
      var barsX = groupX + (groupWidth - barsWidth) / 2;

      for (var c = 0; c < engines.Length; c++)
      {
        var item = row.First(x => x.Engine == engines[c]);
        var x = barsX + c * (barWidth + barGap);
        if (item.Phase == null)
          continue;

        var ratio = item.Phase.OperationsPerSecond / max;
        var color = chart.ColorFor(item.Engine);
        var barHeight = Math.Max(3, plotHeight * ratio);
        chart.Rect(x, baseline - barHeight, barWidth, barHeight, color, 4);
        chart.Text(x + barWidth / 2, baseline - barHeight - 7, $"{(ratio * 100).ToString("0", CultureInfo.InvariantCulture)}%", 10, "#374151", "middle", "700");
      }

      chart.Text(groupX + groupWidth / 2, baseline + 34, ShortPhaseName(phase), 13, "#374151", "middle", "700");
    }

    return chart.Build();
  }

  static string CreateResources(IReadOnlyList<BenchmarkResult> results)
  {
    var chart = new SvgChartBuilder(1360, 462, "Resource Footprint", $"Lower is better for both dimensions{FormatParallelism(results)}");
    DrawResourceBars(
        chart,
        "Storage",
        results.Where(r => r.StorageSizeBytes.HasValue)
            .Select(r => (r.Engine, Value: (double)r.StorageSizeBytes!.Value, Display: ResultWriter.FormatBytes(r.StorageSizeBytes.Value)))
            .OrderBy(x => x.Value)
            .ToArray(),
        SvgChartBuilder.MarginLeft,
        150);

    DrawResourceBars(
        chart,
        "Process peak memory",
        results.Where(r => r.PeakProcessWorkingSetBytes.HasValue)
            .Select(r => (r.Engine, Value: (double)r.PeakProcessWorkingSetBytes!.Value, Display: ResultWriter.FormatBytes(r.PeakProcessWorkingSetBytes.Value)))
            .OrderBy(x => x.Value)
            .ToArray(),
        SvgChartBuilder.MarginLeft,
        320);

    chart.Text(980, 122, "Measurement scope", 12, "#6b7280", weight: "700");
    chart.Text(980, 150, "MySQL memory is the .NET client only.", 13, "#374151");
    chart.Text(980, 174, "Embedded engines include native memory.", 13, "#374151");
    chart.Text(980, 198, "Storage is measured after settle/checkpoint.", 13, "#374151");
    return chart.Build();
  }

  static void DrawResourceBars(
      SvgChartBuilder chart,
      string title,
      IReadOnlyList<(string Engine, double Value, string Display)> data,
      double x,
      double y)
  {
    chart.Text(x, y - 28, title, 17, "#111827", weight: "800");
    const double barWidth = 520;
    var max = Math.Max(1, data.Count == 0 ? 1 : data.Max(d => d.Value));
    for (var i = 0; i < data.Count; i++)
    {
      var item = data[i];
      var rowY = y + i * 31;
      var width = barWidth * item.Value / max;
      chart.Text(x, rowY + 14, item.Engine, 13, "#111827", weight: "700");
      chart.Rect(x + 132, rowY, barWidth, 20, "#f3f4f6", 10);
      chart.Rect(x + 132, rowY, Math.Max(4, width), 20, chart.ColorFor(item.Engine), 10);
      chart.Text(x + 680, rowY + 14, item.Display, 12, "#374151", weight: "700");
    }
  }

  static string ShortPhaseName(string phase) =>
      phase switch
      {
        "insert" => "insert",
        "insert + stabilize" => "insert + stabilize",
        "update" => "update",
        "update + stabilize" => "update + stabilize",
        "read by user id" => "read user id",
        "lookup by email" => "email lookup",
        "scan country/status index" => "country/status",
        "scan created-at index" => "created-at range",
        "scan top reputation index" => "top reputation",
        "query country/status" => "country/status",
        "query created-at range" => "created-at range",
        "query top reputation" => "top reputation",
        "post-update read by user id" => "post read id",
        "post-update lookup by email" => "post email",
        "post-update scan country/status index" => "post country/status",
        "post-update scan top reputation index" => "post reputation",
        "post-update query country/status" => "post country/status",
        "post-update query top reputation" => "post reputation",
        _ => phase
      };

  static string FormatMs(double value) =>
      $"{FormatCount(value)} ms";

  static string FormatCount(double value) =>
      FormatCount((long)Math.Round(value, MidpointRounding.AwayFromZero));

  static string FormatCount(long value) =>
      value.ToString("N0", CultureInfo.InvariantCulture).Replace(",", "_");

  static string FormatParallelism(IReadOnlyList<BenchmarkResult> results)
  {
    var parallelism = results[0].Workload.Parallelism;
    if (parallelism <= 0)
      parallelism = 1;
    return parallelism > 1 ? $" at P{parallelism.ToString(CultureInfo.InvariantCulture)}" : "";
  }

  sealed record ThroughputDataPoint(string Name, double OperationsPerSecond);
}
