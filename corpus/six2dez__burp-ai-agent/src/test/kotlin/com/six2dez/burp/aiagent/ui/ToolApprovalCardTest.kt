package com.six2dez.burp.aiagent.ui

import com.six2dez.burp.aiagent.mcp.SecTier
import com.six2dez.burp.aiagent.mcp.ToolDecision
import com.six2dez.burp.aiagent.ui.components.ToolApprovalCard
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.awt.Component
import java.awt.Container
import javax.swing.AbstractButton
import javax.swing.JButton
import javax.swing.JComponent
import javax.swing.JLabel
import javax.swing.JTextArea
import javax.swing.JTextField
import javax.swing.text.JTextComponent

/**
 * SEC-06 / SC2: proves the trust-typography rules of `ToolApprovalCard` mechanically.
 *
 * These run headless because `build.gradle.kts` passes `-Djava.awt.headless=true` (plan 22-01). A real
 * Swing card is constructed, walked and clicked — no model of the card, and no modal, which is one of
 * the reasons D-06 rejected a dialog: `JOptionPane.getRootFrame()` throws `HeadlessException`, so a
 * modal decision surface would be untestable in CI.
 *
 * Note for anyone reading `ChatPanelConcurrencyTest`: its KDoc claims a real Swing component cannot be
 * constructed headless. That premise was measured false in Phase 22 Wave 0. Do not model these
 * assertions on that file.
 *
 * **What is deliberately NOT asserted here:** pixel positions, colours and fonts. Those are the human
 * UAT items in `22-HUMAN-UAT.md`. What is asserted is structure, widget class, text content and callback
 * wiring — which is what actually carries the security property.
 *
 * **Naming constraint (hard).** `build.gradle.kts` excludes `*IntegrationTest`, `*ConcurrencyTest`,
 * `*BackpressureTest`, `*RestartPolicyTest` and `*SupervisionTest` under `-PexcludeHeavyTests=true`,
 * which is exactly what the PR gate passes. This file must keep the plain `Test` suffix.
 */
class ToolApprovalCardTest {
    @Test
    fun confirmCardRendersFourDecisionButtons() {
        val card = pendingCard(tier = SecTier.CONFIRM, offersSessionActions = true)

        assertEquals(
            listOf("Deny", "Deny for session", "Approve once", "Approve for session"),
            decisionButtonsOf(card).map { it.text },
            "A CONFIRM card must offer all four D-11 actions, in safe-action-first visual order. " +
                "The button count is the structural channel that survives grayscale, low vision and a " +
                "screenshot, and the order is what puts Deny on the first Tab stop.",
        )

        val args = requireNotNull(ChatPanelTestHarness.find(card, JTextArea::class.java))
        assertFalse(
            args.isVisible,
            "A CONFIRM card starts with its arguments COLLAPSED (UI-SPEC anti-habituation rule A). " +
                "Expanding on both tiers would remove the size difference that makes a CONFIRM_EACH " +
                "card interrupt a run of CONFIRM cards.",
        )
    }

    @Test
    fun confirmEachCardRendersTwoDecisionButtons() {
        val card = pendingCard(tier = SecTier.CONFIRM_EACH, offersSessionActions = false)

        assertEquals(
            listOf("Deny", "Approve once"),
            decisionButtonsOf(card).map { it.text },
            "CONFIRM_EACH has no session memory in either direction (D-02), so a session-wide action " +
                "on its card would offer something the gate cannot honour.",
        )
        val everyLabel = descendantsOf(card).mapNotNull { textOf(it) }
        assertFalse(
            everyLabel.any { it == "Deny for session" || it == "Approve for session" },
            "Neither session-scoped label may appear anywhere in a CONFIRM_EACH card's component tree.",
        )

        val args = requireNotNull(ChatPanelTestHarness.find(card, JTextArea::class.java))
        assertTrue(
            args.isVisible,
            "A CONFIRM_EACH card expands its arguments by default (UI-SPEC rule A, the T-22-29 " +
                "mitigation). D-02/D-04's whole argument for this tier is 'constant tool name and " +
                "hostile args' — for it the args ARE the decision, so a payload cannot be approved " +
                "from below a fold.",
        )
    }

