using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

namespace Swarmer
{
    public class BofParser
    {
        // Pattern to identify the start of registry key blocks (now without newlines)
        //private const string KEY_BLOCK_PATTERN_STR = @"[\d ]{2,3}/[\d ]{2,3}/[\d ]{4,5} [\d ]{2.3}:[\d ]{2,3}:[\d ]{2,3} +[H ]{1,2}[K ]{1,2}[E ]{1,2}[Y ]{1,2}[_ ]{1,2}[C ]{1,2}[U ]{1,2}[R ]{1,2}[E ]{1,2}[N ]{1,2}[T ]{1,2}[_ ]{1,2}[U ]{1,2}[S ]{1,2}[E ]{1,2}[R ]{1,2}[\\ ]{1,2}";
        private const string KEY_BLOCK_PATTERN_STR = @"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} +HKEY_CURRENT_USER\\";
        private static readonly Regex KEY_BLOCK_REGEX = new Regex(KEY_BLOCK_PATTERN_STR, RegexOptions.Compiled);
        
        // Pattern to identify registry subkey entries (adjusted for no newlines)
        private const string SUBKEY_PATTERN_STR = @"\t[^\t]*?REG_[A-Z_]+";
        private static readonly Regex SUBKEY_REGEX = new Regex(SUBKEY_PATTERN_STR, RegexOptions.Compiled);
        
        // Pattern for registry types
        private static readonly Regex REG_TYPE_REGEX = new Regex(@"REG_[A-Z_]+", RegexOptions.Compiled);

        private const string KEY_PREFIX = "HKEY_CURRENT_USER\\";
        
        public BofParser()
        {
        }

        public RegistryKeyInfo ParseBofOutput(string filePath)
        {
            // Read the file and normalize by removing all newlines
            string fileContent = File.ReadAllText(filePath);
            fileContent = NormalizeContent(fileContent);
            
            // Create a root key to represent HKCU
            RegistryKeyInfo rootKey = new RegistryKeyInfo
            {
                Name = "HKEY_CURRENT_USER",
                Values = new List<RegistryValueInfo>(),
                Subkeys = new List<RegistryKeyInfo>()
            };

            // Step 1: Split the file into registry key blocks
            List<string> keyBlocks = SplitIntoKeyBlocks(fileContent);
            
            // Step 2: Process each key block
            foreach (string keyBlock in keyBlocks)
            {
                ProcessKeyBlock(keyBlock, rootKey);
            }

            return rootKey;
        }

        private string NormalizeContent(string content)
        {
            string normalized = Regex.Replace(content, @"\r\n|\n|\r", "");            
            return normalized;
        }

        private List<string> SplitIntoKeyBlocks(string content)
        {
            List<string> keyBlocks = new List<string>();
            
            // Find all matches of the key block pattern
            MatchCollection matches = KEY_BLOCK_REGEX.Matches(content);

            Console.WriteLine($"Found {matches.Count} key blocks");
            
            // If no matches found, return empty list
            if (matches.Count == 0)
                return keyBlocks;
            
            // Process each match
            for (int i = 0; i < matches.Count; i++)
            {
                int startIndex = matches[i].Index;
                int endIndex;
                
                // If this is the last match, the end is the end of the content
                if (i == matches.Count - 1)
                {
                    endIndex = content.Length;
                }
                else
                {
                    endIndex = matches[i + 1].Index;
                }
                
                // Extract the block
                string block = content.Substring(startIndex, endIndex - startIndex);
                keyBlocks.Add(block);
            }
            
            return keyBlocks;
        }

