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
    public class GoCompilerMutator : IAstralPeModule {

        /// <summary>
        /// Removes the primary signature that the assembly build ID starts with.
        /// </summary>
        /// <param name="raw">The raw PE file bytes.</param>
        /// <param name="pe">Parsed PE metadata object.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to IMAGE_OPTIONAL_HEADER.</param>
        /// <param name="sectionTableOffset">Offset to section headers.</param>
        /// <param name="rnd">Random number generator (unused).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            if (pe.ImageSectionHeaders == null || pe.ImageSectionHeaders.Length == 0)
                throw new InvalidPeImageException();

            int markersFound = 0;
            for (int i = 0; i < pe.ImageSectionHeaders.Length; i++) {
                string name = pe.ImageSectionHeaders[i].Name;
                if (name == ".symtab" || name == ".reloc")
                    markersFound++;
            }

            if (markersFound != 2)
                return;

            ImageSectionHeader? first = pe.ImageSectionHeaders[0];

            if (first.PointerToRawData == 0 || first.SizeOfRawData == 0)
                return;

            int start = (int)first.PointerToRawData,
                size = (int)first.SizeOfRawData;

            if (start + size > raw.Length)
                throw new IndexOutOfRangeException("Section data goes beyond file bounds.");

            ReadOnlySpan<byte> pattern = Encoding.ASCII.GetBytes(" Go build ID: ");
            ReadOnlySpan<byte> span = raw.AsSpan(start, size);

            int pos = span.IndexOf(pattern);
            if (pos == -1)
                return;

            int absPos = start + pos;
            int strStart = absPos;

            // Expand left to start of string if not null-terminated
            while (strStart > start && raw[strStart - 1] != 0)
                strStart--;

            int strEnd = absPos + pattern.Length;
            while (strEnd < start + size && raw[strEnd] != 0)
                strEnd++;

            for (int i = strStart; i < strEnd; i++)
                raw[i] = 0x00;
        }
    }
}
