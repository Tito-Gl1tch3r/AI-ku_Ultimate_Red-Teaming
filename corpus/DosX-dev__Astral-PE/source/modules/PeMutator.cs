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

using Astral_PE.modules;
using AstralPE.Obfuscator.Modules;
using PeNet;

namespace AstralPE.Obfuscator {
    public class PeMutator {
        private byte[] raw;
        private readonly PeFile pe;
        private readonly Random rnd;

        private readonly int e_lfanew;
        private readonly int optStart;
        private readonly int sectionTableOffset;

        private readonly List<IAstralPeModule> modules = [];

        public static string SelectedFilePath { get; private set; } = string.Empty;
        public static bool LegacyWinCompatMode { get; private set; } = false;

        /// <summary>
        /// Initializes the PE obfuscator and computes important header offsets.
        /// </summary>
        /// <param name="raw">Raw byte array of the PE file.</param>
        /// <param name="pe">Parsed PE structure.</param>
        /// <param name="rnd">Random number generator instance.</param>
        public PeMutator(byte[] raw, PeFile pe, Random rnd, string _selectedFilePath, bool _legacyWinCompatMode) {
            SelectedFilePath = _selectedFilePath;
            LegacyWinCompatMode = _legacyWinCompatMode;

            this.raw = raw ?? throw new ArgumentNullException(nameof(raw));
            this.pe = pe ?? throw new ArgumentNullException(nameof(pe));
            this.rnd = rnd ?? throw new ArgumentNullException(nameof(rnd));

            if (pe.ImageDosHeader == null || pe.ImageNtHeaders == null || pe.ImageNtHeaders.FileHeader == null)
                throw new InvalidOperationException("Invalid PE structure: headers missing.");

            e_lfanew = (int)pe.ImageDosHeader.E_lfanew;
            optStart = e_lfanew + 0x18;
            sectionTableOffset = e_lfanew + 4 + 20 + pe.ImageNtHeaders.FileHeader.SizeOfOptionalHeader;

            RegisterModules();
        }

        /// <summary>
        /// Registers all mutation modules in the order they should be applied.
        /// </summary>
        private void RegisterModules() {
            IAstralPeModule[]? targetedObfuscationModules = [
                new FreePascalCompilerMutator(),
                new LegacyVbCompilerMutator(),
                new DelphiLazarusMutator(),
                new GoCompilerMutator(),
                new UpxPackerMutator()
            ];

            IAstralPeModule[]? standartObfuscationModules = [
                new LinkerVersionInfoWiper(),
                new LargeAddressAwareSetter(),
                new MemoryReserveExpander(),
                new MinimumOsVersionWiper(),
                new WinAuthSignStripper(),
                new OriginalNameWiper(),
                new EntryPointPatcher(),
                new PermissionsSetter(),
                new RichHeaderWiper(),
                new LoadConfigWiper(),
                new DosStubPatcher(),
                new DataDirCleaner(),
                new TimestampWiper(),
                new ChecksumWiper(),
                new ImportMutator(),
                new DebugStripper(),
                new RelocRemover(),
                new TlsCleaner(),
                new ExportFaker(),
                new SectionNameWiper() // Must be last
            ];

            foreach (IAstralPeModule? module in targetedObfuscationModules)
                modules.Add(module);

            foreach (IAstralPeModule? module in standartObfuscationModules)
                modules.Add(module);
        }

        /// <summary>
        /// Applies all registered transformations to the PE file.
        /// </summary>
        /// <returns>Mutated byte array of the PE file.</returns>
        public byte[] Apply() {
            if (pe.IsDotNet) {
                Logging.Write("/CLR(RED)[!] DotNET files are not supported in this version.");
                Environment.Exit(1);
            }

            foreach (IAstralPeModule? module in modules) {
                try {
                    module.Apply(ref raw, pe, e_lfanew, optStart, sectionTableOffset, rnd);
                } catch (Exception ex) {
                    Logging.Write($"/CLR(RED)[!] /CLR(GRAY)(SKIP)/CLR(RED) Module {module.GetType().Name} failed: {ex.Message}");
                }
            }

            return raw;
        }
    }
}
