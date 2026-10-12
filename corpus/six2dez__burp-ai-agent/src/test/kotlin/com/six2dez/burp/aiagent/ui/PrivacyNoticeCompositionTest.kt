package com.six2dez.burp.aiagent.ui

import com.six2dez.burp.aiagent.redact.PrivacyMode
import com.six2dez.burp.aiagent.ui.components.SubtleNotice
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

// The two halves of the shared OFF clause. Asserted as substrings, never as whole HTML messages:
// a full-string assertion would turn every future copy edit into a test failure and would end up
// maintained by pasting rather than by thinking.
private const val RAW_TRAFFIC_CLAUSE = "raw traffic may reach MCP and prompts"
private const val CUSTOM_PATTERNS_CLAUSE = "only your custom patterns are applied"

/**
 * WR-02 — what this file does and does not prove.
 *
 * [privacyNoticeFor] is a pure function of its parameters, so a test of it **can never be red for
 * WR-02**. WR-02 was never a defect in this computation; it lived in *which source the caller
 * passed* — the unsaved `JTextArea` rather than the persisted, validated settings list. Stating
 * that plainly matters more than manufacturing a red-before-green that would pass in both
 * directions and prove nothing.
 *
 * What makes these tests non-vacuous is the pair of guarantees around them:
 *  a. the composer is a **top-level** function, so no Swing component is in its lexical scope and
 *     the defective source is not reachable from inside it — enforced by the compiler, not by a
 *     comment; and
 *  b. mutating the `isNotEmpty()` decision fails these tests in both directions. That was
 *     *verified by running the mutations*, not asserted here; both failure sets are recorded in
 *     `21-14-SUMMARY.md`.
 *
 * The claim the reassuring clause makes is only honest because of the chain behind the argument
 * the caller now passes: the persisted list is written solely by `applyAndSaveSettings`, which
 * takes it from `validateAndCollectCustomPatterns`, which drops every line failing
 * `SafeRegex.isPatternSafe`, and the same list is handed to `Redaction.setCustomPatterns`. A
 * non-empty `persistedCustomPatterns` therefore means the engine really is applying at least one
 * pattern.
 */
class PrivacyNoticeCompositionTest {
    private data class OffArm(
        val label: String,
        val auditOff: Boolean,
        val activeOn: Boolean,
    )

    /** All four OFF risk combinations. They share one `offClause`, so all four are pinned together. */
    private val offArms =
        listOf(
            OffArm("OFF + audit off + active on", auditOff = true, activeOn = true),
            OffArm("OFF + audit off", auditOff = true, activeOn = false),
            OffArm("OFF + active on", auditOff = false, activeOn = true),
            OffArm("bare OFF", auditOff = false, activeOn = false),
        )

    private val somePersistedPatterns = listOf("(?i)internal-token-[0-9a-f]{8}")

    @Test
    fun bareOffWithNoPersistedPatternsWarnsThatRawTrafficMayLeave() {
        val (level, message) =
            privacyNoticeFor(PrivacyMode.OFF, auditOff = false, activeOn = false, persistedCustomPatterns = emptyList())

        assertEquals(SubtleNotice.Level.WARN, level)
        assertTrue(
            message?.contains(RAW_TRAFFIC_CLAUSE) == true,
            "An empty persisted list means nothing is redacted; the banner must say so: $message",
        )
    }

    @Test
    fun bareOffWithPersistedPatternsClaimsOnlyThosePatternsApply() {
        val (level, message) =
            privacyNoticeFor(
                PrivacyMode.OFF,
                auditOff = false,
                activeOn = false,
                persistedCustomPatterns = somePersistedPatterns,
            )

        assertEquals(SubtleNotice.Level.WARN, level)
        assertTrue(
            message?.contains(CUSTOM_PATTERNS_CLAUSE) == true,
            "A non-empty persisted list is genuinely applied by the engine: $message",
        )
    }

    @Test
    fun highestRiskOffArmWarnsRawTrafficWhenNothingIsPersisted() {
        val (level, message) =
            privacyNoticeFor(PrivacyMode.OFF, auditOff = true, activeOn = true, persistedCustomPatterns = emptyList())

        assertEquals(SubtleNotice.Level.RISK, level)
        assertTrue(
            message?.contains(RAW_TRAFFIC_CLAUSE) == true,
            "OFF + audit off + active on with no persisted patterns is the worst case: $message",
        )
    }

