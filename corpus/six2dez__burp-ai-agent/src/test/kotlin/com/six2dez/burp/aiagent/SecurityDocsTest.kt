package com.six2dez.burp.aiagent

import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.File

private const val SECURITY_FILE = "SECURITY.md"
private const val README_FILE = "README.md"
private const val SPEC_FILE = "SPEC.md"
private const val UI_SAFETY_FILE = "docs/ui-safety-guide.md"
private const val ANTHROPIC_DOC = "docs/anthropic-backend.md"
private const val EXTERNAL_MCP_DOC = "docs/external-mcp-servers.md"

/**
 * The preference the AES master key is written to — `SecretCipher.MASTER_KEY_PREF_KEY`.
 *
 * Naming the literal preference key, rather than accepting a vague "stored locally", is what makes
 * the at-rest caveat checkable by a reader: they can look for this string in their own preferences
 * and see the key sitting beside the ciphertext it protects.
 */
private const val MASTER_KEY_PREF = "secret.master.key.v1"

/**
 * The absolute claim `README.md` shipped from v0.9.0 until this phase. It was false the day it was
 * written: the master key is in preferences, Base64-encoded.
 */
private const val STALE_ABSOLUTE_CLAIM = "no plaintext in preferences"

/** Every document required to carry the at-rest caveat, not just the encryption claim. */
private val AT_REST_DOCS = listOf(README_FILE, SPEC_FILE, SECURITY_FILE, ANTHROPIC_DOC, EXTERNAL_MCP_DOC)

/** The three published releases SEC-04 and PRIV-05 are live in. */
private val AFFECTED_VERSIONS = listOf("0.9.0", "0.9.1", "0.9.2")

/** The release that carries both fixes. Published at the 1.0.0 release cut. */
private const val FIXED_VERSION = "1.0.0"

/**
 * DOC-03 / SC5 guard on the security advisory — the statement owed to every user running 0.9.0
 * through 0.9.2, who has an unauthenticated MCP listener if they opted into external access and has
 * sent real session cookies to a third-party model if they ran passive AI scanning.
 *
 * **What this test can do.** It is a string-match guard over `SECURITY.md` as it sits on disk. It
 * stops the advisory from being deleted, stops either finding from losing its affected-version range
 * or its fixed version, stops the user-action line — the only part of an advisory that changes what
 * a reader *does* — from being edited away, and stops the Supported Versions table from drifting
 * back to the stale 0.5 line it carried for four milestones.
 *
 * **What this test cannot do.** It cannot judge whether the advisory's account of each defect is
 * *accurate*, whether the impact is fairly stated rather than softened, or whether a reader would
 * actually act on it. That is judgement. The plan assigns it to the phase verifier and to the
 * human reading this file; the guard below only ensures there is something there to judge.
 *
 * Note on slicing: every version assertion runs against the *individual advisory entry*, not against
 * the whole file. A whole-file match would pass if one entry carried all three versions and the
 * other carried none — which is precisely the half-finished edit worth catching.
 */
class SecurityDocsTest {
    @Test
    fun securityPolicyCarriesAnAdvisoriesSection() {
        val security = readProjectFile(SECURITY_FILE)

        assertTrue(
            security.lineSequence().any { it.trim() == "## Security Advisories" },
            "$SECURITY_FILE must carry a `## Security Advisories` heading. SEC-04 and PRIV-05 were " +
                "confirmed by RUNNING v0.9.2, so the people running it are owed a statement in the " +
                "one file a user checks for exactly that. If this section moved, point this guard " +
                "at its new home rather than deleting the assertion.",
        )
    }

    @Test
    fun theAdvisoriesSectionNamesBothFindings() {
        val advisories = advisoriesSection()

        assertTrue(
            advisories.contains("SEC-04"),
            "The advisories section does not name SEC-04 — the MCP access-control bypass. It is the " +
                "critical finding of this milestone and the reason the milestone exists.",
        )
        assertTrue(
            advisories.contains("PRIV-05"),
            "The advisories section does not name PRIV-05 — the cookie leak to AI backends. It runs " +
                "directly against the project's stated core value, so it cannot be the finding that " +
                "gets quietly dropped from the advisory.",
        )
    }

