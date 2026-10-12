package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.mcp.tools.McpToolExecutor
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * SC6: proves SEC-06 tier resolution for every shape of tool name the model can emit — a catalog ID,
 * one of the ten aliases, an `ext:` namespaced name, and three unknown-name shapes.
 *
 * No tool-context fixture appears here, and that is the point: the gate is context-free and pure, so
 * every row below is assertable with no Burp API, no mock and no Swing harness. If a future change
 * makes a context necessary, the gate has stopped being pure — fix the gate, do not import a fixture.
 */
class SecTierResolutionTest {
    /**
     * The ten alias inputs McpToolExecutor.canonicalToolId accepts, enumerated rather than sampled so
     * that adding an alias without extending this list is visible.
     */
    private val aliasInputs =
        listOf(
            "history",
            "proxy_history",
            "requests",
            "history_regex",
            "proxy_history_regex",
            "ws_history",
            "websocket_history",
            "websocket",
            "sitemap",
            "site_map_history",
        )

    /** The four canonical IDs those ten aliases collapse onto. All four are CONFIRM tools. */
    private val canonicalIds =
        setOf(
            "proxy_http_history",
            "proxy_http_history_regex",
            "proxy_ws_history",
            "site_map",
        )

    @Test
    fun builtInToolResolvesToItsCatalogTier() {
        assertEquals(SecTier.AUTO, ToolApprovalGate.tierFor("scope_check"))
        assertEquals(SecTier.CONFIRM, ToolApprovalGate.tierFor("proxy_http_history"))
        assertEquals(SecTier.CONFIRM_EACH, ToolApprovalGate.tierFor("http1_request"))
    }

    @Test
    fun everyAliasResolvesToItsCanonicalToolsTier() {
        aliasInputs.forEach { alias ->
            assertEquals(
                SecTier.CONFIRM,
                ToolApprovalGate.tierFor(alias),
                "Alias '$alias' did not resolve to its canonical tool's tier. A gate that skips " +
                    "canonicalisation labels this call 'unknown tool' on the card and in the audit " +
                    "record while the executor runs it as a known bulk-history tool.",
            )
        }
    }

    @Test
    fun externalToolNamespaceResolvesToConfirmEach() {
        assertEquals(SecTier.CONFIRM_EACH, ToolApprovalGate.tierFor("ext:demo:anything"))
        assertEquals(
            SecTier.CONFIRM_EACH,
            ToolApprovalGate.tierFor("ext:demo:scope_check"),
            "An external tool whose name collides with a built-in must NOT inherit the built-in's " +
                "tier (T-22-03). The tier is derived from the ext: namespace, never from the catalog.",
        )
        assertNotEquals(SecTier.AUTO, ToolApprovalGate.tierFor("ext:demo:scope_check"))
    }

    @Test
    fun unknownToolFailsClosed() {
        // "EXT:demo:x" is deliberate: canonicalToolId lowercases only for MATCHING and returns the
        // original string, so the wrong-case name never matches the ext: prefix and falls through to
        // the catalog lookup — the same path the executor takes before returning "Unknown tool:".
        val unknownNames = listOf("definitely_not_a_tool", "", "EXT:demo:x")
        unknownNames.forEach { name ->
            assertEquals(
                SecTier.CONFIRM_EACH,
                ToolApprovalGate.tierFor(name),
                "Unrecognised tool name '$name' must fail closed to CONFIRM_EACH.",
            )
            assertNotEquals(
                SecTier.AUTO,
                ToolApprovalGate.tierFor(name),
                "Unrecognised tool name '$name' resolved to AUTO and would have run silently. " +
                    "D-03 removes the AUTHORING default; it does not supply a RUNTIME fallback, " +
                    "and this is that fallback.",
            )
        }
    }

    @Test
    fun gateAndExecutorConsumeTheSameCanonicalisation() {
        aliasInputs.forEach { alias ->
            val canonical = McpToolExecutor.canonicalToolId(alias)
            assertTrue(
                canonical in canonicalIds,
                "Executor canonicalised '$alias' to '$canonical', which is not one of the four " +
                    "canonical IDs this test knows about.",
            )
            val descriptor = McpToolCatalog.all().first { it.id == canonical }
            assertEquals(
                descriptor.secTier,
                ToolApprovalGate.tierFor(alias),
                "The gate and the executor disagree about '$alias'. Either side growing its own " +
                    "alias handling is the defect this assertion exists to catch — there must be " +
                    "exactly one canonicalisation function and both sides must call it.",
            )
        }
    }

    @Test
    fun everyCatalogToolResolvesThroughTheGate() {
        McpToolCatalog.all().forEach { descriptor ->
            assertEquals(
                descriptor.secTier,
                ToolApprovalGate.tierFor(descriptor.id),
                "Catalog tool '${descriptor.id}' did not resolve to its own declared tier through " +
                    "the gate.",
            )
        }
    }
}
