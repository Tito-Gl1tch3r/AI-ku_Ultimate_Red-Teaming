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

namespace AstralPE.Obfuscator.Modules {
    public class SectionNameWiper : IAstralPeModule {

        // The size of a section header in the PE file format (40 bytes).
        private const int SectionHeaderSize = 40;

        /// <summary>
        /// Wipes the names of all sections in the PE file.
        /// This is done by clearing the first 8 bytes (section name) of each section header.
        /// </summary>
        /// <param name="raw">The raw byte array representing the PE file.</param>
        /// <param name="pe">The parsed PE file object containing section headers.</param>
        /// <param name="e_lfanew">The offset to the IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">The offset to the Optional Header.</param>
        /// <param name="sectionTableOffset">The offset to the section table.</param>
        /// <param name="rnd">Random generator, which is not used in this method.</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Ensure the section headers are present
            if (pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Check that section table offset is not obviously broken
            if (sectionTableOffset <= 0 || sectionTableOffset > raw.Length)
                throw new ArgumentOutOfRangeException(nameof(sectionTableOffset), "Section table offset is invalid.");

            // Iterate through all section headers in the PE file
            for (int i = 0; i < pe.ImageSectionHeaders.Length; i++) {
                // Calculate the offset of the current section header
                int sectionNameOffset = sectionTableOffset + i * SectionHeaderSize;

                // Bounds check to avoid corrupting memory
                if (sectionNameOffset + 8 > raw.Length)
                    throw new IndexOutOfRangeException("Section name offset exceeds buffer length.");

                // Clear the first 8 bytes of each section header (section name)
                for (int j = 0; j < 8; j++)
                    raw[sectionNameOffset + j] = 0x00;
            }
        }
    }
}
