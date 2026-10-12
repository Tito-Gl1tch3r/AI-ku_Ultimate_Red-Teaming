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
    public class WinAuthSignStripper : IAstralPeModule {

        /// <summary>
        /// Applies the overlay stripper to remove the overlay from the PE file if it matches the signature.
        /// The signature we are looking for is "00 02 02 00" (which is a common pattern found in some overlays).
        /// If this pattern is found at the start of the overlay, the overlay is removed.
        /// </summary>
        /// <param name="raw">The raw byte array of the PE file.</param>
        /// <param name="pe">The parsed PE file, used to access the section headers and overlay information.</param>
        /// <param name="e_lfanew">The offset to the IMAGE_NT_HEADERS in the PE file.</param>
        /// <param name="optStart">The offset to the Optional Header in the PE file.</param>
        /// <param name="sectionTableOffset">The offset to the section table in the PE file.</param>
        /// <param name="rnd">A random number generator (currently unused in this module, but required by the interface).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Validate section headers
            if (pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            // Calculate the offset to the overlay data (after the last section)
            uint overlayOffset = pe.ImageSectionHeaders.Max(s => s.PointerToRawData + s.SizeOfRawData);

            // Make sure overlayOffset is not beyond the file length
            if (overlayOffset >= raw.Length)
                return;

            // Calculate the length of the overlay and check if it's too short to contain the signature
            if (raw.Length - (int)overlayOffset < 8)
                return;

            // Bounds check before reading overlay signature
            if (overlayOffset + 8 > (uint)raw.Length)
                throw new ArgumentOutOfRangeException("Overlay offset exceeds file bounds.");

            // Check for specific PKI-like signature (used in signed overlays)
            if (raw[overlayOffset + 4] == 0x00 &&
                raw[overlayOffset + 5] == 0x02 &&
                raw[overlayOffset + 6] == 0x02 &&
                raw[overlayOffset + 7] == 0x00) {
                // Resize the original byte array to remove the overlay
                Array.Resize(ref raw, (int)overlayOffset);
            }
        }
    }
}