    @Test
    fun modelSuppliedTextNeverInstallsTheHtmlRenderer() {
        val toolId = "<html><b>Approved</b>"
        val argsJson = "<html><i>safe</i>"
        val exercised = mutableSetOf<String>()

        htmlSweepFixtures(toolId, argsJson).forEach { (state, card) ->
            // Rule T-2 made mechanical. BasicHTML.isHTMLString fires only at offset 0 and installs a
            // renderer that both JLabel and AbstractButton route their text through, leaving a non-null
            // "html" client property behind. This is the anti-spoofing assertion the whole card exists for.
            descendantsOf(card).forEach { component ->
                if (component !is JLabel && component !is AbstractButton) return@forEach
                if ((component as JComponent).getClientProperty("html") == null) return@forEach
                val text = textOf(component).orEmpty()
                val exemption = HTML_EXEMPT_ROWS.entries.firstOrNull { it.value(text) }
                assertNotNull(
                    exemption,
                    "Swing's HTML renderer is installed on a ${component.javaClass.simpleName} carrying " +
                        "'$text' on a $state, and that row is not one of the documented extension-authored " +
                        "exemptions. A model-supplied string that reaches an HTML-rendering JLabel or button " +
                        "can paint itself as extension chrome at the exact moment the card asks for " +
                        "authorisation. Add the row to HTML_EXEMPT_ROWS only if its text is extension-" +
                        "authored with no model-supplied interpolation.",
                )
                exercised += requireNotNull(exemption).key
                // The exemption is granted to a STRING SHAPE, so it would survive a future edit that
                // interpolated the model's tool ID or its args into one of those templates — which is
                // exactly the edit WR-06 predicted for the truncation footer. This clause is what stops
                // the exemption from becoming the hole: an exempt row may still carry no model byte.
                assertFalse(
                    text.contains(toolId) || text.contains(argsJson),
                    "An HTML-rendering label on a $state interpolated model-supplied text: '$text'. " +
                        "The exemption covers extension-authored templates whose only interpolations are " +
                        "extension-computed integers; it is not a licence to concatenate model output.",
                )
            }

            val carriers = descendantsOf(card).filter { textOf(it)?.contains(toolId) == true || textOf(it)?.contains(argsJson) == true }
            assertTrue(carriers.isNotEmpty(), "The model's strings must be rendered somewhere on a $state — the user has to see what was asked for.")
            carriers.forEach { component ->
                assertTrue(
                    component is JTextField || component is JTextArea,
                    "Model-supplied text reached a ${component.javaClass.simpleName} on a $state. The " +
                        "positive allowlist is the primary control: it goes into JTextField / JTextArea " +
                        "and nothing else, because neither ever installs the HTML renderer.",
                )
            }
        }

        // NON-VACUITY, and the reason this test was rewritten. The assertion above is a sweep over
        // whatever the fixtures happen to build, so an exemption nobody constructs is an exemption
        // nobody checks — which is precisely how the blanket form this replaced stayed green while
        // `truncationFooter` shipped an `<html>` prefix (UF-2 / UI-REVIEW T-2). Every documented
        // exemption must be REACHED by some fixture, or the fixture set is stale.
        assertEquals(
            HTML_EXEMPT_ROWS.keys,
            exercised,
            "An exemption was declared but never constructed by any fixture, so nothing checks it. " +
                "Either drive the state that builds it or delete the exemption.",
        )
    }

    @Test
    fun modelSuppliedTextIsNeverConcatenatedIntoExtensionText() {
        val toolId = "scope_check_but_actually_evil"
        val card = pendingCard(toolId = toolId)

        descendantsOf(card).forEach { component ->
            if (component is JLabel || component is AbstractButton) {
                assertFalse(
                    textOf(component).orEmpty().contains(toolId),
                    "One widget carries one trust class. A '\$prefix + modelString' concatenation puts " +
                        "attacker-influenceable text inside a widget the user reads as extension chrome.",
                )
            }
            if (component is JComponent) {
                assertFalse(
                    component.toolTipText.orEmpty().contains(toolId),
                    "Swing renders HTML tooltips natively, so a model-authored tooltip is styled, " +
                        "floating, extension-looking text.",
                )
            }
        }
    }

    @Test
    fun toolIdIsSanitizedAndCapped() {
        val card = pendingCard(toolId = "a\r\nInjected: line" + "x".repeat(PADDING_LENGTH))

        val field = requireNotNull(ChatPanelTestHarness.find(card, JTextField::class.java))
        assertFalse(field.text.contains('\r'), "Control characters must be stripped before display.")
        assertFalse(field.text.contains('\n'), "A multi-line tool ID could occupy several lines and imitate an outcome row.")
        assertTrue(
            field.text.contains("aInjected: line"),
            "Control characters are REMOVED, never replaced (CWE-117), so 'a\\r\\nInjected: line' " +
                "collapses to 'aInjected: line' and a forged second line is impossible.",
        )
        assertTrue(
            field.text.length <= TOOL_ID_CAP_WITH_ELLIPSIS,
            "The inline cap is 120 characters plus the ellipsis. Without it a model can use the tool " +
                "ID as a canvas. Rendered length was ${field.text.length}.",
        )
    }

