using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

namespace Swarmer
{
    public class RegistryParser
    {
        public RegistryParser()
        {
        }

        public RegistryKeyInfo ParseRegFile(string regFilePath)
        {
            string[] lines = File.ReadAllLines(regFilePath, Encoding.Unicode);
            
            // Check for REG format header
            if (lines.Length == 0 || !lines[0].StartsWith("Windows Registry Editor"))
            {
                throw new FormatException("Not a valid .reg file. Missing registry editor header.");
            }

            // Create a root key to represent HKCU
            RegistryKeyInfo rootKey = new RegistryKeyInfo
            {
                Name = "HKEY_CURRENT_USER",
                Values = new List<RegistryValueInfo>(),
                Subkeys = new List<RegistryKeyInfo>()
            };

            string currentKeyPath = null;
            RegistryKeyInfo currentKey = null;
            
            // For multi-line values
            bool collectingMultiLine = false;
            string multiLineName = null;
            StringBuilder multiLineValue = new StringBuilder();

            // Process each line
            for (int i = 1; i < lines.Length; i++)
            {
                string line = lines[i].Trim();

                // Skip empty lines
                if (string.IsNullOrEmpty(line))
                    continue;

                // If we're collecting a multi-line value
                if (collectingMultiLine)
                {
                    // Check if this line continues the multi-line value
                    if (line.EndsWith("\\"))
                    {
                        // Remove the trailing backslash and add to our value
                        multiLineValue.Append(line.Substring(0, line.Length - 1));
                        continue;
                    }
                    else
                    {
                        // This is the last line of the multi-line value
                        multiLineValue.Append(line);
                        
                        // Process the complete value
                        if (currentKey != null)
                        {
                            string fullValueLine = multiLineName + "=" + multiLineValue.ToString();
                            RegistryValueInfo value = ParseValueLine(fullValueLine);
                            if (value != null)
                            {
                                currentKey.Values.Add(value);
                            }
                        }
                        
                        // Reset multi-line tracking
                        collectingMultiLine = false;
                        multiLineName = null;
                        multiLineValue.Clear();
                        continue;
                    }
                }

                // Check for key declaration
                if (line.StartsWith("[") && line.EndsWith("]"))
                {
                    // Extract key path
                    string keyPath = line.Substring(1, line.Length - 2);
                    
                    // Handle key deletion notation
                    if (keyPath.StartsWith("-"))
                    {
                        // We're creating a new hive, so we can just skip deletion directives
                        currentKeyPath = null;
                        currentKey = null;
                        continue;
                    }

                    // Check if it's a HKCU key (which we want)
                    if (keyPath.Equals("HKEY_CURRENT_USER") || keyPath.Equals("HKCU"))
                    {
                        // This is the root key
                        currentKeyPath = "";
                        currentKey = rootKey;
                    }
                    else if (keyPath.StartsWith("HKEY_CURRENT_USER\\") || keyPath.StartsWith("HKCU\\"))
                    {
                        // Remove the HKCU prefix
                        if (keyPath.StartsWith("HKEY_CURRENT_USER\\"))
                            keyPath = keyPath.Substring("HKEY_CURRENT_USER\\".Length);
                        else if (keyPath.StartsWith("HKCU\\"))
                            keyPath = keyPath.Substring("HKCU\\".Length);

                        currentKeyPath = keyPath;
                        
                        // Create or get the key in our structure
                        currentKey = GetOrCreateKeyPath(rootKey, keyPath.Split('\\'));
                    }
                    else
                    {
                        // We only want HKCU keys for our hive
                        currentKeyPath = null;
                        currentKey = null;
                    }
                }
                else if (currentKey != null)
                {
                    // Check for value
                    int equalsPos = line.IndexOf('=');
                    if (equalsPos > 0)
                    {
                        // Extract name and value parts
                        string name = line.Substring(0, equalsPos);
                        string value = line.Substring(equalsPos + 1);
                        
                        // Check if this is a multi-line value (ends with backslash)
                        if (value.EndsWith("\\"))
                        {
                            // Start tracking a multi-line value
                            collectingMultiLine = true;
                            multiLineName = name;
                            multiLineValue.Clear();
                            multiLineValue.Append(value.Substring(0, value.Length - 1));
                        }
                        else
                        {
                            // Process single-line value
                            RegistryValueInfo valueInfo = ParseValueLine(line);
                            if (valueInfo != null)
                            {
                                currentKey.Values.Add(valueInfo);
                            }
                        }
                    }
                }
            }

            return rootKey;
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

        private RegistryValueInfo ParseValueLine(string line)
        {
            try
            {
                // Find the position of the first equals sign
                int equalsPos = line.IndexOf('=');
                if (equalsPos <= 0)
                {
                    return null;
                }

                // Extract name and value parts
                string namePart = line.Substring(0, equalsPos).Trim();
                string valueContent = line.Substring(equalsPos + 1).Trim();

                // Parse the name part
                string valueName;
                if (namePart == "@")
                {
                    valueName = "";
                }
                else if (namePart.StartsWith("\"") && namePart.EndsWith("\""))
                {
                    // Remove the quotes
                    valueName = namePart.Substring(1, namePart.Length - 2);
                    
                    // Unescape the name
                    valueName = UnescapeRegString(valueName);
                }
                else
                {
                    // This is an invalid format, but let's try to handle it anyway
                    valueName = namePart;
                }
                
                // Parse the value content
                uint valueType;
                byte[] valueData;
                
                if (valueContent.StartsWith("dword:"))
                {
                    // DWORD value
                    valueType = API.REG_DWORD;
                    string dwordStr = valueContent.Substring(6);
                    
                    try
                    {
                        uint dwordValue = Convert.ToUInt32(dwordStr, 16);
                        valueData = BitConverter.GetBytes(dwordValue);
                    }
                    catch (Exception)
                    {
                        return null;
                    }
                }
                else if (valueContent.StartsWith("hex:"))
                {
                    // Binary value
                    valueType = API.REG_BINARY;
                    string hexData = valueContent.Substring(4);
                    valueData = ParseHexString(hexData);
                }
                else if (valueContent.StartsWith("hex("))
                {
                    // Other hex-encoded value
                    int closingParenPos = valueContent.IndexOf(')');
                    if (closingParenPos < 0)
                    {
                        return null;
                    }
                    
                    string typeStr = valueContent.Substring(4, closingParenPos - 4);
                    string hexData = valueContent.Substring(closingParenPos + 2); // Skip "):""
                    
                    try
                    {
                        valueType = Convert.ToUInt32(typeStr, 16);
                    }
                    catch
                    {
                        valueType = API.REG_BINARY;
                    }
                    
                    valueData = ParseHexString(hexData);
                }
                else if (valueContent.StartsWith("\"") && valueContent.EndsWith("\""))
                {
                    // String value
                    valueType = API.REG_SZ;
                    string strValue = valueContent.Substring(1, valueContent.Length - 2);
                    
                    // Unescape the string
                    strValue = UnescapeRegString(strValue);
                    
                    // Add null terminator
                    strValue += '\0';
                    valueData = Encoding.Unicode.GetBytes(strValue);
                }
                else
                {
                    return null;
                }

                return new RegistryValueInfo
                {
                    Name = valueName,
                    Type = valueType,
                    Data = valueData
                };
            }
            catch (Exception)
            {
                return null;
            }
        }

        private string UnescapeRegString(string str)
        {
            // Handle escape sequences in registry strings
            StringBuilder result = new StringBuilder(str.Length);
            
            for (int i = 0; i < str.Length; i++)
            {
                if (str[i] == '\\' && i + 1 < str.Length)
                {
                    // Handle escape sequence
                    switch (str[i + 1])
                    {
                        case '\\': // Backslash
                            result.Append('\\');
                            break;
                        case '"': // Quote
                            result.Append('"');
                            break;
                        case 'r': // Carriage return
                            result.Append('\r');
                            break;
                        case 'n': // Line feed
                            result.Append('\n');
                            break;
                        default: // Other escaped character (just keep it)
                            result.Append(str[i + 1]);
                            break;
                    }
                    i++; // Skip the escaped character
                }
                else
                {
                    result.Append(str[i]);
                }
            }
            
            return result.ToString();
        }

        private byte[] ParseHexString(string hexString)
        {
            List<byte> bytes = new List<byte>();
            
            // Remove whitespace and line continuation characters
            StringBuilder cleanedHex = new StringBuilder();
            for (int i = 0; i < hexString.Length; i++)
            {
                if (hexString[i] == '\\')
                {
                    // Skip backslash and any following whitespace
                    i++;
                    while (i < hexString.Length && char.IsWhiteSpace(hexString[i]))
                        i++;
                    
                    // Back up one character since the loop will increment i
                    i--;
                }
                else if (!char.IsWhiteSpace(hexString[i]))
                {
                    cleanedHex.Append(hexString[i]);
                }
            }
            
            // Split by commas
            string[] parts = cleanedHex.ToString().Split(',');
            
            foreach (string part in parts)
            {
                string trimmedPart = part.Trim();
                if (string.IsNullOrEmpty(trimmedPart))
                    continue;
                    
                try
                {
                    byte b = Convert.ToByte(trimmedPart, 16);
                    bytes.Add(b);
                }
                catch (Exception)
                {                    
                }
            }
            
            return bytes.ToArray();
        }

        // Helper method to check if a quote is escaped
        private bool IsEscapedQuote(string text, int quotePos)
        {
            if (quotePos <= 0)
                return false;
            
            // Count backslashes before the quote
            int backslashCount = 0;
            int pos = quotePos - 1;
            
            while (pos >= 0 && text[pos] == '\\')
            {
                backslashCount++;
                pos--;
            }
            
            // If there's an odd number of backslashes, the quote is escaped
            return backslashCount % 2 != 0;
        }

        private bool IsHexDigit(char c)
        {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
        }
    }

