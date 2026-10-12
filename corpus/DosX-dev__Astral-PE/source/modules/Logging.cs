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

namespace Astral_PE.modules {
    public static class Logging {
        // Lock object to ensure thread-safety during logging.
        private static readonly object _lock = new();

        /// <summary>
        /// Writes a colored message to the console.
        /// The message can include color tags in the format /CLR(COLOR_NAME)TEXT,
        /// where COLOR_NAME is a valid console color (e.g., RED, GREEN, BLUE, etc.).
        /// </summary>
        /// <param name="message">The message to write to the console with embedded color tags.</param>
        public static void Write(string message) {
            // Ensure thread-safety while logging by locking the critical section
            lock (_lock) {
                // Split the message into parts based on the color tag "/CLR("
                string[] parts = message.Split("/CLR(", StringSplitOptions.None);

                // Start with the default white color for text
                Console.ForegroundColor = ConsoleColor.White;
                Console.Write(parts[0]);

                // Process each part that follows a color tag
                for (int i = 1; i < parts.Length; i++) {
                    // Find the closing parenthesis of the color tag
                    int close = parts[i].IndexOf(')');
                    if (close > 0) {
                        // Extract the color name (before the closing parenthesis)
                        string colorName = parts[i][..close];
                        // Extract the text after the closing parenthesis
                        string text = parts[i][(close + 1)..];

                        // Try to parse the color name to a valid ConsoleColor
                        if (Enum.TryParse(colorName, true, out ConsoleColor color)) {
                            // Set the console text color
                            Console.ForegroundColor = color;
                        }
                        // Write the colored text to the console
                        Console.Write(text);
                    }
                }

                // Print a newline after the message
                Console.WriteLine();
                // Reset the console color back to the default color
                Console.ResetColor();
            }
        }
    }
}