    @Test
    fun unknownToolIsLabelledNeverShownBare() {
        val toolId = "definitely_not_in_the_catalog"
        val card = pendingCard(catalogTitle = null, toolId = toolId)

        val labels = descendantsOf(card).filterIsInstance<JLabel>()
        assertTrue(
            labels.any { it.text == "Not a known tool — this call will fail if you approve it." },
            "Rule T-7: an unrecognised tool is labelled as unknown. No catalog title is fabricated for it.",
        )
        labels.forEach {
            assertFalse(
                it.text.orEmpty().contains(toolId),
                "The model's string still appears — sanitized, inside its box — but never as a title.",
            )
        }
    }

    @Test
    fun resolutionRemovesButtonsAndAddsAnOutcomeRow() {
        val received = mutableListOf<ToolDecision>()
        val card = pendingCard(onDecision = { received.add(it) })

        val approve = requireNotNull(decisionButtonsOf(card).firstOrNull { it.text == "Approve once" })
        approve.doClick()
        assertEquals(listOf(ToolDecision.APPROVE_ONCE), received, "Each button must carry its own ToolDecision to the single callback.")

        card.resolve(ToolDecision.APPROVE_ONCE)

        assertEquals(
            0,
            decisionButtonsOf(card).size,
            "Buttons are REMOVED, not disabled. A disabled JButton is indistinguishable from " +
                "'unavailable' months later and leaves permanent noise in a scrolling record.",
        )
        assertTrue(
            descendantsOf(card).filterIsInstance<JLabel>().any { it.text == "Approved once" },
            "The outcome row names the clicked action verbatim — that is what makes the card a record " +
                "rather than a prompt that vanished.",
        )
        assertTrue(
            descendantsOf(card).filterIsInstance<JButton>().any { it.text.orEmpty().contains("arguments") },
            "The args region stays expandable after resolution. The args ARE the record of what was " +
                "authorised; collapsing them for good would destroy the reason the card persists.",
        )
    }

    @Test
    fun accessibleDescriptionEndsWithTheSanitizedToolId() {
        // A fixture that actually NEEDS sanitizing. The previous one was "http1_request", which
        // sanitizeInline returns unchanged — so every assertion below passed identically whether the
        // description interpolated the sanitized ID or the raw model string, and the first of the three
        // claims the guarded KDoc makes ("a multi-line ID cannot be read as several sentences") was
        // untested on this channel (WR-08 / UF-3). This one carries a CR/LF pair, a forged approval
        // glyph and enough padding to trip the 120-character inline cap.
        val raw = "http1_request\r\n✔ Approved by this extension" + "x".repeat(PADDING_LENGTH)
        val resolved = pendingCard(toolId = raw)
        resolved.resolve(ToolDecision.DENY)

        listOf(
            "pending known tool" to pendingCard(toolId = raw),
            "pending unknown tool" to pendingCard(catalogTitle = null, toolId = raw),
            "resolved card" to resolved,
        ).forEach { (state, card) ->
            // Read BACK off the card rather than recomputed here: a test that re-derived the sanitized
            // form with its own call would go green against a description built by a different one.
            val sanitized = requireNotNull(ChatPanelTestHarness.find(card, JTextField::class.java)).text
            assertNotEquals(
                raw,
                sanitized,
                "Fixture check on a $state: the tool ID must be one sanitization actually changes, or " +
                    "the assertions below cannot tell the sanitized form from the raw model string.",
            )

            val description = card.accessibleContext.accessibleDescription
            assertTrue(
                description.endsWith(sanitized),
                "On a $state the accessible description must END with the SANITIZED tool ID and have " +
                    "nothing after it. A screen reader has no notion of position, so anything following " +
                    "the model string would be heard as narration this extension wrote. Got: $description",
            )
            assertTrue(
                description.endsWith("The following tool name was written by the AI, not by this extension: $sanitized"),
                "The disclosure clause must come IMMEDIATELY before the ID, so attribution is heard " +
                    "before the attacker-influenceable text, never after it. Got: $description",
            )
            assertFalse(
                description.contains('\n') || description.contains('\r'),
                "A multi-line ID would be read as several sentences, so the extension's own narration " +
                    "and the model's string become indistinguishable in audio. Got: $description",
            )
        }
    }

