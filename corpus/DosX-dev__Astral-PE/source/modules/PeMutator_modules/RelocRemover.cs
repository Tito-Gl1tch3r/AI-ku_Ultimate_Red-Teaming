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

namespace AstralPE.Obfuscator.Modules {
    public class RelocRemover : IAstralPeModule {

        /// <summary>
        /// Removes the relocation directory and section from the PE file if they are not needed.
        /// This operation is skipped for DLL and driver files.
        /// </summary>
        /// <param name="raw">The raw byte array of the PE file.</param>
        /// <param name="pe">The parsed PE file structure.</param>
        /// <param name="e_lfanew">The offset to the IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">The offset to the Optional Header.</param>
        /// <param name="sectionTableOffset">The offset to the section table.</param>
        /// <param name="rnd">Random generator, unused in this module.</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            if (pe.IsDll || pe.IsDriver)
                return;

            if (pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Locate relocation directory entry in the DataDirectory
            int relocDirOffset = optStart + 0x60 + 5 * 8;
            if (relocDirOffset + 8 > raw.Length)
                throw new ArgumentOutOfRangeException(nameof(relocDirOffset), "Relocation directory offset is outside file bounds.");

            uint relocRva = BitConverter.ToUInt32(raw, relocDirOffset),
                 relocSize = BitConverter.ToUInt32(raw, relocDirOffset + 4);

            // Skip if relocation directory is already empty
            if (relocRva == 0 || relocSize == 0)
                return;

            // Find the .reloc section
            ImageSectionHeader? relocSection = pe.ImageSectionHeaders.FirstOrDefault(s =>
                s.Name?.Trim('\0').Equals(".reloc", StringComparison.OrdinalIgnoreCase) == true);

            if (relocSection == null)
                return;

            int offset = (int)relocSection.PointerToRawData,
                size = (int)relocSection.SizeOfRawData;

            if (offset <= 0 || offset + size > raw.Length)
                throw new ArgumentOutOfRangeException(nameof(offset), "Relocation section is outside file bounds.");

            // Ensure that the RVA in the directory entry lies within the .reloc section
            if (relocRva < relocSection.VirtualAddress || relocRva >= relocSection.VirtualAddress + relocSection.VirtualSize)
                return;

            // Clear the raw relocation data and the directory entry
            Array.Clear(raw, offset, size);
            Array.Clear(raw, relocDirOffset, 8);

            // Set IMAGE_FILE_RELOCS_STRIPPED flag in FileHeader.Characteristics
            const ushort IMAGE_FILE_RELOCS_STRIPPED = 0x0001;

            int fileHeaderOffset = e_lfanew + 4, // Skip PE signature
                characteristicsOffset = fileHeaderOffset + 18; // Offset to Characteristics field

            if (characteristicsOffset + 2 <= raw.Length) {
                ushort current = BitConverter.ToUInt16(raw, characteristicsOffset);
                current |= IMAGE_FILE_RELOCS_STRIPPED;

                byte[] updated = BitConverter.GetBytes(current);
                raw[characteristicsOffset] = updated[0];
                raw[characteristicsOffset + 1] = updated[1];
            }
        }
    }
}