        private void ProcessKeyBlock(string keyBlock, RegistryKeyInfo rootKey)
        {
            // Extract the registry key path
            Match keyMatch = KEY_BLOCK_REGEX.Match(keyBlock);
            if (!keyMatch.Success)
                return;
                
            // Find the start of the key path (after timestamp)
            int keyPrefixIndex = keyMatch.Length;
            if (keyPrefixIndex < 0)
            {
                Console.WriteLine($"Key prefix index is less than 0: {keyBlock}");
                return;
            }
                
            // Extract the key path and create the key
            string fullKeyPath = keyBlock.Substring(keyPrefixIndex);
            string relativePath = "";
            
            // Find end of key path (first tab or end of string)
            int endOfPath = fullKeyPath.IndexOf('\t');
            if (endOfPath == -1) {
                endOfPath = fullKeyPath.Length;
            }
            if (endOfPath > 0)
            {
                relativePath = fullKeyPath.Substring(0, endOfPath);
            } 

            // Special case for the root key
            if (relativePath == "") {
                return;
            }

            if (relativePath.Split('\\').Length == 1) {
                return;
            }

            // Create the key in our structure
            RegistryKeyInfo currentKey = GetOrCreateKeyPath(rootKey, relativePath.Split('\\'));
            

            string subKeyBlock = fullKeyPath.Substring(fullKeyPath.IndexOf(relativePath) + relativePath.Length);
            // Step 3: Split the key block into subkey entries
            List<string> subKeyEntries = SplitIntoSubkeyEntries(subKeyBlock);
            
            // Step 4: Process each subkey entry
            foreach (string subKeyEntry in subKeyEntries)
            {
                RegistryValueInfo value = ProcessSubkeyEntry(subKeyEntry);
                if (value != null)
                {
                    currentKey.Values.Add(value);
                }
            }
        }

        private List<string> SplitIntoSubkeyEntries(string keyBlock)
        {
            List<string> subKeyEntries = new List<string>();
            
            // Find all matches of the subkey pattern
            MatchCollection matches = SUBKEY_REGEX.Matches(keyBlock);
            
            // If no matches found, return empty list
            if (matches.Count == 0)
                return subKeyEntries;
            
            // Process each match
            for (int i = 0; i < matches.Count; i++)
            {
                int startIndex = matches[i].Index;
                int endIndex;
                
                // If this is the last match, the end is the end of the block
                if (i == matches.Count - 1)
                {
                    endIndex = keyBlock.Length;
                }
                else
                {
                    endIndex = matches[i + 1].Index;
                }
                
                // Extract the entry
                string entry = keyBlock.Substring(startIndex, endIndex - startIndex);
                subKeyEntries.Add(entry);
            }
            
            return subKeyEntries;
        }

