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
    public class ChecksumWiper : IAstralPeModule {

        /// <summary>
        /// Overwrites the 4-byte CheckSum field (offset +0x40) in the optional header with zero, if it is non-zero.
        /// </summary>
        /// <param name="raw">The raw byte buffer of the PE file.</param>
        /// <param name="pe">The parsed PE file structure.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to Optional Header.</param>
        /// <param name="sectionTableOffset">Offset to section headers.</param>
        /// <param name="rnd">Random instance (unused).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Sanity check to ensure header structures are available
            if (pe.ImageNtHeaders == null || pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Calculate offset to CheckSum field (offset +0x40 in optional header)
            int checksumOffset = optStart + 0x40;

            // Bounds check
            if (checksumOffset + 4 > raw.Length)
                throw new ArgumentOutOfRangeException(nameof(raw), "Checksum offset exceeds buffer length.");

            // If checksum is already zero, skip
            if (pe.ImageNtHeaders.OptionalHeader.CheckSum == 0)
                return;

            // Clear the 4-byte CheckSum field
            BitConverter.GetBytes(0u).CopyTo(raw, checksumOffset);
        }
    }
}