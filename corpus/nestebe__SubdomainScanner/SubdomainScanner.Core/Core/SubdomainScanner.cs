using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;

namespace SubdomainScanner.Core
{
    /// <summary>
    /// Main manager for subdomain discovery
    /// </summary>
    public class SubdomainScanner : IDisposable
    {
        private readonly string _domain;
        private readonly List<ISubdomainSource> _sources;
        private readonly HttpClient _httpClient;
        private readonly HashSet<string> _allSubdomains;

        public SubdomainScanner(string domain)
        {
            _domain = domain.ToLower().Trim();
            _sources = new List<ISubdomainSource>();
            _allSubdomains = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            // HttpClient configuration
            _httpClient = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(30)
            };
            _httpClient.DefaultRequestHeaders.Add("User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SubdomainScanner/2.0");
        }

        /// <summary>
        /// Adds a search source
        /// </summary>
        public void AddSource(ISubdomainSource source)
        {
            _sources.Add(source);
        }

        /// <summary>
        /// Gets the shared HttpClient
        /// </summary>
        public HttpClient GetHttpClient() => _httpClient;

        /// <summary>
        /// Launches the search on all enabled sources
        /// </summary>
        public async Task<List<string>> ScanAsync()
        {
            Console.WriteLine($"[*] Searching subdomains for: {_domain}");
            Console.WriteLine($"[*] Active sources: {_sources.Count(s => s.IsEnabled)}");
            Console.WriteLine();

            var tasks = _sources
                .Where(s => s.IsEnabled)
                .Select(async source =>
                {
                    var results = await source.SearchAsync(_domain);
                    lock (_allSubdomains)
                    {
                        _allSubdomains.UnionWith(results);
                    }
                });

            await Task.WhenAll(tasks);

            Console.WriteLine();
            Console.WriteLine($"[*] Total unique subdomains: {_allSubdomains.Count}");

            return _allSubdomains.OrderBy(s => s).ToList();
        }

        /// <summary>
        /// Resolves IP addresses for subdomains
        /// </summary>
        public async Task<Dictionary<string, string>> ResolveAsync(List<string> subdomains)
        {
            Console.WriteLine();
            Console.WriteLine("[*] DNS resolution of subdomains...");

            var results = new Dictionary<string, string>();
            var tasks = subdomains.Select(async subdomain =>
            {
                try
                {
                    var addresses = await Dns.GetHostAddressesAsync(subdomain);
                    if (addresses.Length > 0)
                    {
                        var ip = addresses[0].ToString();
                        lock (results)
                        {
                            results[subdomain] = ip;
                        }
                        Console.WriteLine($"    {subdomain} -> {ip}");
                    }
                }
                catch
                {
                    // Ignore resolution errors
                }
            });

            await Task.WhenAll(tasks);
            return results;
        }

        public void Dispose()
        {
            _httpClient?.Dispose();
        }
    }
}