    @Test
    fun theSec04EntryNamesEveryAffectedVersionAndTheFix() {
        assertEntryCarriesVersions("SEC-04")
    }

    @Test
    fun thePriv05EntryNamesEveryAffectedVersionAndTheFix() {
        assertEntryCarriesVersions("PRIV-05")
    }

    @Test
    fun theSec04EntryTellsAnAffectedUserWhatToDo() {
        val entry = advisoryEntry("SEC-04")

        assertTrue(
            entry.contains("User action"),
            "The SEC-04 entry carries no `User action` line. An advisory without one consumes the " +
                "reader's attention without changing what they do, which is worse than no advisory.",
        )
        assertTrue(
            entry.contains("unauthenticated", ignoreCase = true),
            "The SEC-04 user action must tell an operator to treat an externally-reachable listener " +
                "on an affected version as having been UNAUTHENTICATED. Anything softer leaves them " +
                "unsure whether the tool calls they see in their logs were their own.",
        )
        assertTrue(
            entry.contains("rotate", ignoreCase = true),
            "The SEC-04 user action must name the concrete remediation — rotating the MCP bearer " +
                "token. `Be aware of` is not an action.",
        )
    }

    @Test
    fun thePriv05EntryTellsAnAffectedUserWhatToDo() {
        val entry = advisoryEntry("PRIV-05")

        assertTrue(
            entry.contains("User action"),
            "The PRIV-05 entry carries no `User action` line. The whole point of disclosing a cookie " +
                "leak is that the reader rotates the cookies.",
        )
        assertTrue(
            entry.contains("rotate", ignoreCase = true),
            "The PRIV-05 user action must say to ROTATE affected session cookies. Describing the " +
                "leak without naming the remedy leaves the exposure standing.",
        )
        assertTrue(
            entry.contains("disclosed", ignoreCase = true),
            "The PRIV-05 user action must say that affected cookies should be treated as DISCLOSED " +
                "to the configured backend. A reader who thinks this was a near-miss will not act.",
        )
    }

    @Test
    fun thePriv05EntryNamesTheCookiesThatLeaked() {
        val entry = advisoryEntry("PRIV-05")

        listOf("JSESSIONID", "PHPSESSID", "connect.sid", "auth_token", "csrftoken", "remember_me")
            .forEach { cookie ->
                assertTrue(
                    entry.contains(cookie),
                    "The PRIV-05 entry does not name `$cookie`. The six names were verified against " +
                        "the live regexes; listing them is what lets a reader decide in seconds " +
                        "whether their traffic was affected, instead of guessing.",
                )
            }
    }

    @Test
    fun theAdvisorySaysNoIdentifierWasIssuedRatherThanLeavingTheReaderToAssume() {
        val advisories = advisoriesSection()

        assertTrue(
            advisories.contains("CVE") && advisories.contains("GHSA"),
            "The advisories section must state explicitly that no CVE and no GHSA identifier has " +
                "been issued. Silence reads as `there is one and I did not find it`; a fabricated " +
                "identifier would be worse still, because it makes every true statement beside it " +
                "unverifiable.",
        )
        assertFalse(
            Regex("CVE-\\d{4}-\\d{4,}").containsMatchIn(advisories),
            "The advisories section contains something shaped like a real CVE identifier. If one " +
                "has genuinely been issued, update this guard in the same commit that adds it — " +
                "otherwise it is invented, and an invented identifier undermines the whole advisory.",
        )
    }

    @Test
    fun theAdvisoryDoesNotStillCallTheFixUnreleased() {
        val advisories = advisoriesSection()

        // Inverted at the $FIXED_VERSION release cut. Before it, this guard asserted the advisory
        // said the fix was "not yet published", so a reader would not go hunting for a release that
        // did not exist. Now that $FIXED_VERSION ships, the same sentence is the lie: it would tell
        // a user on an affected version to keep waiting when the remedy is available today.
        listOf("not yet published", "unreleased", "will be available when that release ships").forEach { stale ->
            assertFalse(
                advisories.contains(stale, ignoreCase = true),
                "The advisories section still contains \"$stale\", but $FIXED_VERSION is published. " +
                    "A user on an affected version reading that will keep waiting for a fix they " +
                    "could already install. Update the advisory in the same commit that ships the release.",
            )
        }
    }

