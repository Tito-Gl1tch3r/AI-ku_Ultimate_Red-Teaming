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
 */

using PeNet;
using PeNet.Header.Pe;
using System.Text;

namespace AstralPE.Obfuscator.Modules {
    public class FreePascalCompilerMutator : IAstralPeModule {

        /// <summary>
        /// Applies Free Pascal Compiler (FPC) specific metadata cleanup to the PE file.
        /// </summary>
        /// <param name="raw">The raw byte array of the PE file.</param>
        /// <param name="pe">The parsed PE structure.</param>
        /// <param name="e_lfanew">The offset of the PE header.</param>
        /// <param name="optStart">The start offset of the Optional Header.</param>
        /// <param name="sectionTableOffset">The offset of the section table.</param>
        /// <param name="rnd">Random number generator instance.</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Ensure section headers are present
            if (pe.ImageSectionHeaders == null)
                return;

            // Check for the presence of .bss or .CRT sections
            int markersFound = 0;
            for (int i = 0; i < pe.ImageSectionHeaders.Length; i++) {
                string name = pe.ImageSectionHeaders[i].Name;
                if (name == ".bss" || name == ".CRT")
                    markersFound++;
            }

            if (markersFound == 0) // No marker sections found – nothing to do
                return;

            // Process both .rdata and .data sections for FPC strings
            for (int idx = 0; idx < pe.ImageSectionHeaders.Length; idx++) {
                ImageSectionHeader section = pe.ImageSectionHeaders[idx];
                if (section.Name != ".rdata" && section.Name != ".data")
                    continue;

                // Ensure the section is valid
                if (section.PointerToRawData == 0 || section.SizeOfRawData == 0)
                    continue;

                int sectionStart = (int)section.PointerToRawData,
                    sectionSize = (int)section.SizeOfRawData;

                if (sectionStart + sectionSize > raw.Length)
                    throw new IndexOutOfRangeException("Section data goes beyond file bounds.");

                byte[] sectionData = new byte[sectionSize];
                Array.Copy(raw, sectionStart, sectionData, 0, sectionSize);

                byte[] fpcPattern = Encoding.ASCII.GetBytes("FPC");
                int pos = Patcher.IndexOf(sectionData, fpcPattern, 0);

                // Clear all null-terminated strings that contain "FPC"
                while (pos != -1) {

                    int strStart = pos;
                    while (strStart > 0 && sectionData[strStart - 1] != 0)
                        strStart--;

                    int strEnd = pos;
                    while (strEnd < sectionData.Length && sectionData[strEnd] != 0)
                        strEnd++;

                    string s = Encoding.ASCII.GetString(sectionData, strStart, strEnd - strStart);
                    if (s.Contains("FPC")) {
                        for (int j = strStart; j < strEnd; j++)
                            sectionData[j] = 0;
                    }
                    pos = Patcher.IndexOf(sectionData, fpcPattern, strEnd);
                }

                Array.Copy(sectionData, 0, raw, sectionStart, sectionSize);
            }
        }
    }
}
