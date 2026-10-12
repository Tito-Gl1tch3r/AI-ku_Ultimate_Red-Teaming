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

using PeNet;
using PeNet.Header.Pe;
using System.Diagnostics;
using System.Text;

namespace AstralPE.Obfuscator.Modules {
    public class OriginalNameWiper : IAstralPeModule {

        /// <summary>
        /// Applies the cleaning logic to strip any original file names.
        /// </summary>
        /// <param name="raw">The raw PE byte array.</param>
        /// <param name="pe">Parsed PE file structure.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to IMAGE_OPTIONAL_HEADER.</param>
        /// <param name="sectionTableOffset">Offset to the section table.</param>
        /// <param name="rnd">Random number generator (not used).</param>
        public void Apply(ref byte[] raw, PeNet.PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Ensure the PE file is valid
            if (pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Try to wipe OriginalFilename from end of file

            FileVersionInfo? verInfo = FileVersionInfo.GetVersionInfo(PeMutator.SelectedFilePath);
            if (!string.IsNullOrEmpty(verInfo.OriginalFilename)) {
                string orig = verInfo.OriginalFilename;
                byte[] value = Encoding.Unicode.GetBytes(orig + "\0"); // UTF-16 null-terminated

                // Scan the last N bytes of the file for the encoded string (starting from end)
                const int searchWindow = 0x4000; // scan last 16 KB max
                int start = Math.Max(0, raw.Length - searchWindow);

                for (int i = raw.Length - value.Length; i >= start; i--) {
                    bool match = true;
                    for (int j = 0; j < value.Length; j++) {
                        if (raw[i + j] != value[j]) {
                            match = false;
                            break;
                        }
                    }

                    if (match) {
                        Array.Clear(raw, i, value.Length); // zero out the string
                        break;
                    }
                }
            }

            // Wipe export name (if export directory is valid)
            ImageDataDirectory? exportDir = pe.ImageNtHeaders?.OptionalHeader.DataDirectory[0]; // Export is index 0
            if (exportDir == null || exportDir.VirtualAddress == 0 || exportDir.Size == 0)
                return; // No export directory

            uint rva = exportDir.VirtualAddress,
                 exportBaseOffset;

            try {
                exportBaseOffset = rva.RvaToOffset(pe.ImageSectionHeaders);
            } catch {
                // Could not resolve section (e.g., UPX-packed binary)
                return;
            }

            if (exportBaseOffset + 0x10 > raw.Length)
                return; // Structure truncated

            uint nameRva = BitConverter.ToUInt32(raw, (int)(exportBaseOffset + 0x0C));
            if (nameRva == 0)
                return; // No name present

            uint nameOffset;
            try {
                nameOffset = nameRva.RvaToOffset(pe.ImageSectionHeaders);
            } catch {
                return; // Can't map RVA to offset (e.g., section missing)
            }

            if (nameOffset == 0 || nameOffset >= raw.Length)
                throw new IndexOutOfRangeException("Export name offset is outside of file bounds.");

            // Zero out ASCII string name (null-terminated)
            int k = (int)nameOffset;
            while (k < raw.Length && raw[k] != 0) {
                raw[k++] = 0;
            }
        }
    }
}