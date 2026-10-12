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
    public class PermissionsSetter : IAstralPeModule {

        /// <summary>
        /// Applies full memory access flags (RWE + code) to all section headers in the PE file.
        /// </summary>
        /// <param name="raw">The raw byte buffer of the PE image.</param>
        /// <param name="pe">The parsed PE structure.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to IMAGE_OPTIONAL_HEADER.</param>
        /// <param name="sectionTableOffset">Offset to section table start.</param>
        /// <param name="rnd">Random generator (unused).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Ensure section headers are present
            if (pe.ImageSectionHeaders == null || pe.ImageSectionHeaders.Length == 0)
                throw new InvalidPeImageException();

            const int sectionHeaderSize = 40,         // IMAGE_SECTION_HEADER size is 40 bytes
                      characteristicsOffset = 36;     // Characteristics field offset within IMAGE_SECTION_HEADER

            // Define the new permissions:
            // R = Read, W = Write, E = Execute, + mark as code section
            const uint perms = (uint)(
                PeNet.Header.Pe.ScnCharacteristicsType.MemRead |
                PeNet.Header.Pe.ScnCharacteristicsType.MemWrite |
                PeNet.Header.Pe.ScnCharacteristicsType.MemExecute |
                PeNet.Header.Pe.ScnCharacteristicsType.CntCode);

            // Loop through all section headers
            for (int i = 0; i < pe.ImageSectionHeaders.Length; i++) {
                // Calculate the start offset of the current section header
                int sectionOffset = sectionTableOffset + i * sectionHeaderSize;

                // Ensure we won't go out of bounds when writing the 4-byte value
                if (sectionOffset + characteristicsOffset + 4 > raw.Length)
                    throw new ArgumentOutOfRangeException(nameof(raw), "Section header characteristics offset exceeds file bounds.");

                // Overwrite the Characteristics field with our RWE + Code flags
                BitConverter.GetBytes(perms).CopyTo(raw, sectionOffset + characteristicsOffset);
            }
        }
    }
}