    @Test
    fun theSupportedVersionsTableNoLongerNamesTheStaleLine() {
        val security = readProjectFile(SECURITY_FILE)

        assertFalse(
            security.contains("0.5.x"),
            "$SECURITY_FILE still names `0.5.x` as the supported line. That table went unrevised " +
                "for four milestones; a user reading it cannot tell which releases actually receive " +
                "security fixes, which is the one question the table exists to answer.",
        )
        assertTrue(
            security.contains("0.9.x"),
            "$SECURITY_FILE's Supported Versions table must name `0.9.x` — the released line the " +
                "advisory above is about. Leaving it out orphans every affected reader.",
        )
    }

    @Test
    fun theSecurityModelStatesWhereTheMasterKeyLives() {
        val security = readProjectFile(SECURITY_FILE)

        assertTrue(
            security.contains("secret.master.key.v1"),
            "$SECURITY_FILE's Security Model must name `SecretCipher.MASTER_KEY_PREF_KEY` " +
                "(`secret.master.key.v1`) — the preference the AES master key is stored in, " +
                "Base64-encoded, beside the ciphertext it protects. Naming it is what makes the " +
                "caveat checkable rather than a hedge.",
        )
        assertTrue(
            security.contains("does **not** protect") || security.contains("does not protect"),
            "$SECURITY_FILE's Security Model must state what the at-rest encryption does NOT do. A " +
                "user who believes preference-file access is survivable will store a credential " +
                "there that they would otherwise have kept elsewhere.",
        )
    }

    // ---------------------------------------------------------------------------------------------
    // SC6 — the at-rest guarantee, stated accurately rather than absolutely.
    // ---------------------------------------------------------------------------------------------

    @Test
    fun readmeNoLongerCarriesTheAbsoluteAtRestClaim() {
        val readme = readProjectFile(README_FILE)

        assertFalse(
            readme.contains(STALE_ABSOLUTE_CLAIM),
            "$README_FILE still claims `$STALE_ABSOLUTE_CLAIM`. The AES master key is stored in " +
                "preferences Base64-encoded, so the claim is false. It must be REPLACED with what is " +
                "true — deleting the bullet instead reads to a returning user as though the property " +
                "still holds and merely went undocumented.",
        )
    }

    @Test
    fun everyDocumentThatClaimsEncryptionAtRestAlsoStatesTheCaveat() {
        AT_REST_DOCS.forEach { path ->
            val text = readProjectFile(path)

            assertTrue(
                text.contains(MASTER_KEY_PREF),
                "`$path` claims secrets are encrypted at rest but does not name `$MASTER_KEY_PREF` " +
                    "— the preference the master key itself is stored in. All five documents are " +
                    "corrected in one pass on purpose: shipping a corrected README beside " +
                    "uncorrected pages leaves the overstated claim reachable, which is the same " +
                    "outcome as not correcting it.",
            )
            assertTrue(
                text.contains("Burp Preferences", ignoreCase = true),
                "`$path` does not say that the master key lives in Burp Preferences. `Encrypted at " +
                    "rest` without that clause is the claim a user builds a wrong threat model on.",
            )
        }
    }

    @Test
    fun theFullAtRestStatementSaysWhatTheEncryptionDoesNotDo() {
        listOf(README_FILE, SPEC_FILE).forEach { path ->
            val text = readProjectFile(path)

            assertTrue(
                text.contains("not** protect") || text.contains("not protect"),
                "`$path` must carry the full at-rest statement, including what the encryption does " +
                    "NOT protect against. `$README_FILE` Privacy and Security Notes and `$SPEC_FILE` " +
                    "§9 are the two places that statement is made in full; the shorter mentions " +
                    "point here.",
            )
            assertTrue(
                text.contains("casual inspection"),
                "`$path` must name the threat the encryption actually addresses — casual inspection " +
                    "of a preferences file or an export. Stating only the negative leaves a reader " +
                    "wondering why the encryption is there at all.",
            )
        }
    }

    // ---------------------------------------------------------------------------------------------
    // SC6 — the SEC-06 tool-call confirmation flow, which shipped in Phase 22 and was documented
    // only in DECISIONS.md ADR-15, a design record rather than user documentation.
    // ---------------------------------------------------------------------------------------------

