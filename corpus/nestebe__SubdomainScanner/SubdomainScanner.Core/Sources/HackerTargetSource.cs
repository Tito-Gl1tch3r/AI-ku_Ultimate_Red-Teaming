using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using SubdomainScanner.Core;

namespace SubdomainScanner.Sources
{
    /// <summary>
    /// Source using HackerTarget API
    /// </summary>
    public class HackerTargetSource : BaseSubdomainSource
    {
        public override string Name => "HackerTarget";

        public HackerTargetSource(HttpClient httpClient) : base(httpClient)
        {
        }

        public override async Task<HashSet<string>> SearchAsync(string domain)
        {
            LogInfo("Searching via API...");
            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            try
            {
                var url = $"https://api.hackertarget.com/hostsearch/?q={domain}";
                var response = await HttpClient.GetStringAsync(url);

                var lines = response.Split('\n');
                var foundDomains = new List<string>();

                foreach (var line in lines)
                {
                    if (line.Contains(","))
                    {
                        var subdomain = line.Split(',')[0].Trim();
                        foundDomains.Add(subdomain);
                    }
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
