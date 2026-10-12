using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using SubdomainScanner.Core;

namespace SubdomainScanner.Sources
{
    /// <summary>
    /// Source using ThreatCrowd API
    /// </summary>
    public class ThreatCrowdSource : BaseSubdomainSource
    {
        public override string Name => "ThreatCrowd";

        public ThreatCrowdSource(HttpClient httpClient) : base(httpClient)
        {
        }

        public override async Task<HashSet<string>> SearchAsync(string domain)
        {
            LogInfo("Searching via API...");
            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            try
            {
                var url = $"https://www.threatcrowd.org/searchApi/v2/domain/report/?domain={domain}";
                var response = await HttpClient.GetStringAsync(url);

                // Extract subdomains from JSON
                var pattern = @"""([a-z0-9\-\.]+\." + Regex.Escape(domain) + @")""";
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