    @Test
    fun theConfirmationFlowIsDocumentedForUsers() {
        listOf(README_FILE, SPEC_FILE, UI_SAFETY_FILE).forEach { path ->
            val text = readProjectFile(path)

            assertTrue(
                text.contains("confirm", ignoreCase = true),
                "`$path` does not mention the tool-call confirmation flow. It shipped in Phase 22 " +
                    "and was documented only in `DECISIONS.md` ADR-15 — a design record, not " +
                    "something a user reads. A control nobody knows about is one they cannot use.",
            )
        }
    }

    @Test
    fun theDocumentedFlowStatesThatAModelEmittedCallNeedsADecision() {
        listOf(README_FILE, SPEC_FILE).forEach { path ->
            val text = readProjectFile(path)

            assertTrue(
                text.contains("model output") || text.contains("model-emitted"),
                "`$path` must say that the gate applies to a tool call parsed out of MODEL OUTPUT. " +
                    "That is the whole trust boundary: the call originates with the model, not with " +
                    "the user, which is why a decision is required at all.",
            )
        }
    }

    @Test
    fun theDocumentedFlowNamesAllThreeTiers() {
        listOf(README_FILE, SPEC_FILE, UI_SAFETY_FILE).forEach { path ->
            val text = readProjectFile(path).lowercase()

            assertTrue(
                text.contains("session"),
                "`$path` must describe the middle tier — confirm, with an approve-for-this-session " +
                    "option. Documenting only `it asks you` collapses three tiers into one and " +
                    "leaves a user unable to predict when they will be asked again.",
            )
            assertTrue(
                text.contains("every call") || text.contains("every single call"),
                "`$path` must describe the confirm-every-time tier explicitly. It is the tier an " +
                    "unrecognised tool name falls into, so a user who does not know it exists " +
                    "cannot tell a fail-closed prompt from a malfunction.",
            )
        }
    }

    @Test
    fun theDocumentedFlowStatesThatAnUnrecognisedToolFailsClosed() {
        listOf(README_FILE, SPEC_FILE, UI_SAFETY_FILE).forEach { path ->
            val text = readProjectFile(path).lowercase()

            assertTrue(
                text.contains("does not recognise") || text.contains("unrecognised"),
                "`$path` must state that a tool name the catalog does not recognise resolves to " +
                    "confirm-every-time rather than to automatic. `ToolApprovalGate.tierFor` returns " +
                    "`descriptor?.secTier ?: SecTier.CONFIRM_EACH` precisely so this is true; a user " +
                    "who assumes the opposite has the failure mode backwards.",
            )
            assertTrue(
                text.contains("ext:"),
                "`$path` must state that external `ext:`-namespaced tools always confirm every " +
                    "call. `tierFor` short-circuits on that prefix before the catalog lookup, so an " +
                    "external tool can never inherit a built-in's AUTO tier.",
            )
        }
    }

    @Test
    fun theDocumentedFlowStatesThatDecisionsAreRecorded() {
        listOf(README_FILE, SPEC_FILE, UI_SAFETY_FILE).forEach { path ->
            val text = readProjectFile(path).lowercase()

            assertTrue(
                text.contains("audit"),
                "`$path` must state that the decision is audit-logged. `ToolDecisionReporter` emits " +
                    "one audit event and one Burp Output line from a single payload construction; " +
                    "without documenting it, a user cannot answer `what did I approve last week?`",
            )
        }
    }

    @Test
    fun theDocumentedFlowDistinguishesTheTierFromUnsafeMode() {
        listOf(README_FILE, SPEC_FILE, UI_SAFETY_FILE).forEach { path ->
            val text = readProjectFile(path).lowercase()

            assertTrue(
                text.contains("unsafe mode") || text.contains("unsafeonly"),
                "`$path` must state that the confirmation tier is INDEPENDENT of the Unsafe Mode " +
                    "switch (ADR-15 D-01): Unsafe Mode governs whether a tool may ever run, the tier " +
                    "governs whether the model may run it without asking. Naming one axis where two " +
                    "exist is how a user concludes that leaving Unsafe Mode off makes the cards " +
                    "unnecessary.",
            )
        }
    }