        private RegistryValueInfo ProcessSubkeyEntry(string subKeyEntry)
        {
            string subkeyName = "";

            try
            {
                // Remove the leading tab
                subKeyEntry = subKeyEntry.TrimStart('\t');
                
                // Find the registry type
                Match typeMatch = REG_TYPE_REGEX.Match(subKeyEntry);
                if (!typeMatch.Success)
                    return null;
                
                // Extract the key name (everything before the type)
                subkeyName = subKeyEntry.Substring(0, typeMatch.Index).Trim();
                
                // Get the registry type string
                string typeStr = typeMatch.Value;
                
                // Determine the registry type
                uint type = GetRegistryType(typeStr);
                
                // Extract the value (everything after the type)
                string valueStr = "";
                
                // Extract value part after the type
                if (typeMatch.Index + typeMatch.Length < subKeyEntry.Length)
                {
                    valueStr = subKeyEntry.Substring(typeMatch.Index + typeMatch.Length).Trim();
                }
                
                // Process the value based on the type
                byte[] data;
                switch (type)
                {
                    case API.REG_BINARY:
                        // For binary, extract all hex digits and convert to bytes
                        data = ProcessBinaryData(valueStr);
                        break;
                        
                    case API.REG_DWORD:
                        // Parse the DWORD value
                        valueStr = valueStr.Trim();
                        uint dwordValue;
                        if (uint.TryParse(valueStr, out dwordValue))
                        {
                            data = BitConverter.GetBytes(dwordValue);
                        }
                        else
                        {
                            // Try parsing as hex if it has 0x prefix
                            if (valueStr.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                            {
                                dwordValue = Convert.ToUInt32(valueStr.Substring(2), 16);
                                data = BitConverter.GetBytes(dwordValue);
                            }
                            else
                            {
                                // Just try as hex
                                dwordValue = Convert.ToUInt32(valueStr, 16);
                                data = BitConverter.GetBytes(dwordValue);
                            }
                        }
                        break;
                        
                    case API.REG_SZ:
                    case API.REG_EXPAND_SZ:
                        // For string values, store as Unicode with null terminator
                        string strWithNull = valueStr + '\0';
                        data = Encoding.Unicode.GetBytes(strWithNull);
                        break;
                        
                    case API.REG_MULTI_SZ:
                        // Handle multi-string values
                        List<string> strings = new List<string>();
                        
                        // Check if values are separated by \0
                        if (valueStr.Contains("\\0"))
                        {
                            strings.AddRange(valueStr.Split(new[] { "\\0" }, StringSplitOptions.RemoveEmptyEntries));
                        }
                        else
                        {
                            // Just use the single value
                            strings.Add(valueStr);
                        }
                        
                        List<byte> multiStrData = new List<byte>();
                        
                        foreach (string str in strings)
                        {
                            string trimmed = str.Trim();
                            if (!string.IsNullOrEmpty(trimmed))
                            {
                                byte[] strBytes = Encoding.Unicode.GetBytes(trimmed + '\0');
                                multiStrData.AddRange(strBytes);
                            }
                        }
                        
                        // Add final null terminator
                        multiStrData.AddRange(Encoding.Unicode.GetBytes("\0"));
                        data = multiStrData.ToArray();
                        break;
                        
                    default:
                        // For unknown types, store as string
                        data = Encoding.Unicode.GetBytes(valueStr + '\0');
                        break;
                }
                
                return new RegistryValueInfo
                {
                    Name = subkeyName,
                    Type = type,
                    Data = data
                };
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing subkey [{subkeyName}] entry: {ex.Message}");
                Console.WriteLine(subKeyEntry);
                return null;
            }
        }

        private byte[] ProcessBinaryData(string valueStr)
        {
            // Extract only hex characters
            StringBuilder hexOnly = new StringBuilder();
            foreach (char c in valueStr)
            {
                if (IsHexDigit(c))
                {
                    hexOnly.Append(c);
                }
            }
            
            string hexString = hexOnly.ToString();
            
            // If there's an odd number of hex characters, pad with a leading zero
            if (hexString.Length % 2 != 0)
            {
                hexString = "0" + hexString;
            }
            
            // Convert to bytes
            List<byte> bytes = new List<byte>();
            for (int i = 0; i < hexString.Length; i += 2)
            {
                string byteStr = hexString.Substring(i, 2);
                try
                {
                    byte value = Convert.ToByte(byteStr, 16);
                    bytes.Add(value);
                }
                catch
                {
                    // Skip invalid hex values
                }
            }
            
            return bytes.ToArray();
        }

        private uint GetRegistryType(string typeStr)
        {
            switch (typeStr.ToUpper())
            {
                case "REG_SZ":
                    return API.REG_SZ;
                case "REG_BINARY":
                    return API.REG_BINARY;
                case "REG_DWORD":
                    return API.REG_DWORD;
                case "REG_QWORD":
                    return API.REG_QWORD;
                case "REG_MULTI_SZ":
                    return API.REG_MULTI_SZ;
                case "REG_EXPAND_SZ":
                    return API.REG_EXPAND_SZ;
                default:
                    return API.REG_NONE;
            }
        }

        private RegistryKeyInfo GetOrCreateKeyPath(RegistryKeyInfo rootKey, string[] keyParts)
        {
            RegistryKeyInfo currentKey = rootKey;

            foreach (string part in keyParts)
            {
                if (string.IsNullOrEmpty(part))
                    continue;

                // Look for existing subkey
                RegistryKeyInfo subKey = currentKey.Subkeys.Find(k => k.Name.Equals(part, StringComparison.OrdinalIgnoreCase));
                
                if (subKey == null)
                {
                    // Create new subkey
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

            return currentKey;
        }

        private bool IsHexDigit(char c)
        {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
        }
    }
}
