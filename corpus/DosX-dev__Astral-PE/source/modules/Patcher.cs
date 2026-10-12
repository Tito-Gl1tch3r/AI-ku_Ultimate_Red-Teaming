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

using PeNet.Header.Pe;
using System.Collections.Concurrent;

namespace AstralPE.Obfuscator.Modules {
    public static class Patcher {

        /// <summary>
        /// Replaces all occurrences of a byte sequence in the entire buffer using parallel search.
        /// </summary>
        /// <param name="data">The buffer to search and replace in.</param>
        /// <param name="find">The byte sequence to find.</param>
        /// <param name="replace">The byte sequence to replace with.</param>
        public static void ReplaceBytes(byte[] data, byte[] find, byte[] replace) {
            if (find.Length == 0 || replace.Length == 0 || data.Length < find.Length)
                return;

            int len = find.Length,
                limit = data.Length - len;

            ConcurrentBag<int> matches = [];

            Parallel.ForEach(Partitioner.Create(0, limit, 8192), range => {
                for (int i = range.Item1; i < range.Item2; i++) {
                    bool match = true;
                    for (int j = 0; j < len; j++) {
                        if (data[i + j] != find[j]) {
                            match = false;
                            break;
                        }
                    }
                    if (match)
                        matches.Add(i);
                }
            });

            foreach (int index in matches.OrderBy(i => i)) {
                Buffer.BlockCopy(replace, 0, data, index, Math.Min(replace.Length, len));
            }
        }

        /// <summary>
        /// Finds the first occurrence of a byte pattern in the buffer.
        /// </summary>
        /// <param name="haystack">The buffer to search in.</param>
        /// <param name="needle">The byte pattern to find.</param>
        /// <returns>The index of the first occurrence of the pattern, or -1 if not found.</returns>
        public static int IndexOf(byte[] haystack, byte[] needle) {
            return IndexOf(haystack, needle, 0);
        }

        /// <summary>
        /// Finds the first occurrence of a byte pattern in the buffer starting at the specified index.
        /// </summary>
        /// <param name="haystack">The buffer to search in.</param>
        /// <param name="needle">The byte pattern to find.</param>
        /// <param name="startIndex">The index to start searching from.</param>
        public static int IndexOf(byte[] haystack, byte[] needle, int startIndex) {
            if (needle == null || needle.Length == 0 || haystack.Length < needle.Length || startIndex < 0)
                return -1;

            int len = needle.Length,
                limit = haystack.Length - len,
                result = -1;

            Parallel.ForEach(Partitioner.Create(startIndex, limit + 1, 8192), (range, state) => {
                for (int i = range.Item1; i < range.Item2; i++) {
                    bool match = true;
                    for (int j = 0; j < len; j++) {
                        if (haystack[i + j] != needle[j]) {
                            match = false;
                            break;
                        }
                    }
                    if (match) {
                        Interlocked.CompareExchange(ref result, i, -1);
                        state.Stop();
                        return;
                    }
                }
            });

            return result;
        }

        /// <summary>
        /// Converts a file offset to a relative virtual address (RVA).
        /// </summary>
        /// <param name="offset">The file offset to convert.</param>
        /// <param name="sections">The array of section headers to use for conversion.</param>
        public static uint OffsetToRva(uint offset, ImageSectionHeader[] sections) {
            if (sections == null || sections.Length == 0)
                throw new ArgumentException("Section headers are missing.");

            foreach (var sec in sections) {
                if (offset >= sec.PointerToRawData && offset < sec.PointerToRawData + sec.SizeOfRawData)
                    return sec.VirtualAddress + (offset - sec.PointerToRawData);
            }

            return 0;
        }

        /// <summary>
        /// Converts a relative virtual address (RVA) to a file offset.
        /// </summary>
        /// <param name="rva">The RVA to convert.</param>
        /// <param name="sections">The array of section headers to use for conversion.</param>
        public static uint RvaToOffset(uint rva, ImageSectionHeader[] sections) {
            foreach (var section in sections) {
                if (rva >= section.VirtualAddress && rva < section.VirtualAddress + section.VirtualSize)
                    return section.PointerToRawData + (rva - section.VirtualAddress);
            }

            return 0;
        }
    }
}