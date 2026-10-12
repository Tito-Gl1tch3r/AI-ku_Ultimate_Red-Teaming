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
using System.Text;

namespace AstralPE.Obfuscator.Modules {
    public class DelphiLazarusMutator : IAstralPeModule {

        /// <summary>
        /// Applies Delphi/Lazarus meta data cleanup to the PE file.
        /// </summary>
        /// <param name="raw">The raw byte array of the PE file.</param>
        /// <param name="pe">The parsed PE structure.</param>
        /// <param name="e_lfanew">The offset of the PE header.</param>
        /// <param name="optStart">The start offset of the Optional Header.</param>
        /// <param name="sectionTableOffset">The offset of the section table.</param>
        /// <param name="rnd">Random number generator instance.</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Ensure the section headers are present
            if (pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Check for the presence of .bss or .CRT sections
            int markersFound = 0;
            for (int i = 0; i < pe.ImageSectionHeaders.Length; i++) {
                string name = pe.ImageSectionHeaders[i].Name;
                if (name == ".bss" || name == ".CRT") {
                    markersFound++;
                    break;
                }
            }

            if (markersFound != 2) // No Delphi/Lazarus sections found
                return;

            string[] exactMatches = new string[] {
                "Property streamed in older Lazarus revision",
                "Used in a previous version of Lazarus"
            };

            string[] prefixMatches = new string[] {
                "TLazWriterTiff - Lazarus LCL: ",
                "TTiffImage - Lazarus LCL: "
            };

            // Remove exact matches in the whole file
            for (int i = 0; i < exactMatches.Length; i++) {
                byte[] pattern = Encoding.ASCII.GetBytes(exactMatches[i]);
                int index = Patcher.IndexOf(raw, pattern, 0);

                while (index != -1) {
                    int end = index;
                    while (end < raw.Length && raw[end] != 0)
                        end++;
                    for (int j = index; j < end; j++)
                        raw[j] = 0;
                    index = Patcher.IndexOf(raw, pattern, end);
                }
            }

            // Remove prefix matches in the whole file
            for (int i = 0; i < prefixMatches.Length; i++) {
                byte[] prefixPattern = Encoding.ASCII.GetBytes(prefixMatches[i]);
                int index = Patcher.IndexOf(raw, prefixPattern, 0);

                while (index != -1) {
                    int end = index;
                    while (end < raw.Length && raw[end] != 0)
                        end++;
                    for (int j = index; j < end; j++)
                        raw[j] = 0;
                    
                    index = Patcher.IndexOf(raw, prefixPattern, end);
                }
            }
        }
    }
}