using System;
using System.Collections.Generic;
using System.IO;

namespace Swarmer
{
    public class HiveWriter
    {
        public HiveWriter()
        {
        }

        public bool CreateAndPopulateHive(RegistryKeyInfo rootKey, string outputHivePath)
        {
            try
            {
                Console.WriteLine($"Creating and populating hive to: {outputHivePath}");
                Console.WriteLine($"Root key: {rootKey.Name}");
                Console.WriteLine($"Subkeys: {rootKey.Subkeys.Count}");
                Console.WriteLine($"Values: {rootKey.Values.Count}");

                string fullHivePath = Path.GetFullPath(outputHivePath);
                string initialTempPath = Path.Combine(Path.GetDirectoryName(fullHivePath), 
                    $"initial_{Path.GetRandomFileName()}_{Path.GetFileName(fullHivePath)}");
                string saveTempPath = Path.Combine(Path.GetDirectoryName(fullHivePath), 
                    $"save_{Path.GetRandomFileName()}_{Path.GetFileName(fullHivePath)}");

                SafeDeleteFile(initialTempPath);
                SafeDeleteFile(saveTempPath);

                IntPtr hiveKey = IntPtr.Zero;
                uint result;

                // Step 1: Create an empty file for RegLoadAppKeyW
                using (File.Create(initialTempPath)) { }
                
                // Step 2: Load the empty hive using RegLoadAppKeyW
                result = API.RegLoadAppKeyW(
                    initialTempPath,
                    out hiveKey,
                    API.KEY_ALL_ACCESS,
                    API.REG_PROCESS_APPKEY,
                    0);

                if (result != API.ERROR_SUCCESS)
                {
                    Console.WriteLine($"Failed to create hive using RegLoadAppKeyW. Error code: {result}");
                    return false;
                }

                // Step 3: Close the RegLoadAppKeyW handle
                if (hiveKey != IntPtr.Zero)
                {
                    API.RegCloseKey(hiveKey);
                    hiveKey = IntPtr.Zero;
                }
                
                // Step 4: Now open the hive with OROpenHive
                result = API.OROpenHive(initialTempPath, out hiveKey);
                if (result != API.ERROR_SUCCESS)
                {
                    Console.WriteLine($"Failed to open hive with OROpenHive. Error code: {result}");
                    return false;
                }

                PopulateHiveFromRegistryData(hiveKey, rootKey);

                // Get current OS version
                var osVersion = Environment.OSVersion.Version;
                uint osMajorVersion = (uint)osVersion.Major;
                uint osMinorVersion = (uint)osVersion.Minor;
                Console.WriteLine($"Saving hive to: {fullHivePath}");
                
                SafeDeleteFile(saveTempPath);
                result = API.ORSaveHive(hiveKey, saveTempPath, osMajorVersion, osMinorVersion);

                if (result != API.ERROR_SUCCESS)
                {
                    Console.WriteLine($"Failed to save hive to temporary file. Error code: {result} (0x{result:X})");
                    return false;
                }
                else
                {
                    SafeDeleteFile(fullHivePath);
                    File.Move(saveTempPath, fullHivePath);
                }

                API.ORCloseHive(hiveKey);
                SafeDeleteFile(initialTempPath);
                SafeDeleteFile(saveTempPath);

                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
                return false;
            }
        }

        private void PopulateHiveFromRegistryData(IntPtr hiveKey, RegistryKeyInfo rootKey)
        {
            // Process all values in the root key
            foreach (var value in rootKey.Values)
            {
                SetRegistryValue(hiveKey, value);
            }

            // Process all subkeys recursively
            foreach (var subkey in rootKey.Subkeys)
            {
                IntPtr subkeyHandle = CreateRegistryKey(hiveKey, subkey.Name);
                if (subkeyHandle != IntPtr.Zero)
                {
                    // Process the subkey's values
                    foreach (var value in subkey.Values)
                    {
                        SetRegistryValue(subkeyHandle, value);
                    }
                    ProcessSubkeys(subkeyHandle, subkey.Subkeys);
                    API.ORCloseKey(subkeyHandle);
                }
            }
        }

        private void ProcessSubkeys(IntPtr parentKeyHandle, List<RegistryKeyInfo> subkeys)
        {
            foreach (var subkey in subkeys)
            {
                IntPtr subkeyHandle = CreateRegistryKey(parentKeyHandle, subkey.Name);
                if (subkeyHandle != IntPtr.Zero)
                {
                    // Process the subkey's values
                    foreach (var value in subkey.Values)
                    {
                        SetRegistryValue(subkeyHandle, value);
                    }
                    ProcessSubkeys(subkeyHandle, subkey.Subkeys);
                    API.ORCloseKey(subkeyHandle);
                }
            }
        }

        private IntPtr CreateRegistryKey(IntPtr parentKeyHandle, string keyName)
        {
            IntPtr keyHandle;
            uint disposition;

            uint result = API.ORCreateKey(
                parentKeyHandle,
                keyName,
                null,
                API.REG_OPTION_NON_VOLATILE,
                IntPtr.Zero,
                out keyHandle,
                out disposition);

            if (result != API.ERROR_SUCCESS)
            {
                return IntPtr.Zero;
            }
            return keyHandle;
        }

        private void SetRegistryValue(IntPtr keyHandle, RegistryValueInfo value)
        {
            uint result = API.ORSetValue(
                keyHandle,
                value.Name,
                value.Type,
                value.Data,
                (uint)value.Data.Length);
        }

        // Helper method to safely delete a file if it exists
        private void SafeDeleteFile(string filePath)
        {
            try
            {
                if (File.Exists(filePath))
                {
                    File.Delete(filePath);
                }
            }
            catch (Exception)
            {
            }
        }
    }
} 