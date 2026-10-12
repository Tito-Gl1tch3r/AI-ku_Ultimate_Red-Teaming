using System;
using System.Collections.Generic;
using System.IO;

namespace SubdomainScanner.Utils
{
    /// <summary>
    /// Utility for exporting results
    /// </summary>
    public static class FileExporter
    {
        /// <summary>
        /// Exports a list of subdomains to a text file
        /// </summary>
        public static void ExportToText(List<string> subdomains, string filePath)
        {
            try
            {
                File.WriteAllLines(filePath, subdomains);
                Console.WriteLine($"[+] Results exported: {filePath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[!] Error during export: {ex.Message}");
            }
        }

        /// <summary>
        /// Exports subdomains with their IPs to CSV
        /// </summary>
        public static void ExportToCsv(Dictionary<string, string> subdomainsWithIp, string filePath)
        {
            try
            {
                var lines = new List<string> { "Subdomain,IP Address" };
                foreach (var kvp in subdomainsWithIp)
                {
                    lines.Add($"{kvp.Key},{kvp.Value}");
                }

                File.WriteAllLines(filePath, lines);
                Console.WriteLine($"[+] Results exported to CSV: {filePath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[!] Error during CSV export: {ex.Message}");
            }
        }

        /// <summary>
        /// Exports to JSON
        /// </summary>
        public static void ExportToJson(List<string> subdomains, string filePath)
        {
            try
            {
                var json = System.Text.Json.JsonSerializer.Serialize(new
                {
                    timestamp = DateTime.UtcNow,
                    total = subdomains.Count,
                    subdomains = subdomains
                }, new System.Text.Json.JsonSerializerOptions
                {
                    WriteIndented = true
                });

                File.WriteAllText(filePath, json);
                Console.WriteLine($"[+] Results exported to JSON: {filePath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[!] Error during JSON export: {ex.Message}");
            }
        }
    }
}
