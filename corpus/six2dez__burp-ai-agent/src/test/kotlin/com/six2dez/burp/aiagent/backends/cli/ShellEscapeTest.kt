package com.six2dez.burp.aiagent.backends.cli

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * Phase 26 SC1 / QUAL-06 — pins the quoting contract of [shellEscape] and the argv [buildPtyCommand]
 * hands to `sh -c`.
 *
 * The defect these tests exist for: [shellEscape] used to quote only when an argument contained
 * whitespace, a double quote or an apostrophe. `foo;id` and a command substitution contain none of
 * those, so they reached `/bin/sh -c` unquoted and the shell parsed them as syntax. A CLI command,
 * its extras and the agent profile are user- or settings-import-supplied, so that is a
 * settings-import-to-command-execution path.
 *
 * The fix inverts the test to an allowlist: an argument is passed through bare ONLY when every one
 * of its characters is an ASCII letter, an ASCII digit, or one of `.`, `_`, `/`, `-`. Everything
 * else is single-quoted.
 *
 * Two halves matter and both are asserted here:
 *  1. the per-argument return value of [shellEscape];
 *  2. the joined command string [buildPtyCommand] produces, because that string — not the
 *     per-argument value — is what the shell actually parses.
 *
 * No test here spawns a shell. The apostrophe round-trip asserts the exact expected escaped bytes
 * and states in a comment what a POSIX shell reads them back as; spawning `/bin/sh` would trade a
 * deterministic assertion for a subprocess dependency without adding evidence.
 */
class ShellEscapeTest {
    // ---- SC1: the two argument forms the defect let through ----

    @Test
    fun semicolonArgumentIsSingleQuoted() {
        val escaped = shellEscape("foo;id")
        assertTrue(
            escaped.startsWith("'") && escaped.endsWith("'"),
            "an argument containing ';' must be single-quoted or the shell reads it as a command separator, got: $escaped",
        )
        assertEquals("'foo;id'", escaped, "the semicolon must survive inside the quotes, not be stripped")
    }

    @Test
    fun commandSubstitutionArgumentIsSingleQuoted() {
        val escaped = shellEscape("\$(cmd)")
        assertTrue(
            escaped.startsWith("'") && escaped.endsWith("'"),
            "an argument containing a command substitution must be single-quoted, got: $escaped",
        )
        assertEquals("'\$(cmd)'", escaped, "the substitution text must survive inside the quotes verbatim")
    }

    // ---- SC1: the over-quoting guard. A fix that quotes everything breaks working CLI backends ----

    @Test
    fun plainFlagIsPassedThroughUnquoted() {
        assertEquals("--silent", shellEscape("--silent"), "a bare long flag must not gain quotes")
    }

    @Test
    fun absolutePathIsPassedThroughUnquoted() {
        assertEquals(
            "/usr/local/bin/claude",
            shellEscape("/usr/local/bin/claude"),
            "slashes are in the allowlist, so an absolute executable path must pass through byte-identical",
        )
    }

    @Test
    fun versionSuffixAndUnderscoreNameArePassedThroughUnquoted() {
        assertEquals("claude-3.5", shellEscape("claude-3.5"), "hyphen, digits and dot are all allowlisted")
        assertEquals("gemini_cli", shellEscape("gemini_cli"), "underscore is allowlisted")
    }

    // ---- SC1 edges ----

    @Test
    fun emptyArgumentBecomesTwoApostrophes() {
        assertEquals(
            "''",
            shellEscape(""),
            "an empty argument must become '' or it vanishes from the joined command line and argv arity changes",
        )
    }

    @Test
    fun embeddedApostropheUsesPosixQuoteEscape() {
        // A POSIX shell reads 'it'"'"'s' back as the single word: it's
        // (close single quote, double-quoted apostrophe, reopen single quote).
        assertEquals(
            "'it'\"'\"'s'",
            shellEscape("it's"),
            "an embedded apostrophe must close-escape-reopen or it terminates the quoting and starts a new shell word",
        )
    }

    @Test
    fun everyNonAllowlistedCharacterForcesQuoting() {
        val hostile =
            mapOf(
                "newline" to "a\nb",
                "backtick" to "a`b",
                "asterisk" to "a*b",
                "tilde" to "a~b",
                "dollar" to "a\$b",
                "pipe" to "a|b",
                "ampersand" to "a&b",
                "space" to "a b",
                "double quote" to "a\"b",
                // U+00E9 (LATIN SMALL LETTER E WITH ACUTE) is outside the ASCII allowlist and must be quoted.
                "non-ascii letter" to "café",
            )
        for ((label, value) in hostile) {
            val escaped = shellEscape(value)
            assertTrue(
                escaped.startsWith("'") && escaped.endsWith("'"),
                "an argument containing a $label is not in the allowlist and must be quoted, got: $escaped",
            )
        }
    }

    @Test
    fun allowlistCoversTheFullAsciiLetterAndDigitRange() {
        val allowlisted = ('a'..'z').joinToString("") + ('A'..'Z').joinToString("") + ('0'..'9').joinToString("")
        assertEquals(
            allowlisted,
            shellEscape(allowlisted),
            "every ASCII letter and digit is allowlisted, so a string of only those must pass through byte-identical",
        )
    }

    // ---- SC1 end to end: what the shell actually parses ----

    @Test
    fun ptyArgvOnMacOsCarriesTheSemicolonArgumentQuoted() {
        val argv = buildPtyCommand(listOf("claude", "-p", "foo;id"), "Mac OS X")
        assertEquals(
            listOf("script", "-q", "/dev/null", "/bin/sh", "-c"),
            argv.subList(0, 5),
            "the macOS pty shape is 'script -q /dev/null /bin/sh -c <command>'",
        )
        assertEquals(6, argv.size, "the joined command is one trailing argv element, got: $argv")
        assertEquals(
            "claude -p 'foo;id'",
            argv[5],
            "the string handed to sh -c must carry foo;id inside single quotes so the shell never sees the ';'",
        )
    }

    @Test
    fun ptyArgvOnLinuxCarriesTheSemicolonArgumentQuoted() {
        val argv = buildPtyCommand(listOf("claude", "-p", "foo;id"), "Linux")
        assertEquals(
            listOf("script", "-q", "-c", "claude -p 'foo;id'", "/dev/null"),
            argv,
            "the Linux pty shape is 'script -q -c <command> /dev/null' with the command quoted the same way",
        )
    }

    @Test
    fun ptyArgvLeavesAllowlistedArgumentsByteIdentical() {
        val argv = buildPtyCommand(listOf("/usr/local/bin/claude", "--silent", "claude-3.5"), "Mac OS X")
        assertEquals(
            "/usr/local/bin/claude --silent claude-3.5",
            argv[5],
            "a fully allowlisted argv must reach sh -c unquoted or every working CLI invocation changes shape",
        )
    }

    @Test
    fun ptyArgvKeepsAnEmptyArgumentAsAWord() {
        val argv = buildPtyCommand(listOf("claude", "-p", ""), "Mac OS X")
        assertEquals(
            "claude -p ''",
            argv[5],
            "an empty argument must stay a word in the joined command or the shell receives two arguments, not three",
        )
    }
}
