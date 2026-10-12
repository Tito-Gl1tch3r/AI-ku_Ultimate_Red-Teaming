using SubdomainScanner.Core;
using SubdomainScanner.Sources;
using System.Collections.Concurrent;

namespace SubdomainScanner.Blazor.Services
{
    public class ScannerService
    {
        private readonly IHttpClientFactory _httpClientFactory;

        public event Action<string>? OnLog;
        public event Action<List<string>>? OnScanCompleted;

        public ScannerService(IHttpClientFactory httpClientFactory)
        {
            _httpClientFactory = httpClientFactory;
        }

        public async Task<ScanResult> ScanAsync(ScanConfiguration config, CancellationToken cancellationToken = default)
        {
            var result = new ScanResult();
            var logs = new ConcurrentBag<string>();
            Core.SubdomainScanner? scanner = null;

            try
            {
                // Do NOT use 'using' with HttpClient from IHttpClientFactory
                // The factory manages the lifecycle - disposing it causes issues
                var httpClient = _httpClientFactory.CreateClient();
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

                // Check for cancellation before starting scan
                cancellationToken.ThrowIfCancellationRequested();

                // Scan
                result.Subdomains = await scanner.ScanAsync();

                // Check for cancellation after scan
                cancellationToken.ThrowIfCancellationRequested();

                result.TotalFound = result.Subdomains.Count;

                Log($"Found {result.TotalFound} unique subdomains");

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
                OnScanCompleted?.Invoke(result.Subdomains);
            }
            catch (OperationCanceledException)
            {
                result.IsSuccess = false;
                result.ErrorMessage = "Scan cancelled by user";
                Log("Scan cancelled");
            }
            catch (Exception ex)
            {
                result.IsSuccess = false;
                result.ErrorMessage = ex.Message;
                Log($"Error: {ex.Message}");
            }
            finally
            {
                // Dispose scanner immediately
                try
                {
                    scanner?.Dispose();
                }
                catch
                {
                    // Ignore disposal errors
                }

                // Note: In Blazor, we typically don't dispose HttpClient from IHttpClientFactory
                // as it's managed by the framework. However, since we're creating new instances
                // in our factory, we should dispose them to avoid memory leaks.
                // For cancelled operations, we give a delay to avoid errors.
            }

            result.Logs = logs.ToList();
            return result;
        }

        private void Log(string message)
        {
            OnLog?.Invoke(message);
        }
    }

    public class ScanConfiguration
    {
        public string Domain { get; set; } = string.Empty;
        public List<string> EnabledSources { get; set; } = new();
        public bool ResolveDns { get; set; }
    }

    public class ScanResult
    {
        public bool IsSuccess { get; set; }
        public string? ErrorMessage { get; set; }
        public List<string> Subdomains { get; set; } = new();
        public Dictionary<string, string> ResolvedDomains { get; set; } = new();
        public int TotalFound { get; set; }
        public List<string> Logs { get; set; } = new();
    }
}
