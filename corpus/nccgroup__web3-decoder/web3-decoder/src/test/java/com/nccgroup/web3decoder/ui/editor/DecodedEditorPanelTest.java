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

class DecodedEditorPanelTest {

    @Test
    void constructsAndStartsOnStructuredCard() {
        DecodedEditorPanel p = assertDoesNotThrow(() -> new DecodedEditorPanel(true, null));
        assertNotNull(p.getComponent());
        assertEquals("structured", p.currentCardForTesting());
        assertTrue(p.structuredButtonForTesting().isSelected());
        assertFalse(p.jsonButtonForTesting().isSelected());
        assertTrue(p.expandButtonForTesting().isEnabled());
        assertTrue(p.collapseButtonForTesting().isEnabled());
    }

    @Test
    void setTextForwardsToJsonEditorAndUpdatesStructured() {
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        String json = "{\"to\":\"0xca11bde05977b3631167028862be2a173976ca11\","
                + "\"function\":\"swap(uint256,bool)\",\"decodeSource\":\"cache\",\"status\":\"decoded\"}";
        p.setText(json);
        assertEquals(json, p.getText());
        assertFalse(p.isModified(), "programmatic setText must not flip modified");
        // Structured view rendered chips for the new content.
        assertTrue(containsChipOfKind(p.structuredViewForTesting(), StyleKind.SOURCE_CACHE));
        assertTrue(containsChipOfKind(p.structuredViewForTesting(), StyleKind.STATUS_OK));
        // Summary picked up function + abbreviated to.
        assertEquals("swap(uint256,bool)", p.summaryForTesting().functionText());
        assertTrue(p.summaryForTesting().toText().startsWith("→ 0xca11"));
    }

    @Test
    void switchingToJsonShowsJsonCardAndDisablesExpandCollapse() {
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        p.setText("{\"function\":\"a()\"}");
        p.showCardForTesting("json");
        assertEquals("json", p.currentCardForTesting());
        assertTrue(p.jsonButtonForTesting().isSelected());
        assertFalse(p.structuredButtonForTesting().isSelected());
        assertFalse(p.expandButtonForTesting().isEnabled());
        assertFalse(p.collapseButtonForTesting().isEnabled());
    }

    @Test
    void switchingBackToStructuredReparsesCurrentJsonText() {
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        p.setText("{\"function\":\"a()\",\"decodeSource\":\"cache\"}");
        p.showCardForTesting("json");
        // Replace text directly via the JSON editor as if the user edited it.
        p.jsonEditorForTesting().setText("{\"function\":\"b()\",\"decodeSource\":\"etherscan\"}");
        p.showCardForTesting("structured");
        // The structured view should reflect the new decodeSource (etherscan), not the prior one.
        assertTrue(containsChipOfKind(p.structuredViewForTesting(), StyleKind.SOURCE_ETHERSCAN));
        assertFalse(containsChipOfKind(p.structuredViewForTesting(), StyleKind.SOURCE_CACHE));
    }

    @Test
    void plainTextDoesNotPopulateSummary() {
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        p.setText("No JSON-RPC calls found.");
        assertEquals("", p.summaryForTesting().functionText());
        assertEquals("", p.summaryForTesting().toText());
    }

    @Test
    void chainHintEnablesExplorerLinkOnAddresses() {
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        // Address-only row so the structured view renders an addressRow.
        p.setText("{\"to\":\"0xca11bde05977b3631167028862be2a173976ca11\"}");
        // No chain set → no link.
        assertFalse(hasNamedComponent(p.structuredViewForTesting(), "explorer-link"),
                "explorer link should not render without a chain hint");
        p.setChainHint(1);
        assertTrue(hasNamedComponent(p.structuredViewForTesting(), "explorer-link"),
                "explorer link should render after a known chain hint is set");
        p.setChainHint(-1);
        assertFalse(hasNamedComponent(p.structuredViewForTesting(), "explorer-link"),
                "explorer link should disappear after the chain hint is cleared");
    }

    @Test
    void unknownChainStillRendersAddressRowButNoLink() {
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        p.setText("{\"to\":\"0xca11bde05977b3631167028862be2a173976ca11\"}");
        // 999999 isn't in BlockExplorer's table → no link, even with a hint set.
        p.setChainHint(999999);
        assertFalse(hasNamedComponent(p.structuredViewForTesting(), "explorer-link"));
        // ...but a copy button still shows on the address row.
        assertTrue(hasNamedComponent(p.structuredViewForTesting(), "copy-button"));
    }

    private static boolean hasNamedComponent(Container root, String name) {
        for (Component c : root.getComponents()) {
            if (name.equals(c.getName())) return true;
            if (c instanceof Container && hasNamedComponent((Container) c, name)) return true;
        }
        return false;
    }

    @Test
    void readOnlyPanelConstructsWithoutThrowing() {
        DecodedEditorPanel p = assertDoesNotThrow(() -> new DecodedEditorPanel(false, null));
        p.setText("{\"function\":\"x()\"}");
        assertFalse(p.isModified());
    }

    @Test
    void getTextIsTheJsonEditorTextVerbatim() {
        // The re-encode path in Web3RequestEditor reads getText() and parses it back —
        // it must round-trip whatever was put in via setText, untouched.
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        String json = "[{\"index\":0,\"status\":\"decoded\",\"function\":\"a()\"}]";
        p.setText(json);
        assertEquals(json, p.getText());
    }

    @Test
    void topLevelArraySummaryStaysEmpty() {
        DecodedEditorPanel p = new DecodedEditorPanel(true, null);
        p.setText("[{\"index\":0,\"function\":\"a()\"}]");
        assertEquals("", p.summaryForTesting().functionText());
        assertEquals("", p.summaryForTesting().toText());
    }

    private static boolean containsChipOfKind(Container root, StyleKind kind) {
        for (StructuredDecodedView.Chip chip : collectChips(root)) {
            if (chip.kind() == kind) return true;
        }
        return false;
    }

    private static List<StructuredDecodedView.Chip> collectChips(Container root) {
        List<StructuredDecodedView.Chip> out = new ArrayList<>();
        walkChips(root, out);
        return out;
    }

    private static void walkChips(Container c, List<StructuredDecodedView.Chip> out) {
        for (Component child : c.getComponents()) {
            if (child instanceof StructuredDecodedView.Chip) {
                out.add((StructuredDecodedView.Chip) child);
            }
            if (child instanceof Container) {
                walkChips((Container) child, out);
            }
        }
    }
}
