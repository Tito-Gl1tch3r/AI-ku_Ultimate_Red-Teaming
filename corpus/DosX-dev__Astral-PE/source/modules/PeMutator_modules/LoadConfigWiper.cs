/*
 * This file is part of the Astral-PE project.
 * Copyright (c) 2025 DosX. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the “Software”), to deal
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
    public class LoadConfigWiper : IAstralPeModule {

        /// <summary>
        /// Applies the logic to wipe the Load Config Directory if safe.
        /// </summary>
        /// <param name="raw">Raw byte buffer of the PE file.</param>
        /// <param name="pe">Parsed PE file structure from PeNet.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to IMAGE_OPTIONAL_HEADER.</param>
        /// <param name="sectionTableOffset">Offset to section table.</param>
        /// <param name="rnd">Random generator (unused).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Verify header structures are present
            if (pe.ImageNtHeaders == null || pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Locate Load Config Directory
            ImageDataDirectory? loadCfg = pe.ImageNtHeaders.OptionalHeader.DataDirectory[(int)DataDirectoryType.LoadConfig];
            if (loadCfg.VirtualAddress == 0 || loadCfg.Size == 0)
                return;

            // Translate RVA to raw file offset
            uint rva = loadCfg.VirtualAddress,  
                 offset = rva.RvaToOffset(pe.ImageSectionHeaders);

            if (offset == 0 || offset + loadCfg.Size > raw.Length)
                throw new Exception("Load Config Directory points outside of file bounds.");

            // Check GuardFlags to see if CFG is enabled
            if (loadCfg.Size >= 0x48) {
                uint guardFlags = BitConverter.ToUInt32(raw, (int)(offset + 0x40));
                if ((guardFlags & 0x100) != 0) // IMAGE_GUARD_CF
                    throw new Exception("CFG (Control Flow Guard) is enabled. Skipping Load Config wipe.");
            }

            // Clear the Load Config Directory data
            Array.Clear(raw, (int)offset, (int)loadCfg.Size);

            // Clear the DataDirectory entry
            int dataDirOffset = optStart + 0x60 + ((int)DataDirectoryType.LoadConfig * 8);
            if (dataDirOffset + 8 > raw.Length)
                throw new IndexOutOfRangeException("DataDirectory offset is outside of file bounds.");

            Array.Clear(raw, dataDirOffset, 8);
        }
    }
}
