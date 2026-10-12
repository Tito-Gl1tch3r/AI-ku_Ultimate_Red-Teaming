using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace Swarmer
{
    class Program
    {
        static void Main(string[] args)
        {
            // Process flags
            List<string> processedArgs = new List<string>();
            bool useBofParser = false;
            string startupKeyName = null;
            string startupKeyValue = null;
            
            for (int i = 0; i < args.Length; i++)
            {
                string arg = args[i];
                if (arg == "--bof")
                {
                    useBofParser = true;
                }
                else if (arg == "--startup-key" && i + 1 < args.Length)
                {
                    startupKeyName = args[i + 1];
                    i++; // Skip the next argument since we've consumed it
                }
                else if (arg == "--startup-value" && i + 1 < args.Length)
                {
                    startupKeyValue = args[i + 1];
                    i++; // Skip the next argument since we've consumed it
                }
                else
                {
                    processedArgs.Add(arg);
                }
            }

            if (processedArgs.Count != 2)
            {
                Console.WriteLine("Usage: swarmer.exe [options] <input_file> <output.hive>");
                Console.WriteLine("Options:");
                Console.WriteLine("  --bof               Parse input file as BOF registry output format");
                Console.WriteLine("  --startup-key KEY   Add a startup entry with the specified KEY name");
                Console.WriteLine("  --startup-value VAL Value for the startup entry (path to executable)");
                Console.WriteLine("");
                Console.WriteLine("Examples:");
                Console.WriteLine("  swarmer.exe exported.reg NTUSER.MAN");
                Console.WriteLine("  swarmer.exe --bof reg_dump.txt NTUSER.MAN");
                Console.WriteLine("  swarmer.exe --startup-key \"My Program\" --startup-value \"C:\\Program Files\\MyApp\\app.exe\" exported.reg NTUSER.MAN");
                return;
            }

            string inputFilePath = processedArgs[0];
            string hiveFilePath = processedArgs[1];

            if (!File.Exists(inputFilePath))
            {
                Console.WriteLine($"Error: Input file '{inputFilePath}' not found.");
                return;
            }

            try
            {
                RegistryKeyInfo rootKey;
                
                if (useBofParser)
                {
                    // Parse the BOF registry output file
                    Console.WriteLine("Parsing BOF registry output...");
                    BofParser parser = new BofParser();
                    rootKey = parser.ParseBofOutput(inputFilePath);
                }
                else
                {
                    // Parse the .reg file
                    Console.WriteLine("Parsing .reg file...");
                    RegistryParser parser = new RegistryParser();
                    rootKey = parser.ParseRegFile(inputFilePath);
                }

                // Validate startup parameters - both must be specified if one is
                if ((!string.IsNullOrEmpty(startupKeyName) && string.IsNullOrEmpty(startupKeyValue)) ||
                    (string.IsNullOrEmpty(startupKeyName) && !string.IsNullOrEmpty(startupKeyValue)))
                {
                    throw new ArgumentException("Both --startup-key and --startup-value must be specified when using startup functionality");
                }

                // Add startup entry if requested
                if (!string.IsNullOrEmpty(startupKeyName) && !string.IsNullOrEmpty(startupKeyValue))
                {
                    Console.WriteLine($"Adding startup entry: {startupKeyName} -> {startupKeyValue}");
                    AddStartupEntry(rootKey, startupKeyName, startupKeyValue);
                }

                // Create and populate the hive
                Console.WriteLine("Creating registry hive...");
                HiveWriter writer = new HiveWriter();
                bool success = writer.CreateAndPopulateHive(rootKey, hiveFilePath);

                if (success)
                {
                    Console.WriteLine("Operation completed successfully.");
                }
                else
                {
                    Console.WriteLine("Operation failed.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
            }
        }

        private static void AddStartupEntry(RegistryKeyInfo rootKey, string keyName, string keyValue)
        {
            // Path to the Run key
            string[] runKeyPath = { "SOFTWARE", "Microsoft", "Windows", "CurrentVersion", "Run" };
            
            // Get or create the Run key
            RegistryKeyInfo currentKey = rootKey;
            foreach (string part in runKeyPath)
            {
                // Find the subkey
                RegistryKeyInfo subKey = currentKey.Subkeys.Find(k => k.Name.Equals(part, StringComparison.OrdinalIgnoreCase));
                
                // If it doesn't exist, create it
                if (subKey == null)
                {
                    subKey = new RegistryKeyInfo
                    {
                        Name = part,
                        Values = new List<RegistryValueInfo>(),
                        Subkeys = new List<RegistryKeyInfo>()
                    };
                    currentKey.Subkeys.Add(subKey);
                }
                
                currentKey = subKey;
            }
            
            // Create the REG_SZ value with null terminator
            string valueWithNull = keyValue + '\0';
            byte[] data = Encoding.Unicode.GetBytes(valueWithNull);
            
            // Remove any existing value with the same name
            currentKey.Values.RemoveAll(v => v.Name.Equals(keyName, StringComparison.OrdinalIgnoreCase));
            
            // Add the startup entry
            currentKey.Values.Add(new RegistryValueInfo
            {
                Name = keyName,
                Type = API.REG_SZ,
                Data = data
            });
        }
    }
} 