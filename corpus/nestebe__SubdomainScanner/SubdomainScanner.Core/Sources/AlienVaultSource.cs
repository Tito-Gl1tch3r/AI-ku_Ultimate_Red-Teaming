using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using SubdomainScanner.Core;

namespace SubdomainScanner.Sources
{
    /// <summary>
    /// Source using AlienVault OTX (Open Threat Exchange)
    /// </summary>
    public class AlienVaultSource : BaseSubdomainSource
    {
        public override string Name => "AlienVault OTX";

        public AlienVaultSource(HttpClient httpClient) : base(httpClient)
        {
        }

        public override async Task<HashSet<string>> SearchAsync(string domain)
        {
            LogInfo("Searching via Open Threat Exchange...");
            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            try
            {
                var url = $"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns";
                var response = await HttpClient.GetStringAsync(url);

                // Extract hostnames from JSON
                var pattern = @"""hostname"":""([^""]+)""";
                var matches = Regex.Matches(response, pattern);

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
