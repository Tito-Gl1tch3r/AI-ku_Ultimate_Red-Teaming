using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using SubdomainScanner.Core;

namespace SubdomainScanner.Sources
{
    /// <summary>
    /// Source using Wayback Machine (Internet Archive)
    /// </summary>
    public class WaybackMachineSource : BaseSubdomainSource
    {
        public override string Name => "Wayback Machine";

        public WaybackMachineSource(HttpClient httpClient) : base(httpClient)
        {
        }

        public override async Task<HashSet<string>> SearchAsync(string domain)
        {
            LogInfo("Searching via Internet Archive...");
            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            try
            {
                // Wayback Machine CDX API
                var url = $"https://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&fl=original&collapse=urlkey";
                var response = await HttpClient.GetStringAsync(url);

                // Extract domains from URLs
                var pattern = $@"https?://([a-z0-9\-\.]+\.{Regex.Escape(domain)})";
                var matches = Regex.Matches(response, pattern, RegexOptions.IgnoreCase);

                var foundDomains = new List<string>();
                foreach (Match match in matches)
                {
                    foundDomains.Add(match.Groups[1].Value);
                }

                results = CleanSubdomains(foundDomains, domain);
                LogInfo($"Found {results.Count} subdomains");
            }
            catch (Exception ex)
            {
                LogError(ex);
            }

            return results;
        }
    }
}