    // Helper class to mimic std::string_view from C++
    public class StringView
    {
        private readonly string _source;
        private int _start;
        private int _length;
        
        public StringView(string source)
        {
            _source = source;
            _start = 0;
            _length = source.Length;
        }
        
        public int Length => _length;
        
        public bool IsEmpty => _length == 0;
        
        public char this[int index]
        {
            get
            {
                if (index < 0 || index >= _length)
                    throw new IndexOutOfRangeException();
                return _source[_start + index];
            }
        }
        
        public void RemovePrefix(int count)
        {
            if (count > _length)
                count = _length;
            
            _start += count;
            _length -= count;
        }
        
        public string Substring(int start, int length)
        {
            if (start < 0 || start >= _length)
                throw new IndexOutOfRangeException();
            
            if (length > _length - start)
                length = _length - start;
            
            return _source.Substring(_start + start, length);
        }
        
        public int IndexOf(string value)
        {
            int pos = _source.IndexOf(value, _start, _length);
            return pos == -1 ? -1 : pos - _start;
        }
        
        public bool StartsWith(string value)
        {
            if (_length < value.Length)
                return false;
            
            for (int i = 0; i < value.Length; i++)
            {
                if (_source[_start + i] != value[i])
                    return false;
            }
            
            return true;
        }
    }

    // Classes to store registry information
    public class RegistryValueInfo
    {
        public string Name { get; set; }
        public uint Type { get; set; }
        public byte[] Data { get; set; }
    }

    public class RegistryKeyInfo
    {
        public string Name { get; set; }
        public List<RegistryValueInfo> Values { get; set; }
        public List<RegistryKeyInfo> Subkeys { get; set; }
    }
} 