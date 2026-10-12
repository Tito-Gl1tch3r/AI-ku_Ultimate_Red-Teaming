using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace SubdomainScanner.Core
{
    /// <summary>
    /// Abstract base class for all subdomain sources
    /// </summary>
    public abstract class BaseSubdomainSource : ISubdomainSource
    {
        protected readonly HttpClient HttpClient;

        public abstract string Name { get; }
        public bool IsEnabled { get; set; } = true;

        protected BaseSubdomainSource(HttpClient httpClient)
        {
            HttpClient = httpClient;
        }

        public abstract Task<HashSet<string>> SearchAsync(string domain);

        /// <summary>
        /// Cleans and validates subdomains
        /// </summary>
        protected HashSet<string> CleanSubdomains(IEnumerable<string> subdomains, string targetDomain)
        {
            var cleaned = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            foreach (var subdomain in subdomains)
            {
                if (string.IsNullOrWhiteSpace(subdomain))
                    continue;

                var processed = subdomain.ToLower().Trim();

                // Replace literal escape sequences
                processed = processed.Replace("\\n", "\n")
                                   .Replace("\\r", "\r")
                                   .Replace("\\t", "\t");

                // Split multiple entries
                var parts = processed.Split(new[] { ' ', '\r', '\n', '\t' },
                                          StringSplitOptions.RemoveEmptyEntries);

                foreach (var part in parts)
                {
                    var clean = part.Trim();

                    // Validation
                    if (!string.IsNullOrWhiteSpace(clean) &&
                        clean.EndsWith(targetDomain) &&
                        !clean.StartsWith("*") &&
                        !clean.Contains("@") &&
                        clean.Contains(".") &&
                        IsValidDomain(clean))
                    {
                        cleaned.Add(clean);
                    }
                }
            }

            return cleaned;
        }

        /// <summary>
        /// Validates domain format
        /// </summary>
        protected bool IsValidDomain(string domain)
        {
            if (string.IsNullOrWhiteSpace(domain))
                return false;

            // Basic pattern to validate a domain
            var pattern = @"^[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,}$";
            return Regex.IsMatch(domain, pattern);
        }

        /// <summary>
        /// Logs an error (can be overridden)
        /// </summary>
        protected virtual void LogError(Exception ex)
        {
            Console.WriteLine($"    Error {Name}: {ex.Message}");
        }

        /// <summary>
        /// Logs information (can be overridden)
        /// </summary>
        protected virtual void LogInfo(string message)
        {
            Console.WriteLine($"[+] {Name}: {message}");
        }
    }
}