    @Test
    fun theOperatorRunbookExplainsTheCardAndItsActions() {
        val guide = readProjectFile(UI_SAFETY_FILE)

        assertTrue(
            guide.lineSequence().any { it.trim() == "## Tool-Call Confirmation" },
            "`$UI_SAFETY_FILE` must carry a `## Tool-Call Confirmation` section. This runbook is " +
                "where an operator looks when the extension asks them to approve something; if the " +
                "answer is not here they will approve without knowing what they approved.",
        )
        listOf("Approve once", "Approve for session", "Deny for session")
            .forEach { label ->
                assertTrue(
                    guide.contains(label),
                    "`$UI_SAFETY_FILE` does not explain the `$label` action. The four labels are " +
                        "declared in `ToolApprovalCard`; a runbook that omits one leaves the " +
                        "operator guessing at the button with the widest blast radius.",
                )
            }
        assertTrue(
            guide.contains("Clear Chat"),
            "`$UI_SAFETY_FILE` must state that Clear Chat discards session approvals. " +
                "`ChatPanel.clearChatState` assigns a fresh `ToolApprovalMemory` for exactly this " +
                "reason — an approval granted while reviewing target A must not run silently " +
                "against target B.",
        )
        assertTrue(
            guide.contains("not authorised"),
            "`$UI_SAFETY_FILE` must state that a denial returns a neutral result to the model " +
                "rather than an error. `ToolApprovalGate.DENIAL_RESULT` says `not authorised … do " +
                "not retry`; an operator who believes denial throws will hesitate to use it.",
        )
    }

    /**
     * Reads a file relative to the Gradle project directory.
     *
     * `tasks.test` runs with the project directory as its working directory, so a plain relative path
     * resolves. The existence assertion names the resolved working directory rather than letting a
     * future build-layout change surface as an unhelpful empty string.
     */
    internal fun readProjectFile(relativePath: String): String {
        val file = File(relativePath)
        assertTrue(
            file.isFile,
            "Expected to find `$relativePath` relative to the test working directory " +
                "`${System.getProperty("user.dir")}`, resolved as `${file.absolutePath}`. " +
                "If the build layout changed, fix the path here rather than deleting this test.",
        )
        return file.readText()
    }

    /** `SECURITY.md`'s advisories section, sliced from its heading to the next `## ` heading. */
    private fun advisoriesSection(): String = slice(readProjectFile(SECURITY_FILE), "## Security Advisories", "\n## ")

    /**
     * One advisory entry, sliced from its `### ` heading to the next `### ` or `## ` heading, so a
     * version-range assertion cannot be satisfied by text belonging to the OTHER finding.
     */
    private fun advisoryEntry(finding: String): String {
        val advisories = advisoriesSection()
        val start = advisories.indexOf("### $finding")
        assertTrue(
            start >= 0,
            "$SECURITY_FILE's advisories section has no `### $finding` heading to slice. Each " +
                "finding needs its own entry — a merged paragraph lets one finding's details stand " +
                "in for the other's.",
        )
        val rest = advisories.substring(start)
        val next = rest.indexOf("\n### ", 1).let { if (it >= 0) it else rest.indexOf("\n## ", 1) }
        return if (next >= 0) rest.substring(0, next) else rest
    }

    private fun assertEntryCarriesVersions(finding: String) {
        val entry = advisoryEntry(finding)

        AFFECTED_VERSIONS.forEach { version ->
            assertTrue(
                entry.contains(version),
                "The $finding entry does not name affected version `$version`. All three published " +
                    "0.9.x releases carry this defect; hedging the range leaves a reader on the " +
                    "unnamed one assuming they are safe.",
            )
        }
        assertTrue(
            entry.contains(FIXED_VERSION),
            "The $finding entry does not name `$FIXED_VERSION` as the fixed version. An advisory " +
                "that states the problem without stating the fix gives the reader nowhere to go.",
        )
    }

    private fun slice(
        text: String,
        heading: String,
        terminator: String,
    ): String {
        val start = text.indexOf(heading)
        assertTrue(start >= 0, "Expected to find `$heading` to slice from.")
        val next = text.indexOf(terminator, start + heading.length)
        return if (next >= 0) text.substring(start, next) else text.substring(start)
    }
}
