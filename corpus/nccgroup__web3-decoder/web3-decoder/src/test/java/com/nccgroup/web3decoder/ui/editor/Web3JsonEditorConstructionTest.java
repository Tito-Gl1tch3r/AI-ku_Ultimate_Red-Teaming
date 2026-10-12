package com.nccgroup.web3decoder.ui.editor;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * Headless smoke tests for the editor's construction and basic wiring. These guard the
 * class of bug where {@code JPanel}'s constructor calls {@code updateUI()} before the
 * {@code panel} field is assigned — which previously threw an NPE in {@code applyTheme()}.
 */
class Web3JsonEditorConstructionTest {

    @Test
    void constructsWithoutThrowing() {
        Web3JsonEditor editor = assertDoesNotThrow(() -> new Web3JsonEditor(true, null));
        assertNotNull(editor.getComponent());
    }

    @Test
    void readOnlyConstructsWithoutThrowing() {
        assertDoesNotThrow(() -> new Web3JsonEditor(false, null));
    }

    @Test
    void programmaticSetTextDoesNotMarkModified() {
        Web3JsonEditor editor = new Web3JsonEditor(true, null);
        String json = "{\"function\":\"swap(uint256,bool)\"}";
        editor.setText(json);
        assertEquals(json, editor.getText());
        assertFalse(editor.isModified());
    }
}
