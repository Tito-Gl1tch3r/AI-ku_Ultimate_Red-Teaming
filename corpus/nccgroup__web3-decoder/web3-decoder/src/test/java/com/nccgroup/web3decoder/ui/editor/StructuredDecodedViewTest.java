package com.nccgroup.web3decoder.ui.editor;

import org.junit.jupiter.api.Test;

import java.awt.Component;
import java.awt.Container;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Headless tests for the structured (read-only) projection of the decoded JSON. We don't
 * paint anything; we just inspect the rendered component tree to confirm chips, disclosure
 * nodes, and resilience to bad input.
 */
class StructuredDecodedViewTest {

    private static List<StructuredDecodedView.Chip> chipsIn(Container root) {
        List<StructuredDecodedView.Chip> out = new ArrayList<>();
        collectChips(root, out);
        return out;
    }

    private static void collectChips(Container c, List<StructuredDecodedView.Chip> out) {
        for (Component child : c.getComponents()) {
            if (child instanceof StructuredDecodedView.Chip) {
                out.add((StructuredDecodedView.Chip) child);
            }
            if (child instanceof Container) {
                collectChips((Container) child, out);
            }
        }
    }

    private static List<StructuredDecodedView.DisclosureNode> disclosuresIn(Container root) {
        List<StructuredDecodedView.DisclosureNode> out = new ArrayList<>();
        collectDisclosures(root, out);
        return out;
    }

    private static void collectDisclosures(Container c, List<StructuredDecodedView.DisclosureNode> out) {
        for (Component child : c.getComponents()) {
            if (child instanceof StructuredDecodedView.DisclosureNode) {
                out.add((StructuredDecodedView.DisclosureNode) child);
            }
            if (child instanceof Container) {
                collectDisclosures((Container) child, out);
            }
        }
    }

    private static boolean anyChipOfKind(Container root, StyleKind kind) {
        for (StructuredDecodedView.Chip chip : chipsIn(root)) {
            if (chip.kind() == kind) return true;
        }
        return false;
    }

    @Test
    void nullAndEmptyDoNotThrow() {
        StructuredDecodedView v = new StructuredDecodedView();
        assertDoesNotThrow(() -> v.setSource(null));
        assertDoesNotThrow(() -> v.setSource(""));
    }

    @Test
    void plainTextRendersWithoutThrowing() {
        StructuredDecodedView v = new StructuredDecodedView();
        assertDoesNotThrow(() -> v.setSource("No JSON-RPC calls found."));
        // No disclosure nodes for plain text input — it's not JSON.
        assertTrue(disclosuresIn(v).isEmpty());
    }

    @Test
    void malformedJsonFallsBackToText() {
        StructuredDecodedView v = new StructuredDecodedView();
        assertDoesNotThrow(() -> v.setSource("{not json"));
        // Should not produce a disclosure tree from malformed input.
        assertTrue(disclosuresIn(v).isEmpty());
    }

