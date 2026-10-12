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
using AstralPE.Obfuscator;
using PeNet;
using System.Diagnostics;
using System.Reflection;

namespace AstralPE {
    /// <summary>
    /// The main entry point for the AstralPE obfuscation tool.
    /// Handles command-line arguments, performs obfuscation, and saves the modified PE file.
    /// </summary>
    class Program {
        // Initialize the random number generator for any random operations.
        private readonly static Random rnd = new();

        /// <summary>
        /// Main method of the application. It handles command-line input, performs obfuscation,
        /// and saves the resulting obfuscated PE file.
        /// </summary>
        /// <param name="args">The command-line arguments passed to the application.</param>
        static void Main(string[] args) {
            Logging.Write("/CLR(WHITE)\n" +
                " █████╗  ███████╗████████╗██████╗  █████╗ ██╗/CLR(DARKGRAY)        ██████╗ ███████╗/CLR(WHITE)\n" +
                " ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║/CLR(DARKGRAY)        ██╔══██╗██╔════╝/CLR(WHITE)\n" +
                " ███████║███████╗   ██║   ██████╔╝███████║██║/CLR(DARKGRAY) █████╗ ██████╔╝█████╗  /CLR(WHITE)\n" +
                " ██╔══██║╚════██║   ██║   ██╔══██╗██╔══██║██║/CLR(DARKGRAY) ╚════╝ ██╔═══╝ ██╔══╝  /CLR(WHITE)\n" +
                " ██║  ██║███████║   ██║   ██║  ██║██║  ██║███████╗/CLR(DARKGRAY)   ██║     ███████╗/CLR(WHITE)\n" +
                " ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝/CLR(DARKGRAY)   ╚═╝     ╚══════╝/CLR(WHITE)\n" +
                "  /CLR(GRAY)Advanced utility for mutation (shallow obfuscation) of PE files.\n" +
                "          GitHub: /CLR(BLUE)https://github.com/DosX-dev/Astral-PE/CLR(WHITE)\n");


            if (args.Length == 0) {
                ShowUsage();
                return;
            }

            bool legacyWinCompatMode = false;
            string? inputPath = null, outputPath = null;

            // Parse command-line arguments.
            for (int i = 0; i < args.Length; i++) {
                string arg = args[i];

                if (arg == "-h" || arg == "--help") {
                    ShowUsage();
                    return;
                } else if (arg == "-v" || arg == "--version") {
                    string? version = typeof(Program).Assembly
                        .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?
                        .InformationalVersion;

                    if (version != null) {
                        version = "v" + version;
                    } else {
                        version = "Unknown";
                    }

                    Logging.Write("/CLR(CYAN)[@] /CLR(WHITE)Current version is: " + version);
                    return;
                } else if (arg == "-l" || arg == "--legacy-win-compat-mode") {
                    legacyWinCompatMode = true;
                } else if (arg == "-o" || arg == "--output") {
                    if (i + 1 < args.Length)
                        outputPath = args[++i];
                } else if (arg.StartsWith("-")) {
                    Logging.Write("/CLR(DARKGRAY)[?] Specified flag /CLR(GRAY)" + arg + "/CLR(DARKGRAY) is not valid.");
                } else if (inputPath == null) {
                    inputPath = arg;
                }
            }

            if (inputPath == null) {
                Logging.Write("/CLR(RED)[!] No input file specified.");
                return;
            }

            if (!File.Exists(inputPath)) {
                Logging.Write("/CLR(RED)[!] File not found:/CLR(WHITE) " + inputPath);
                return;
            }

            if (string.IsNullOrWhiteSpace(outputPath)) {
                outputPath = Path.Combine(
                    Path.GetDirectoryName(inputPath) ?? "",
                    Path.GetFileNameWithoutExtension(inputPath) + "_ast" + Path.GetExtension(inputPath)
                );
            }

            try {
                // Read the raw bytes from the input file.
                byte[] raw = File.ReadAllBytes(inputPath);

                // Create a PeFile object for PE file parsing and manipulation.
                PeFile pe = new(raw);

                // Log the start of the obfuscation process.
                Logging.Write("/CLR(CYAN)[@] /CLR(WHITE)Obfuscating: /CLR(GRAY)" + inputPath);

                if (legacyWinCompatMode) {
                    Logging.Write("/CLR(DARKYELLOW)[!] Compatibility mode with older versions of Windows is enabled.\n    /CLR(RED)Obfuscation will be less effective!/CLR(DARKYELLOW) Keep this in mind.");
                }

                // Create a PeMutator instance and apply obfuscation.
                PeMutator? obfuscator = new(raw, pe, rnd, inputPath, legacyWinCompatMode);
                raw = obfuscator.Apply();

                try {
                    // Write the obfuscated data to the output file.
                    File.WriteAllBytes(outputPath, raw);

                    using (var fs = new FileStream(outputPath, FileMode.Append, FileAccess.Write))
                        fs.WriteByte(0x00);

                    Logging.Write("/CLR(GREEN)[+] /CLR(WHITE)Saved as: /CLR(GRAY)" + outputPath);
                } catch (Exception ex) {
                    Logging.Write("/CLR(RED)[!] Failed to save the obfuscated file: " + ex.Message);
                }
            } catch (Exception ex) {
                Logging.Write("/CLR(RED)[!] An error occurred during obfuscation: " + ex.Message);
            }
        }

        /// <summary>
        /// Displays the usage information for the tool.
        /// </summary>
        static void ShowUsage() {
            Logging.Write("/CLR(CYAN)" +
                          "[?] /CLR(WHITE)Usage: /CLR(YELLOW)<file.exe|dll> [-o|--output <output.exe|dll>] /CLR(DARKGRAY)" + "-> Specify output path\n" +
                          "                          /CLR(YELLOW)[-l|--legacy-win-compat-mode]  /CLR(DARKGRAY)" + "-> Compatibility with Windows 7+\n" +
                          "                          /CLR(DARKYELLOW)[-v|--version]                 /CLR(DARKGRAY)" +  "-> Show product version");
        }
    }
}