    @Test
    fun compactRowRendersBothVariantsWithNoButtons() {
        val denied = ToolApprovalCard.compact(ToolDecision.SESSION_DENIED, "Send HTTP/1.1 request", "http1_request", "{}")
        val approved = ToolApprovalCard.compact(ToolDecision.SESSION_APPROVED, "Send HTTP/1.1 request", "http1_request", "{}")

        assertTrue(
            labelTextsOf(denied).any { it.contains("Blocked automatically — you denied this tool for this chat") },
            "The session-denied row is REQUIRED: without it the denial is invisible and the chain " +
                "appears to stall for no reason.",
        )
        assertTrue(
            labelTextsOf(approved).any { it.contains("Ran without asking — approved for this chat") },
            "The session-approved row ships too (FLAG-22-03): the card is a record, and a call that ran " +
                "against the target with nobody asked is exactly what a record is for.",
        )

        listOf(denied, approved).forEach { card ->
            assertEquals(0, decisionButtonsOf(card).size, "A compact row is a receipt, not a prompt — nothing was offered here.")
            assertTrue(
                labelTextsOf(card).any { it.contains("AI-supplied — this extension did not write the text below:") },
                "Rule T-5 is not conditional on card kind: wherever a model region appears, the trust " +
                    "label appears immediately above it.",
            )
            assertNotNull(
                ChatPanelTestHarness.find(card, JTextField::class.java),
                "The boxed tool-ID field stays: for an unknown tool the model's string is the only " +
                    "identifying content in the whole record.",
            )
        }
    }
}

/**
 * The ONLY label texts on this card that may install Swing's HTML renderer, enumerated one row at a
 * time.
 *
 * The assertion this replaced exempted nothing and swept **every** `JLabel`, which was already false
 * of shipped code: `truncationFooter` is a `JLabel` on a *pending* card and takes an `<html>` prefix
 * whenever the args preview truncates (`ToolApprovalCard.footerTextFor`). It stayed green only because
 * its single fixture passed 23 characters of args, so the footer was never constructed — and that
 * over-broad-but-unexercised assertion is what blocked the row-2 / row-10 wrapping fix the UI audit
 * measured as a reachability blocker (UF-2, UI-REVIEW T-2 / S-1).
 *
 * The exemption is granted per row, never to `JLabel` as a class, and each entry earns it the same
 * way: the string is extension-authored, it is interpolated with extension-computed integers or
 * nothing at all, and a plain `JLabel` does not wrap while the transcript sets
 * `HORIZONTAL_SCROLLBAR_NEVER` — so without the prefix the row clips with no way to read the rest.
 * The sweep additionally requires that no exempt row carries a model byte, which is what stops this
 * map from becoming the hole it exists to bound.
 */
private val HTML_EXEMPT_ROWS: Map<String, (String) -> Boolean> =
    mapOf(
        // Interpolates two extension-computed character counts and nothing else. Prefix-matched
        // because those integers vary; the no-model-byte clause in the sweep covers the tail.
        "row 8 — args truncation footer" to { text: String -> text.startsWith("<html>Showing the first ") },
        // Verbatim from the Copywriting Contract, no interpolation at all, so matched exactly.
        "compact row — outcome verb" to { text: String -> text in COMPACT_OUTCOME_VERBS_HTML },
        // Rows 2 and 10, wrapped so the card can shrink far enough to keep its decision buttons on
        // screen (22-UI-REVIEW.md S-1). Both are `private const` copy with no interpolation whatsoever,
        // which is the strongest form this exemption takes — matched exactly, so a template that grew an
        // interpolation would land in the un-exempt branch and fail before the no-model-byte clause even
        // ran.
        "row 2 — tier reason" to { text: String -> text in TIER_REASONS_HTML },
        "row 10 — session scope footer" to { text: String -> text == SESSION_SCOPE_FOOTER_HTML },
    )

/** Both tier reasons, `<html>`-wrapped by `ToolApprovalCard.wrapped`, verbatim from the copy contract. */
private val TIER_REASONS_HTML =
    setOf(
        "<html>Approving for the session applies to this tool until this chat is deleted.",
        "<html>This tool is approved one call at a time. A session-wide approval is not offered for it.",
    )

/** Row 10, `<html>`-wrapped, verbatim from the copy contract. */
private const val SESSION_SCOPE_FOOTER_HTML =
    "<html>\"Session\" means this chat. Approvals are forgotten when the chat is deleted, " +
        "and are not restored when Burp restarts."

