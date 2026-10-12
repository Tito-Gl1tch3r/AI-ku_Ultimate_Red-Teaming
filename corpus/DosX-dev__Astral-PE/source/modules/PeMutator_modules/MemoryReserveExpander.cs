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
    public class MemoryReserveExpander : IAstralPeModule {

        /// <summary>
        /// Sets SizeOfStackReserve and SizeOfHeapReserve to elevated defaults
        /// if current values are below recommended thresholds.
        /// </summary>
        /// <param name="raw">Raw PE file bytes.</param>
        /// <param name="pe">Parsed PE metadata.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Offset to IMAGE_OPTIONAL_HEADER.</param>
        /// <param name="sectionTableOffset">Offset to section headers.</param>
        /// <param name="rnd">Random number generator (unused).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            const uint STACK_RESERVE = 0x02000000, // 32 MB
                       HEAP_RESERVE = 0x04000000; // 64 MB

            bool is64 = pe.Is64Bit;

            int stackReserveOffset = is64 ? optStart + 0x48 : optStart + 0x40,
                heapReserveOffset = is64 ? optStart + 0x58 : optStart + 0x50;

            if (stackReserveOffset + (is64 ? 8 : 4) > raw.Length || heapReserveOffset + (is64 ? 8 : 4) > raw.Length)
                throw new IndexOutOfRangeException("Stack or heap reserve field is outside of file bounds.");

            // Stack reserve
            if (stackReserveOffset + (is64 ? 8 : 4) <= raw.Length) {
                ulong current = is64 ? BitConverter.ToUInt64(raw, stackReserveOffset) : BitConverter.ToUInt32(raw, stackReserveOffset);
                if (current < STACK_RESERVE) {
                    byte[] updated = is64 ? BitConverter.GetBytes((ulong)STACK_RESERVE) : BitConverter.GetBytes(STACK_RESERVE);
                    Buffer.BlockCopy(updated, 0, raw, stackReserveOffset, updated.Length);
                }
            }

            // Heap reserve
            if (heapReserveOffset + (is64 ? 8 : 4) <= raw.Length) {
                ulong current = is64 ? BitConverter.ToUInt64(raw, heapReserveOffset) : BitConverter.ToUInt32(raw, heapReserveOffset);
                if (current < HEAP_RESERVE) {
                    byte[] updated = is64 ? BitConverter.GetBytes((ulong)HEAP_RESERVE) : BitConverter.GetBytes(HEAP_RESERVE);
                    Buffer.BlockCopy(updated, 0, raw, heapReserveOffset, updated.Length);
                }
            }
        }
    }
}
