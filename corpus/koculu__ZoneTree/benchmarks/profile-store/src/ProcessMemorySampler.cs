using System.Diagnostics;

namespace ProfileStore.Benchmark;

public sealed class ProcessMemorySampler : IAsyncDisposable
{
  readonly Process Process = Process.GetCurrentProcess();
  readonly CancellationTokenSource Cancellation = new();
  readonly Task SamplingTask;
  int Stopped;

  ProcessMemorySampler(TimeSpan interval)
  {
    Process.Refresh();
    InitialWorkingSetBytes = Process.WorkingSet64;
    PeakWorkingSetBytes = InitialWorkingSetBytes;
    SamplingTask = Task.Run(() => SampleLoopAsync(interval));
  }

  public long InitialWorkingSetBytes { get; }

  public long PeakWorkingSetBytes { get; private set; }

  public static ProcessMemorySampler Start() =>
      new(TimeSpan.FromMilliseconds(100));

  public async Task StopAsync()
  {
    if (Interlocked.Exchange(ref Stopped, 1) != 0)
      return;

    await Cancellation.CancelAsync();
    try
    {
      await SamplingTask;
    }
    catch (OperationCanceledException)
    {
    }
    Sample();
    Process.Refresh();
    PeakWorkingSetBytes = Math.Max(PeakWorkingSetBytes, Process.PeakWorkingSet64);
  }

  async Task SampleLoopAsync(TimeSpan interval)
  {
    using var timer = new PeriodicTimer(interval);
    while (await timer.WaitForNextTickAsync(Cancellation.Token))
      Sample();
  }

  void Sample()
  {
    Process.Refresh();
    PeakWorkingSetBytes = Math.Max(PeakWorkingSetBytes, Process.WorkingSet64);
  }

  public async ValueTask DisposeAsync()
  {
    await StopAsync();
    Cancellation.Dispose();
    Process.Dispose();
  }
}
