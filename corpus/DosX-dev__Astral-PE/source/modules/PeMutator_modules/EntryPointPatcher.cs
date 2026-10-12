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
    public class EntryPointPatcher : IAstralPeModule {

        /// <summary>
        /// Patches the entry point in the PE file.
        /// </summary>
        /// <param name="raw">The raw byte array of the PE file.</param>
        /// <param name="pe">The parsed PE file.</param>
        /// <param name="e_lfanew">Offset to IMAGE_NT_HEADERS.</param>
        /// <param name="optStart">Start offset of the Optional Header.</param>
        /// <param name="sectionTableOffset">Offset to the section table.</param>
        /// <param name="rnd">Random number generator to shuffle bytes (used in the second patch).</param>
        public void Apply(ref byte[] raw, PeFile pe, int e_lfanew, int optStart, int sectionTableOffset, Random rnd) {
            // Ensure the PE file is valid
            if (pe.ImageNtHeaders == null || pe.ImageSectionHeaders == null)
                throw new InvalidPeImageException();

            uint epRva = pe.ImageNtHeaders.OptionalHeader.AddressOfEntryPoint,
                 epOffset = epRva.RvaToOffset(pe.ImageSectionHeaders);

            if (epOffset >= raw.Length)
                throw new Exception("EntryPoint offset is out of file bounds.");

            List<byte> oneByteInstructions = pe.Is64Bit ? new List<byte> {
                // PUSH rAX–rDI (0x50–0x57), without 0x54 (PUSH rSP)
                0x50, 0x51, 0x52, 0x53, 0x55, 0x56, 0x57,

                // Other x64-safe oneByteInstructions
                0x90, // NOP
                0xF8, // CLC
                0xF9, // STC
                0xFC, // CLD
            } : new List<byte> {
                // PUSH rAX–rDI (0x50–0x57), without 0x54 (PUSH rSP)
                0x50, 0x51, 0x52, 0x53, 0x55, 0x56, 0x57,

                // INC rAX–rDI (0x40–0x47), without 0x44 (INC rSP)
                0x40, 0x41, 0x42, 0x43, 0x45, 0x46, 0x47,

                // DEC rAX–rDI (0x48–0x4F), without 0x4C (DEC rSP)
                0x48, 0x49, 0x4A, 0x4B, 0x4D, 0x4E, 0x4F,

                // Legacy single-byte x86 oneByteInstructions
                0x90, // NOP
                0xF8, // CLC
                0xF9, // STC
                0xFC, // CLD
                0x27, // DAA
                0x2F, // DAS
                0x3F, // AAS
                0x61, // POPAD
                0x9C, // PUSHFD
                0x2E, // CS
                0x36, // SS
                0x3E, // DS
                0x26, // ES
            };

            // Randomly patch or remove 0x60 (PUSHAD/PUSHAL)
            if (raw[epOffset] == 0x60) {
                if (rnd.Next(2) == 0) { // Remove
                    raw[epOffset] = 0xCC;
                    epOffset++;
                } else { // Patch
                    raw[epOffset] = oneByteInstructions[rnd.Next(oneByteInstructions.Count)];
                }
            }

            // Shuffle PUSH oneByteInstructions in UPX64 signature
            if (epOffset + 4 < raw.Length &&
                raw[epOffset + 0] == 0x53 && raw[epOffset + 1] == 0x56 &&
                raw[epOffset + 2] == 0x57 && raw[epOffset + 3] == 0x55) {

                byte[] pushes = { 0x53, 0x56,
                                  0x57, 0x55 };

                for (int i = pushes.Length - 1; i > 0; i--) {
                    int j = rnd.Next(i + 1);
                    (pushes[i], pushes[j]) = (pushes[j], pushes[i]);
                }

                for (int i = 0; i < pushes.Length; i++)
                    raw[epOffset + i] = pushes[i];
            }

            // Go-style JMP obfuscation (JMP + INT3 padding)
            if (raw[epOffset] == 0xE9) {
                uint i = epOffset + 5;
                while (i < raw.Length && raw[i] == 0xCC) {
                    raw[i] = (byte)rnd.Next(0x00, 0xFF);
                    i++;
                }
            }

            // Randomly patch or remove 0x55 (push ebx) for TCC
            if (raw[epOffset] == 0x55 && raw[epOffset + 1] == 0x89 && raw[epOffset + 3] == 0x81) {
                if (rnd.Next(2) == 0) { // Remove
                    raw[epOffset] = 0xCC;
                    epOffset++;
                } else { // Patch
                    raw[epOffset] = oneByteInstructions[rnd.Next(oneByteInstructions.Count)];
                }
            }

            bool isVcStyle = false,
                 isMinGwStyle = false;

            // VC++ or MinGW EP stack alignment mutation + NOP/trap sequence replacement
            if (pe.Is64Bit && epOffset + 32 < raw.Length) {
                // Check if entry point starts with VC++-style prologue:
                // sub rsp, imm8; call; add rsp, imm8
                isVcStyle =
                    raw[epOffset + 0] == 0x48 && raw[epOffset + 1] == 0x83 && raw[epOffset + 2] == 0xEC &&
                    raw[epOffset + 4] == 0xE8 &&
                    raw[epOffset + 9] == 0x48 && raw[epOffset + 10] == 0x83 && raw[epOffset + 11] == 0xC4;

                // Check if entry point starts with MinGW-style prologue:
                // sub rsp, imm8; mov rax, [rip+...]
                isMinGwStyle =
                    raw[epOffset + 0] == 0x48 && raw[epOffset + 1] == 0x83 && raw[epOffset + 2] == 0xEC &&
                    raw[epOffset + 4] == 0x48 && raw[epOffset + 5] == 0x8B && raw[epOffset + 6] == 0x05;

                // Proceed only if one of the patterns matched
                if (isVcStyle || isMinGwStyle) {
                    // // Nop mutation for MinGW
                    if (isMinGwStyle) {
                        for (uint i = epOffset + 12; i < epOffset + 32 && i + 2 < raw.Length; i++) {
                            if (raw[i] == 0x90 && raw[i + 1] == 0x90 && raw[i + 2] == 0x90) {
                                int variant = rnd.Next(4);

                                switch (variant) {
                                    case 0: raw[i] = 0x0F; raw[i + 1] = 0x1F; raw[i + 2] = 0x00; break;
                                    case 1: raw[i] = 0x66; raw[i + 1] = 0x90; raw[i + 2] = 0x90; break;
                                    case 2: raw[i] = 0x90; raw[i + 1] = 0x66; raw[i + 2] = 0x90; break;
                                    case 3: break; // leave 90 90 90 as-is
                                }

                                break;
                            }
                        }
                    }

                    // Dead bytes garbage after JMP for VC++
                    if (isVcStyle &&
                        raw[epOffset + 13] == 0xE9 && // jmp
                        raw[epOffset + 18] == 0xCC && raw[epOffset + 19] == 0xCC) { // 2x int3
                        Span<byte> garbage = stackalloc byte[2];
                        rnd.NextBytes(garbage);

                        raw[epOffset + 18] = garbage[0]; // first int3
                        raw[epOffset + 19] = garbage[1]; // second int3
                    }
                }
            }

            // 1. If free space is available, inject a short obfuscation sequence
            // 2. If not -> slide over known NOP pattern
            // 3. If not -> mutate entrypoint stack alignment

            // EntryPoint shift mutation w/ multi-level obfuscation (5/2/1-byte options)
            if (epOffset >= 1) {
                int space = 0;

                if (epOffset >= 1 &&
                    (raw[epOffset - 5] != 0xE9)) { // Skip Microsoft VC++ 19.35.32217 debug builds by checking for CALL opcode
                    byte fill = raw[epOffset - 1];

                    if (fill == 0x00 || fill == 0x90 || fill == 0xCC) {
                        for (int i = 1; i <= Math.Min(5, epOffset); i++) {
                            if (raw[epOffset - i] == fill)
                                space++;
                            else
                                break;
                        }
                    }
                }

                if (space >= 5) {

                    List<byte> regVariants = new() {
                        0xC0, // EAX
                        0xC9, // ECX
                        0xD2, // EDX
                        0xDB, // EBX
                        0xED, // EBP
                        0xF6, // ESI
                        0xFF  // EDI
                    };

                    byte reg = regVariants[rnd.Next(regVariants.Count)];

                    int junkCount = Math.Min(space - 2, 2), // max 2 bytes of junk (safe, can be changed)
                        totalSize = 2 + 2 + junkCount, // xor + jz + junk
                        breakerOffset = (int)epOffset - totalSize;

                    raw[breakerOffset + 0] = 0x31;     // xor
                    raw[breakerOffset + 1] = reg;      // rax/rcx/.../esi/edi
                    raw[breakerOffset + 2] = 0x74;     // jz
                    raw[breakerOffset + 3] = (byte)junkCount;

                    for (int i = 0; i < junkCount; i++)
                        raw[breakerOffset + 4 + i] = (byte)rnd.Next(0x00, 0xFF);

                    epOffset -= (uint)totalSize;

                } else if (space >= 3) {
                    // Inject universal 2-byte garbage op
                    List<byte[]> epGarbage = [
                        [0x0F, 0xA2], // cpuid
                        [0x0F, 0x31], // rdtsc
                        [0x66, 0x90], // nop (xchg ax, ax)
                        [0x84, 0xC0], // test al, al
                        [0x85, 0xC0], // test eax, eax
                        [0x09, 0xC0], // or eax, eax
                        [0x33, 0xC0], // xor eax, eax
                        [0x33, 0xC9], // xor ecx, ecx
                        [0x33, 0xD2], // xor edx, edx
                        [0x33, 0xDB], // xor ebx, ebx
                        [0x33, 0xF6], // xor esi, esi
                        [0x33, 0xFF], // xor edi, edi
                        [0xFC, 0x90], // cld; nop
                        [0xF8, 0x90], // clc; nop
                        [0xF9, 0x90], // stc; nop
                        [0x90, 0xFC], // nop; cld
                        [0x90, 0xF8], // nop; clc
                        [0x90, 0xF9] // nop; stc
                    ];

                    byte[] instr = epGarbage[rnd.Next(epGarbage.Count)];
                    raw[epOffset - 2] = instr[0];
                    raw[epOffset - 1] = instr[1];
                    epOffset -= 2;
                } else { // If no free space

                    // Try to slide EntryPoint over known safe oneByteInstructions
                    byte[][] knownSafeOps = [
                        // 1. No operations
                        [0x66, 0x0F, 0x1F, 0x84, 0x00, 0x00, 0x00, 0x00, 0x00], // nop dword ptr [rax + rax*1 + 0x0]
                        [0x0F, 0x1F, 0x84, 0x00, 0x00, 0x00, 0x00, 0x00],       // nop dword ptr [rax + rax*1 + 0x0]
                        [0x0F, 0x1F, 0x80, 0x00, 0x00, 0x00, 0x00],             // nop dword ptr [rax + 0x0]
                        [0x66, 0x0F, 0x1F, 0x44, 0x00, 0x00],                   // nop word ptr [rax + rax*1 + 0x0]
                        [0x0F, 0x1F, 0x44, 0x00, 0x00],                         // nop dword ptr [rax + 0x0]
                        [0x0F, 0x1F, 0x40, 0x00],                               // nop dword ptr [rax + 0x0]
                        [0x0F, 0x1F, 0x00],                                     // nop dword ptr [rax]
                        [0x66, 0x90],                                           // xchg ax, ax
                        [0x90],                                                 // nop

                        // 2. Fake operations
                        [0x8D, 0x1C, 0x00],  [0x8D, 0x40, 0x00],                // lea ebx, [eax + eax];  lea eax, [eax]
                        [0x8D, 0x48, 0x00],  [0x8D, 0x50, 0x00],                // lea ecx, [eax];        lea edx, [eax]
                        [0x31, 0xC0],        [0x31, 0xC9],                      // xor eax, eax;          xor ecx, ecx
                        [0x31, 0xD2],        [0x31, 0xDB],                      // xor edx, edx;          xor ebx, ebx
                        [0x29, 0xC0],        [0x29, 0xC9],                      // sub eax, eax;          sub ecx, ecx
                        [0x89, 0xC0],        [0x89, 0xD2],                      // mov eax, eax;          mov edx, edx
                        [0x89, 0xDB],        [0x85, 0xC0],                      // mov ebx, ebx;          test eax, eax
                        [0x84, 0xC0],        [0x09, 0xC0],                      // test al, al;           or eax, eax
                        [0x33, 0xC0],        [0x33, 0xC9],                      // xor eax, eax;          xor ecx, ecx
                        [0x33, 0xD2],        [0x33, 0xDB],                      // xor edx, edx;          xor ebx, ebx
                        [0x33, 0xF6],        [0x33, 0xFF],                      // xor esi, esi;          xor edi, edi
                        [0x87, 0xD1],        [0x87, 0xDB],                      // xchg edx, ecx;         xchg ebx, ebx
                        [0x87, 0xC0],        [0x21, 0xC0],                      // xchg eax, eax;         and eax, eax
                        [0x0F, 0xA2],        [0x0F, 0x31],                      // cpuid;                 rdtsc
                        [0x50],              [0x51],                            // push eax;              push ecx
                        [0x52],              [0x53],                            // push edx;              push ebx
                        [0x55],              [0x58],                            // push ebp;              pop eax
                        [0x59],              [0x5A],                            // pop ecx;               pop edx
                        [0x5B],              [0x5D],                            // pop ebx;               pop ebp
                        [0x9C],              [0x9D],                            // pushfd;                popfd
                        [0xFC],              [0xF8],                            // cld;                   clc
                        [0xF9]                                                  // stc
                    ];

                    bool shifted = false,
                         foundAny;

                    do {
                        foundAny = false;

                        foreach (var nop in knownSafeOps) {
                            int instructionLength = nop.Length;
                            if (epOffset >= instructionLength) {
                                bool match = true;
                                for (int i = 0; i < instructionLength; i++) {
                                    if (raw[epOffset - instructionLength + i] != nop[i]) {
                                        match = false;
                                        break;
                                    }
                                }

                                if (match) {
                                    epOffset -= (uint)instructionLength;
                                    foundAny = true;
                                    shifted = true;
                                    break; // start again from new offset
                                }
                            }
                        }

                    } while (foundAny);

                    // If not slid over NOPs, try mutating entrypoint stack alignment
                    if (!shifted && (isMinGwStyle || isVcStyle)) {
                        byte originalStackVal = raw[epOffset + 3];
                        List<byte> stackVariants = new() { 0x38, 0x48, 0x58 };
                        stackVariants.Remove(originalStackVal);
                        byte newStackVal = stackVariants[rnd.Next(stackVariants.Count)];

                        raw[epOffset + 3] = newStackVal;

                        if (isVcStyle) {
                            raw[epOffset + 12] = newStackVal;
                        } else if (isMinGwStyle) {
                            for (uint i = epOffset + 7; i < epOffset + 32 && i + 4 < raw.Length; i++) {
                                if (raw[i] == 0x48 && raw[i + 1] == 0x83 && raw[i + 2] == 0xC4 &&
                                    raw[i + 3] == originalStackVal && raw[i + 4] == 0xC3) {
                                    raw[i + 3] = newStackVal;
                                    break;
                                }
                            }
                        }
                    }
                }

                uint newEpRva = epOffset.OffsetToRva(pe.ImageSectionHeaders);
                pe.ImageNtHeaders.OptionalHeader.AddressOfEntryPoint = newEpRva;
                BitConverter.GetBytes(newEpRva).CopyTo(raw, optStart + 0x10);
            }
        }
    }
}
