/*
 * This file is part of the Astral-PE project.
 * Copyright (c) 2025 DosX. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 * Astral-PE is a low-level post-compilation PE header mutator (obfuscator) for native
 * Windows x86/x64 binaries. It modifies structural metadata while preserving execution integrity.
 *
 * For source code, updates, and documentation, visit:
 * https://github.com/DosX-dev/Astral-PE
 */

using Astral_PE.modules;
using PeNet;
using System.Text;

namespace AstralPE.Obfuscator.Modules {
    public class ImportMutator : IAstralPeModule {
        /// <summary>
        /// Applies mutation to the PE file's import table.
        /// This includes DLL name mutation and noise injection into metadata fields.
        /// </summary>
        /// <param name="raw">Raw byte array representing the PE file.</param>
        /// <param name="pe">Parsed PE file object.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS (unused here).</param>
        /// <param name="optStart">Offset to the Optional Header start (unused here).</param>
        /// <param name="sectionTableOffset">Offset to the section table (unused here).</param>
        /// <param name="rnd">Random number generator instance.</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Basic validation for PE structure presence
            if (pe.ImageNtHeaders == null || pe.ImageSectionHeaders == null ||
                pe.ImageImportDescriptors == null || pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            uint importTableRva = pe.ImageNtHeaders.OptionalHeader.DataDirectory[1].VirtualAddress;
            int descriptorIndex = 0;

            // Iterate through each IMAGE_IMPORT_DESCRIPTOR in the import table
            foreach (var descriptor in pe.ImageImportDescriptors) {
                uint nameRva = descriptor.Name,
                     fileOffset = Patcher.RvaToOffset(nameRva, pe.ImageSectionHeaders);

                if (fileOffset == 0 || fileOffset >= raw.Length)
                    continue; // Skip invalid or corrupted entries

                // Calculate the length of the null-terminated DLL name string
                int length = 0;
                
                while (fileOffset + length < raw.Length && raw[fileOffset + length] != 0)
                    length++;

                if (length == 0)
                    continue;

                // Extract original DLL name
                string original = Encoding.ASCII.GetString(raw, (int)fileOffset, length),
                       dll = original;

                // Only mutate DLLs that are not Windows API sets (e.g., api-ms-win-*)
                bool hasDllExtension = dll.EndsWith(".dll", StringComparison.OrdinalIgnoreCase);

                // Remove ".dll" extension for mutation
                if (hasDllExtension)
                    dll = dll[..^4];

                // Randomize character casing of the DLL name
                string mutated = StringsWorker.RandomizeCase(dll);

                if (!PeMutator.LegacyWinCompatMode) { // Not for Windows 7 / 8
                    // Optionally prepend random path-like prefix
                    if (hasDllExtension && !dll.StartsWith("api-ms-win-", StringComparison.OrdinalIgnoreCase)) {
                        string[] sep = ["./", ".\\"];
                        string prefix = sep[rnd.Next(sep.Length)];
                        if (rnd.Next(2) == 0)
                            prefix += sep[rnd.Next(sep.Length)];
                        mutated = prefix + mutated;
                    }
                }

                // Encode back to ASCII with null terminator
                byte[] mutatedBytes = Encoding.ASCII.GetBytes(mutated + "\0");

                // Enforce safety limit (max 8 extra bytes beyond original)
                if (mutatedBytes.Length > length + 8)
                    throw new InvalidOperationException("Mutated name is too long.");

                // Overwrite original DLL name in-place
                Array.Copy(mutatedBytes, 0, raw, (int)fileOffset, mutatedBytes.Length);

                // Get the raw file offset for this IMAGE_IMPORT_DESCRIPTOR
                uint descriptorRva = importTableRva + (uint)(descriptorIndex * 20),
                     descriptorOffset = Patcher.RvaToOffset(descriptorRva, pe.ImageSectionHeaders);

                // Inject random values into TimeDateStamp and ForwarderChain (fields at offset +4 and +8)
                if (descriptorOffset + 12 <= raw.Length) {
                    uint timeDateStamp = (uint)rnd.Next(int.MinValue, int.MaxValue),
                         forwarderChain = (uint)rnd.Next(int.MinValue, int.MaxValue);

                    raw[descriptorOffset + 4] = (byte)(timeDateStamp & 0xFF);
                    raw[descriptorOffset + 5] = (byte)((timeDateStamp >> 8) & 0xFF);
                    raw[descriptorOffset + 6] = (byte)((timeDateStamp >> 16) & 0xFF);
                    raw[descriptorOffset + 7] = (byte)((timeDateStamp >> 24) & 0xFF);

                    raw[descriptorOffset + 8] = (byte)(forwarderChain & 0xFF);
                    raw[descriptorOffset + 9] = (byte)((forwarderChain >> 8) & 0xFF);
                    raw[descriptorOffset + 10] = (byte)((forwarderChain >> 16) & 0xFF);
                    raw[descriptorOffset + 11] = (byte)((forwarderChain >> 24) & 0xFF);
                }

                descriptorIndex++;
            }
        }
    }
}