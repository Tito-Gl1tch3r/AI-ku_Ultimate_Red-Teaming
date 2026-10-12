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
    public class LargeAddressAwareSetter : IAstralPeModule {

        /// <summary>
        /// Sets the IMAGE_FILE_LARGE_ADDRESS_AWARE flag in IMAGE_FILE_HEADER.Characteristics.
        /// Does nothing if the flag is already set.
        /// </summary>
        /// <param name="raw">Raw PE file bytes.</param>
        /// <param name="pe">Parsed PE metadata.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to IMAGE_OPTIONAL_HEADER.</param>
        /// <param name="sectionTableOffset">Offset to section headers.</param>
        /// <param name="rnd">Random number generator (unused).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            const ushort IMAGE_FILE_LARGE_ADDRESS_AWARE = 0x0020; // Flag to allow >2 GB address space on 64-bit

            int fileHeaderOffset = e_lfanew + 4, // Skip PE signature "PE\0\0"
                characteristicsOffset = fileHeaderOffset + 18; // Offset to Characteristics field

            // Check for bounds safety
            if (characteristicsOffset + 2 > raw.Length)
                throw new IndexOutOfRangeException("Characteristics field is outside of file bounds.");

            // Read current flags
            ushort current = BitConverter.ToUInt16(raw, characteristicsOffset);
            if ((current & IMAGE_FILE_LARGE_ADDRESS_AWARE) != 0)
                return;

            // Set flag and write back
            current |= IMAGE_FILE_LARGE_ADDRESS_AWARE;
            byte[] updated = BitConverter.GetBytes(current);
            raw[characteristicsOffset] = updated[0];
            raw[characteristicsOffset + 1] = updated[1];
        }
    }
}