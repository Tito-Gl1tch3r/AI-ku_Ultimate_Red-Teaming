using SubdomainScanner.Core;
using SubdomainScanner.Sources;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace SubdomainScanner.Avalonia.Services;

public class ScannerService
{
    private readonly IHttpClientFactory _httpClientFactory;

    public event Action<string>? OnLog;
    public event Action<ScanProgress>? OnProgress;

    public ScannerService(IHttpClientFactory httpClientFactory)
    {
        _httpClientFactory = httpClientFactory;
    }

    public async Task<ScanResult> ScanAsync(ScanConfiguration config, CancellationToken cancellationToken = default)
    {
        var result = new ScanResult();
        var logs = new List<string>();
        HttpClient? httpClient = null;
        Core.SubdomainScanner? scanner = null;
        bool wasCancelled = false;

        try
        {
            httpClient = _httpClientFactory.CreateClient();
            httpClient.Timeout = TimeSpan.FromSeconds(30);
            httpClient.DefaultRequestHeaders.Add("User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SubdomainScanner/2.0");

            scanner = new Core.SubdomainScanner(config.Domain);

            // Create sources
            var sources = new List<ISubdomainSource>();

            if (config.EnabledSources.Contains("crt.sh"))
                sources.Add(new CrtShSource(httpClient));
            if (config.EnabledSources.Contains("hackertarget"))
                sources.Add(new HackerTargetSource(httpClient));
            if (config.EnabledSources.Contains("wayback"))
                sources.Add(new WaybackMachineSource(httpClient));
            if (config.EnabledSources.Contains("alienvault"))
                sources.Add(new AlienVaultSource(httpClient));
            if (config.EnabledSources.Contains("threatcrowd"))
                sources.Add(new ThreatCrowdSource(httpClient));
            if (config.EnabledSources.Contains("commoncrawl"))
                sources.Add(new CommonCrawlSource(httpClient));

            foreach (var source in sources)
            {
                scanner.AddSource(source);
            }

            Log($"Starting scan for domain: {config.Domain}");
            Log($"Active sources: {sources.Count}");
            ReportProgress(0, sources.Count, "Initializing scan...");

            // Check for cancellation before starting scan
            cancellationToken.ThrowIfCancellationRequested();

            // Scan
            result.Subdomains = await scanner.ScanAsync();

            // Check for cancellation after scan
            cancellationToken.ThrowIfCancellationRequested();

            result.TotalFound = result.Subdomains.Count;

            Log($"Found {result.TotalFound} unique subdomains");
            ReportProgress(sources.Count, sources.Count, $"Found {result.TotalFound} subdomains");

            // DNS Resolution if enabled
            if (config.ResolveDns && result.Subdomains.Any())
            {
                // Check for cancellation before DNS resolution
                cancellationToken.ThrowIfCancellationRequested();

                Log("Starting DNS resolution...");
                result.ResolvedDomains = await scanner.ResolveAsync(result.Subdomains);
                Log($"Resolved {result.ResolvedDomains.Count} subdomains");
            }

            result.IsSuccess = true;
        }
        catch (OperationCanceledException)
        {
            wasCancelled = true;
            result.IsSuccess = false;
            result.ErrorMessage = "Scan cancelled by user";
            Log("Scan cancelled");
        }
        catch (ObjectDisposedException)
        {
            wasCancelled = true;
            result.IsSuccess = false;
            result.ErrorMessage = "Scan cancelled";
            Log("Scan cancelled");
        }
        catch (HttpRequestException ex)
        {
            result.IsSuccess = false;
            result.ErrorMessage = $"Network error: {ex.Message}";
            Log($"Network error: {ex.Message}");
        }
        catch (Exception ex)
        {
            result.IsSuccess = false;
            result.ErrorMessage = ex.Message;
            Log($"Error: {ex.Message}");
        }
        finally
        {
            // Dispose scanner immediately - it doesn't make HTTP requests
            try
            {
                scanner?.Dispose();
            }
            catch
            {
                // Ignore scanner disposal errors
            }

            // Handle HttpClient disposal based on cancellation status
            if (httpClient != null)
            {
                if (wasCancelled)
                {
                    // If cancelled, background HTTP requests may still be running
                    // Dispose HttpClient asynchronously after a delay to avoid ObjectDisposedException
                    // This prevents memory leaks while allowing ongoing requests to complete gracefully
                    var clientToDispose = httpClient;
                    _ = Task.Run(async () =>
                    {
                        try
                        {
                            // Wait 5 seconds for ongoing requests to complete or fail
                            // This is a balance between cleanup speed and avoiding errors
                            await Task.Delay(5000, CancellationToken.None);
                            clientToDispose.Dispose();
                        }
                        catch
                        {
                            // Ignore disposal errors - requests may have already completed
                        }
                    });

                    Log("Background cleanup scheduled (5s delay)");
                }
                else
                {
                    // Normal completion - dispose immediately
                    try
                    {
                        httpClient.Dispose();
                    }
                    catch
                    {
                        // Ignore disposal errors
                    }
                }
            }
        }

        return result;
    }

    private void Log(string message)
    {
        OnLog?.Invoke(message);
    }

    private void ReportProgress(int current, int total, string message)
    {
        OnProgress?.Invoke(new ScanProgress(current, total, message));
    }
}

public record ScanConfiguration(
    string Domain,
    List<string> EnabledSources,
    bool ResolveDns);

public record ScanResult
{
    public bool IsSuccess { get; set; }
    public string? ErrorMessage { get; set; }
    public List<string> Subdomains { get; set; } = new();
    public Dictionary<string, string> ResolvedDomains { get; set; } = new();
    public int TotalFound { get; set; }
}

public record ScanProgress(int Current, int Total, string Message)
{
    public double Percentage => Total > 0 ? (double)Current / Total * 100 : 0;
}
