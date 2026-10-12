using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using SubdomainScanner.Core;

namespace SubdomainScanner.Sources
{
    /// <summary>
    /// Source using crt.sh (Certificate Transparency Logs)
    /// </summary>
    public class CrtShSource : BaseSubdomainSource
    {
        public override string Name => "crt.sh";

        public CrtShSource(HttpClient httpClient) : base(httpClient)
        {
        }

        public override async Task<HashSet<string>> SearchAsync(string domain)
        {
            LogInfo("Searching via Certificate Transparency...");
            var results = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            try
            {
                // Wildcard search
                var url1 = $"https://crt.sh/?q=%.{domain}&output=json";
                var response1 = await HttpClient.GetStringAsync(url1);

                var matches = Regex.Matches(response1, @"""name_value"":""([^""]+)""");
                var foundDomains = new List<string>();

                foreach (Match match in matches)
                {
                    foundDomains.Add(match.Groups[1].Value);
                }

                results.UnionWith(CleanSubdomains(foundDomains, domain));

                // Direct search
                var url2 = $"https://crt.sh/?q={domain}&output=json";
                var response2 = await HttpClient.GetStringAsync(url2);

                matches = Regex.Matches(response2, @"""common_name"":""([^""]+)""");
                foundDomains.Clear();

                foreach (Match match in matches)
                {
                    foundDomains.Add(match.Groups[1].Value);
                }

                results.UnionWith(CleanSubdomains(foundDomains, domain));

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
