using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using SubdomainScanner.Core;

namespace SubdomainScanner.Sources
{
    /// <summary>
    /// Source using CommonCrawl Index
    /// </summary>
    public class CommonCrawlSource : BaseSubdomainSource
    {
        public override string Name => "CommonCrawl";

        public CommonCrawlSource(HttpClient httpClient) : base(httpClient)
        {
        }

        public override async Task<HashSet<string>> SearchAsync(string domain)
        {
            LogInfo("Searching via Index...");
            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            try
            {
                // Use CommonCrawl Index API
                var url = $"https://index.commoncrawl.org/CC-MAIN-2024-10-index?url=*.{domain}&output=json";
                var response = await HttpClient.GetStringAsync(url);

                // Extract URLs and domains
                var pattern = $@"""url"":""https?://([a-z0-9\-\.]+\.{Regex.Escape(domain)})";
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