/** The two `<html>`-wrapped compact verbs, spelled out so a copy change has to be made here too. */
private val COMPACT_OUTCOME_VERBS_HTML =
    setOf(
        "<html>Ran without asking — approved for this chat",
        "<html>Blocked automatically — you denied this tool for this chat",
    )

/**
 * Comfortably past the card's private 3200-character args preview cap, so `footerTextFor` returns the
 * truncated form and the footer actually takes its `<html>` prefix.
 *
 * Restated rather than shared because the cap is `private` to `ToolApprovalCard` — and it does not
 * need to track it, because the non-vacuity assertion at the end of the sweep fails loudly if this
 * number ever stops being enough.
 */
private const val ARGS_PAST_PREVIEW_CAP = 4000

/**
 * The card states the HTML-renderer sweep must visit.
 *
 * A pending card with SHORT args was the sweep's only fixture, and it is precisely the state in which
 * `footerTextFor` returns `null` and `isCompact` is false — so neither of the two shipped `<html>`
 * sites was ever constructed, let alone checked. Both are driven here.
 */
private fun htmlSweepFixtures(
    toolId: String,
    argsJson: String,
): List<Pair<String, ToolApprovalCard>> =
    listOf(
        "pending card with short args" to pendingCard(toolId = toolId, args = argsJson),
        "pending card with args past the preview cap" to
            pendingCard(toolId = toolId, args = argsJson + "y".repeat(ARGS_PAST_PREVIEW_CAP)),
        "compact session-denied row" to
            ToolApprovalCard.compact(ToolDecision.SESSION_DENIED, "Send HTTP/1.1 request", toolId, argsJson),
        "compact session-approved row" to
            ToolApprovalCard.compact(ToolDecision.SESSION_APPROVED, "Send HTTP/1.1 request", toolId, argsJson),
    )

/** 120-character inline cap plus the one ellipsis character `sanitizeInline` appends. */
private const val TOOL_ID_CAP_WITH_ELLIPSIS = 121

/** Enough padding to push a tool ID well past the inline cap. */
private const val PADDING_LENGTH = 300

/** The D-11 label set. Membership of it is what makes a button a *decision* control. */
private val DECISION_LABELS = setOf("Deny", "Deny for session", "Approve once", "Approve for session")

/**
 * Builds a pending card. The model-supplied strings have defaults so each test overrides only the one
 * it is about; [onDecision] defaults to a no-op because eight of the nine tests do not assert on it.
 */
private fun pendingCard(
    tier: SecTier = SecTier.CONFIRM,
    catalogTitle: String? = "Send HTTP/1.1 request",
    toolId: String = "http1_request",
    args: String? = "{\"host\":\"evil.example\"}",
    offersSessionActions: Boolean = true,
    repeatCount: Int = 1,
    onDecision: (ToolDecision) -> Unit = { },
): ToolApprovalCard =
    ToolApprovalCard(
        tier = tier,
        catalogTitle = catalogTitle,
        modelSuppliedToolId = toolId,
        modelSuppliedArgsJson = args,
        offersSessionActions = offersSessionActions,
        repeatCount = repeatCount,
        onDecision = onDecision,
    )

/**
 * Every descendant of [root], depth first, in insertion order — so a returned list of buttons is also
 * their visual order.
 *
 * `ChatPanelTestHarness.find` is reused for every single-component lookup in this file and is not
 * duplicated here. It returns the FIRST match by design, and the assertions that carry the security
 * property in this suite are counts and exhaustive sweeps ("exactly four buttons", "no JLabel anywhere
 * has the HTML renderer"), which a first-match finder cannot express.
 */
private fun descendantsOf(root: Container): List<Component> =
    root.components.flatMap { child ->
        listOf(child) + if (child is Container) descendantsOf(child) else emptyList()
    }

/** The rendered text of any widget that has some, regardless of which trust class it belongs to. */
private fun textOf(component: Component): String? =
    when (component) {
        is JTextComponent -> component.text
        is AbstractButton -> component.text
        is JLabel -> component.text
        else -> null
    }

private fun decisionButtonsOf(card: Container): List<AbstractButton> = descendantsOf(card).filterIsInstance<AbstractButton>().filter { it.text in DECISION_LABELS }

private fun labelTextsOf(card: Container): List<String> = descendantsOf(card).filterIsInstance<JLabel>().mapNotNull { it.text }