    @Test
    fun highestRiskOffArmClaimsCustomPatternsWhenSomeArePersisted() {
        val (level, message) =
            privacyNoticeFor(
                PrivacyMode.OFF,
                auditOff = true,
                activeOn = true,
                persistedCustomPatterns = somePersistedPatterns,
            )

        assertEquals(SubtleNotice.Level.RISK, level)
        assertTrue(
            message?.contains(CUSTOM_PATTERNS_CLAUSE) == true,
            "The reassuring clause is earned once the engine holds a pattern: $message",
        )
    }

    @Test
    fun everyOffArmWarnsRawTrafficWhenNoPatternsArePersisted() {
        for (arm in offArms) {
            val (level, message) =
                privacyNoticeFor(
                    PrivacyMode.OFF,
                    auditOff = arm.auditOff,
                    activeOn = arm.activeOn,
                    persistedCustomPatterns = emptyList(),
                )

            assertTrue(
                message?.contains(RAW_TRAFFIC_CLAUSE) == true,
                "${arm.label}: must keep the strong warning when nothing is persisted: $message",
            )
            assertFalse(
                message?.contains(CUSTOM_PATTERNS_CLAUSE) == true,
                "${arm.label}: must never claim custom patterns apply when none are persisted: $message",
            )
            assertNotHidden(arm.label, level)
        }
    }

    @Test
    fun everyOffArmClaimsCustomPatternsWhenSomeArePersisted() {
        for (arm in offArms) {
            val (level, message) =
                privacyNoticeFor(
                    PrivacyMode.OFF,
                    auditOff = arm.auditOff,
                    activeOn = arm.activeOn,
                    persistedCustomPatterns = somePersistedPatterns,
                )

            assertTrue(
                message?.contains(CUSTOM_PATTERNS_CLAUSE) == true,
                "${arm.label}: must report the patterns the engine actually holds: $message",
            )
            assertFalse(
                message?.contains(RAW_TRAFFIC_CLAUSE) == true,
                "${arm.label}: the two clauses are exclusive; both cannot appear: $message",
            )
            assertNotHidden(arm.label, level)
        }
    }

    @Test
    fun offArmLevelsAreRiskForCombinationsAndWarnForBareOff() {
        val expected =
            mapOf(
                "OFF + audit off + active on" to SubtleNotice.Level.RISK,
                "OFF + audit off" to SubtleNotice.Level.RISK,
                "OFF + active on" to SubtleNotice.Level.RISK,
                "bare OFF" to SubtleNotice.Level.WARN,
            )

        for (arm in offArms) {
            val (level, _) =
                privacyNoticeFor(
                    PrivacyMode.OFF,
                    auditOff = arm.auditOff,
                    activeOn = arm.activeOn,
                    persistedCustomPatterns = emptyList(),
                )
            assertEquals(expected[arm.label], level, "${arm.label}: notice level changed")
        }
    }

    @Test
    fun strictWithActiveScannerIsInfoAndIgnoresThePatternList() {
        val (withNone, messageWithNone) =
            privacyNoticeFor(PrivacyMode.STRICT, auditOff = false, activeOn = true, persistedCustomPatterns = emptyList())
        val (withSome, messageWithSome) =
            privacyNoticeFor(
                PrivacyMode.STRICT,
                auditOff = false,
                activeOn = true,
                persistedCustomPatterns = somePersistedPatterns,
            )

        assertEquals(SubtleNotice.Level.INFO, withNone)
        assertEquals(SubtleNotice.Level.INFO, withSome)
        // STRICT still runs the built-in rules, so neither OFF clause belongs here.
        assertEquals(messageWithNone, messageWithSome, "STRICT must not vary with the pattern list")
        assertFalse(messageWithNone?.contains(RAW_TRAFFIC_CLAUSE) == true, "STRICT is not raw traffic")
    }

    @Test
    fun balancedWithNoOtherRiskHidesTheNotice() {
        val (level, message) =
            privacyNoticeFor(
                PrivacyMode.BALANCED,
                auditOff = false,
                activeOn = false,
                persistedCustomPatterns = somePersistedPatterns,
            )

        assertNull(level, "BALANCED with audit on and the scanner off warrants no advisory")
        assertNull(message, "A hidden notice carries no message")
    }

    private fun assertNotHidden(
        label: String,
        level: SubtleNotice.Level?,
    ) = assertTrue(level != null, "$label: an OFF arm must always show a notice")
}
