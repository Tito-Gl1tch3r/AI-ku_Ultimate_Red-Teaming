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
    public class DosStubPatcher : IAstralPeModule {

        /// <summary>
        /// Patches the DOS stub of the PE file:
        /// <list type="bullet">
        /// <item>Replaces the DOS header with the "MZ" signature.</item>
        /// <item>Zeroes out the data between the "MZ" signature and the NT headers.</item>
        /// <item>Sets the e_lfanew field to indicate the location of the IMAGE_NT_HEADERS.</item>
        /// </list>
        /// </summary>
        /// <param name="raw">The raw byte array representing the PE file.</param>
        /// <param name="pe">The parsed PE file object containing the IMAGE_DOS_HEADER and IMAGE_NT_HEADERS.</param>
        /// <param name="e_lfanew">The offset to the IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">The start offset of the Optional Header.</param>
        /// <param name="sectionTableOffset">The offset to the section table.</param>
        /// <param name="rnd">Random number generator (not used in this method).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Validate e_lfanew to ensure it's within bounds of the buffer
            if (e_lfanew <= 0 || e_lfanew + 4 > raw.Length)
                throw new Exception("e_lfanew points outside the bounds of the file. DOS stub patching aborted.");

            // Set the "MZ" signature at the beginning of the DOS header
            raw[0] = (byte)'M';
            raw[1] = (byte)'Z';

            // Clear the region between "MZ" and the NT headers (pointed to by e_lfanew)
            for (int i = 2; i < e_lfanew; i++)
                raw[i] = 0;

            // Write the e_lfanew value at the offset 0x3C in the DOS header
            BitConverter.GetBytes(e_lfanew).CopyTo(raw, 0x3C);
        }
    }
}
