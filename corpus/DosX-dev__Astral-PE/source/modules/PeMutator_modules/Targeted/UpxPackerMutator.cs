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
using System.Text;

namespace AstralPE.Obfuscator.Modules {
    public class UpxPackerMutator : IAstralPeModule {

        /// <summary>
        /// Detects and removes the UPX version signature from the PE file and changes the imports hash.
        /// </summary>
        /// <param name="raw">The raw byte array of the PE file.</param>
        /// <param name="pe">The parsed PE structure.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to IMAGE_OPTIONAL_HEADER.</param>
        /// <param name="sectionTableOffset">Offset to section table start.</param>
        /// <param name="rnd">Random instance (unused).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            if (pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Check for any section named "UPX"
            if (!pe.ImageSectionHeaders.Any(s => s.Name?.Contains("UPX") == true))
                return;

            // Signature pattern: 4 bytes for version + null + "UPX!"
            // e.g., "4.25\0UPX!" = 4 + 1 + 4 = 9 bytes
            for (int i = 0; i < raw.Length - 8; i++) {
                if (raw[i + 4] == 0x00 &&
                    raw[i + 5] == 'U' && raw[i + 6] == 'P' &&
                    raw[i + 7] == 'X' && raw[i + 8] == '!') {

                    // Clear 9-byte UPX signature
                    Patcher.ReplaceBytes(raw, raw.Skip(i).Take(9).ToArray(), new byte[9]);
                    break;
                }
            }

            if (pe.IsExe) {

                // Change imports hash. Yes, we sacrifice ExitProcess, but it works
                byte[] exit = Encoding.ASCII.GetBytes('\0' + "ExitProcess" + '\0'),
                       fake = Encoding.ASCII.GetBytes('\0' + "CopyContext" + '\0');

                Patcher.ReplaceBytes(raw, exit, fake);
            }
        }
    }
}