    @Test
    void singleEthCallProducesCallNodeWithChips() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{"
                + "\"to\":\"0xca11bde05977b3631167028862be2a173976ca11\","
                + "\"function\":\"swap(uint256,bool)\","
                + "\"args\":{\"amountIn\":1},"
                + "\"decodeSource\":\"cache\","
                + "\"status\":\"decoded\""
                + "}");
        assertFalse(disclosuresIn(v).isEmpty(), "expected at least one disclosure node");
        assertTrue(anyChipOfKind(v, StyleKind.SOURCE_CACHE), "expected SOURCE_CACHE chip");
        assertTrue(anyChipOfKind(v, StyleKind.STATUS_OK), "expected STATUS_OK chip");
    }

    @Test
    void batchArrayProducesOneRootNodePerElement() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("["
                + "{\"index\":0,\"status\":\"decoded\",\"function\":\"a()\"},"
                + "{\"index\":1,\"status\":\"skipped\",\"reason\":\"No ABI\"},"
                + "{\"index\":2,\"status\":\"error\",\"reason\":\"bad\"}"
                + "]");
        List<StructuredDecodedView.DisclosureNode> all = disclosuresIn(v);
        long topLevel = all.stream().filter(d -> !isNested(v, d)).count();
        assertEquals(3, topLevel, "expected 3 top-level disclosure nodes");
        assertTrue(anyChipOfKind(v, StyleKind.STATUS_OK));
        assertTrue(anyChipOfKind(v, StyleKind.STATUS_SKIPPED));
        assertTrue(anyChipOfKind(v, StyleKind.ERROR));
    }

    /** True when {@code node}'s parent chain contains another DisclosureNode somewhere above. */
    private static boolean isNested(Container root, StructuredDecodedView.DisclosureNode node) {
        Container p = node.getParent();
        while (p != null && p != root) {
            if (p instanceof StructuredDecodedView.DisclosureNode) return true;
            p = p.getParent();
        }
        return false;
    }

    @Test
    void nestedCallsRecurseAndCarryChips() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{"
                + "\"function\":\"aggregate3((address,bool,bytes)[])\","
                + "\"decodeSource\":\"builtin\","
                + "\"nestedCalls\":["
                + "  {\"depth\":1,\"target\":\"0xa0ffb9c1ce1fe56963b0321b32e7a0302114058b\","
                + "   \"status\":\"skipped\",\"reason\":\"No ABI found\"}"
                + "]"
                + "}");
        assertTrue(anyChipOfKind(v, StyleKind.SOURCE_BUILTIN), "expected SOURCE_BUILTIN chip on the root");
        assertTrue(anyChipOfKind(v, StyleKind.STATUS_SKIPPED), "expected STATUS_SKIPPED chip on the nested call");
        // The nested call's reason should be present as a (non-throwing) row.
        assertNotNull(v.getComponent(0));
    }

    @Test
    void unknownDecodeSourceDoesNotProduceChip() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{\"function\":\"x()\",\"decodeSource\":\"manual\",\"status\":\"decoded\"}");
        assertFalse(anyChipOfKind(v, StyleKind.SOURCE_CACHE));
        assertFalse(anyChipOfKind(v, StyleKind.SOURCE_ETHERSCAN));
        assertFalse(anyChipOfKind(v, StyleKind.SOURCE_FOURBYTE));
        assertFalse(anyChipOfKind(v, StyleKind.SOURCE_BUILTIN));
        assertTrue(anyChipOfKind(v, StyleKind.STATUS_OK));
    }

    @Test
    void expandAllAndCollapseAllAffectRootVisibility() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{"
                + "\"function\":\"top()\","
                + "\"nestedCalls\":["
                + "  {\"function\":\"inner()\",\"status\":\"decoded\"}"
                + "]"
                + "}");
        v.collapseAll();
        boolean anyExpanded = disclosuresIn(v).stream()
                .anyMatch(StructuredDecodedView.DisclosureNode::isExpanded);
        assertFalse(anyExpanded, "collapseAll should leave every node collapsed");

        v.expandAll();
        boolean allExpanded = disclosuresIn(v).stream()
                .allMatch(StructuredDecodedView.DisclosureNode::isExpanded);
        assertTrue(allExpanded, "expandAll should leave every node expanded");
    }

    @Test
    void depthAndAllowFailureAreHiddenFromBody() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{"
                + "\"function\":\"poolIdToPoolKey(bytes32)\","
                + "\"depth\":1,"
                + "\"target\":\"0xa0ffb9c1ce1fe56963b0321b32e7a0302114058b\","
                + "\"allowFailure\":true,"
                + "\"args\":{\"id\":\"0xfe\"}"
                + "}");
        for (Component c : labelsIn(v)) {
            if (c instanceof javax.swing.JLabel) {
                String txt = ((javax.swing.JLabel) c).getText();
                assertFalse("depth:".equals(txt), "depth field leaked into the body");
                assertFalse("allowFailure:".equals(txt), "allowFailure field leaked into the body");
            }
        }
    }

    @Test
    void proxyFieldRendersAsProxiedChipAndIsNotInBody() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{"
                + "\"function\":\"swap()\","
                + "\"proxy\":{\"implementation\":\"0xabc\"},"
                + "\"decodeSource\":\"cache\""
                + "}");
        assertTrue(chipsIn(v).stream().anyMatch(c -> c.kind() == StyleKind.STATUS_PROXIED),
                "expected PROXIED chip in header when proxy field present");
        // Walk the disclosure body and confirm no "proxy:" key row was rendered.
        boolean leakedProxyKey = false;
        for (java.awt.Component c : labelsIn(v)) {
            if (c instanceof javax.swing.JLabel) {
                String txt = ((javax.swing.JLabel) c).getText();
                if (txt != null && txt.startsWith("proxy")) {
                    leakedProxyKey = true;
                    break;
                }
            }
        }
        assertFalse(leakedProxyKey, "proxy field should not be rendered as a body row");
    }

    @Test
    void emptyObjectFieldRendersAsSingleScalarRow() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{\"function\":\"x()\",\"args\":{}}");
        // The "args" should NOT produce a nested disclosure node.
        boolean argsHasDisclosure = disclosuresIn(v).stream().anyMatch(d -> {
            for (java.awt.Component c : d.headerForTesting().getComponents()) {
                if (c instanceof javax.swing.JLabel
                        && "args:".equals(((javax.swing.JLabel) c).getText())) {
                    return true;
                }
            }
            return false;
        });
        assertFalse(argsHasDisclosure, "empty args should render inline, not as a disclosure");
    }

    private static List<java.awt.Component> labelsIn(java.awt.Container root) {
        List<java.awt.Component> out = new ArrayList<>();
        collectAll(root, out);
        return out;
    }

    private static void collectAll(java.awt.Container c, List<java.awt.Component> out) {
        for (java.awt.Component child : c.getComponents()) {
            out.add(child);
            if (child instanceof java.awt.Container) {
                collectAll((java.awt.Container) child, out);
            }
        }
    }

    @Test
    void setSourceCanBeCalledRepeatedlyWithDifferentShapes() {
        StructuredDecodedView v = new StructuredDecodedView();
        v.setSource("{\"function\":\"a()\"}");
        v.setSource("[{\"index\":0,\"status\":\"decoded\",\"function\":\"a()\"}]");
        v.setSource("plain text");
        v.setSource(null);
        v.setSource("{\"function\":\"b()\",\"decodeSource\":\"etherscan\"}");
        assertTrue(anyChipOfKind(v, StyleKind.SOURCE_ETHERSCAN));
    }
}
