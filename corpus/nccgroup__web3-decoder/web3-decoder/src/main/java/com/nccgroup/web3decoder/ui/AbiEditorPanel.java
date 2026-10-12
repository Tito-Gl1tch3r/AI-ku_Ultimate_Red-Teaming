// File: AbiEditorPanel.java
package com.nccgroup.web3decoder.ui;

import burp.api.montoya.MontoyaApi;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.ObjectWriter;
import com.nccgroup.web3decoder.ui.editor.Web3JsonEditor;

import javax.swing.*;
import java.awt.*;

public class AbiEditorPanel extends JPanel {
    private final Web3JsonEditor abiEditor;
    private JButton saveButton;
    private JLabel chainAndContractLabel; // Label for chain ID and contract address

    private int currentChainId = -1;
    private String currentContractAddress = null;
    private AbiSaveListener abiSaveListener;

    /**
     * Listener interface for ABI save events.
     */
    public interface AbiSaveListener {
        void onAbiSave(int chainId, String contractAddress, String abi);
    }

    /**
     * Sets the AbiSaveListener.
     *
     * @param listener The listener to set.
     */
    public void setAbiSaveListener(AbiSaveListener listener) {
        this.abiSaveListener = listener;
    }

    /**
     * Constructs the AbiEditorPanel.
     *
     * @param api The MontoyaApi instance.
     */
    public AbiEditorPanel(MontoyaApi api) {
        this.abiEditor = new Web3JsonEditor(true, api.logging());
        initializeUI();
    }

    /**
     * Initializes the UI components for the AbiEditorPanel. The header label
     * and Save button are *owned* by this panel but exposed via accessors so
     * the parent can dock them into a unified panel header — keeping the
     * editor body free of inline title/button rows.
     */
    private void initializeUI() {
        setLayout(new BorderLayout());

        // Header-bound label (mounted into the wrapping PanelHeader's subtitle slot
        // by the parent). Kept as a field so set*() methods can update its text.
        chainAndContractLabel = new JLabel();
        chainAndContractLabel.setForeground(Web3UiTheme.mutedFg());

        // Header-bound Save button (also mounted into the wrapping PanelHeader).
        saveButton = new JButton("Save");
        saveButton.setToolTipText("Save the edited ABI.");
        saveButton.setEnabled(false);
        styleAsAccent(saveButton);
        saveButton.addActionListener(e -> saveAbi());

        // ABI Editor body fills the panel.
        abiEditor.setEditable(true);
        add(abiEditor.getComponent(), BorderLayout.CENTER);
    }

    /** Subtitle label intended for the host PanelHeader's subtitle slot. */
    public JLabel getContextLabel() {
        return chainAndContractLabel;
    }

    /** Save button intended for the host PanelHeader's trailing slot. */
    public JButton getSaveButton() {
        return saveButton;
    }

    private static void styleAsAccent(JButton button) {
        button.setBackground(Web3UiTheme.accent());
        button.setForeground(Web3UiTheme.accentForeground());
        button.setFont(button.getFont().deriveFont(Font.BOLD));
        button.setFocusPainted(false);
        button.setOpaque(true);
        // FlatLaf honors a custom button background only if the button isn't
        // forced into "default" style; the line above keeps it consistent
        // under both themes.
    }

    /**
     * Sets the ABI details to be displayed and edited in the editor.
     *
     * @param chainId         The chain ID of the ABI.
     * @param contractAddress The contract address of the ABI.
     * @param abi             The ABI string to display.
     */
    public void setAbi(int chainId, String contractAddress, String abi) {
        this.currentChainId = chainId;
        this.currentContractAddress = contractAddress;

        // Format the ABI JSON for pretty display
        String formattedAbi = formatJson(abi);

        // Set the ABI content in the editor
        abiEditor.setText(formattedAbi);
        abiEditor.setEditable(true);

        // Enable or disable the Save button based on whether a valid ABI is loaded
        if (chainId != -1 && contractAddress != null && !contractAddress.isEmpty()) {
            saveButton.setEnabled(true);
            chainAndContractLabel.setText("Chain " + chainId + "  ·  " + contractAddress);
        } else {
            saveButton.setEnabled(false);
            chainAndContractLabel.setText("");
        }
    }

    /**
     * Show a detected ABI in read-only mode (no chain/address context to save against).
     * Header label describes the origin so the user can see what they're looking at.
     */
    public void setDetectedAbi(String fingerprint, String firstSeenUrl, String abi) {
        this.currentChainId = -1;
        this.currentContractAddress = null;
        String formattedAbi = formatJson(abi);
        abiEditor.setText(formattedAbi);
        abiEditor.setEditable(false);
        saveButton.setEnabled(false);
        String shortFp = fingerprint == null || fingerprint.length() < 12
                ? String.valueOf(fingerprint)
                : fingerprint.substring(0, 12) + "…";
        String urlSuffix = (firstSeenUrl == null || firstSeenUrl.isEmpty())
                ? ""
                : " (from " + firstSeenUrl + ")";
        chainAndContractLabel.setText("Detected ABI: " + shortFp + urlSuffix);
    }

    /**
     * Saves the edited ABI.
     */
    private void saveAbi() {
        if (abiSaveListener != null) {
            String editedAbi = abiEditor.getText().trim();

            // Validate that the edited ABI is valid JSON
            if (!isValidJson(editedAbi)) {
                JOptionPane.showMessageDialog(this, "Invalid ABI format. Please ensure it is valid JSON.", 
                                        "Input Error", JOptionPane.ERROR_MESSAGE);
                return;
            }

            // Minify the JSON before saving
            String minifiedAbi = minifyJson(editedAbi);

            abiSaveListener.onAbiSave(currentChainId, currentContractAddress, minifiedAbi);
        }
    }

    /**
     * Formats a JSON string with indentation for pretty display.
     *
     * @param jsonStr The JSON string to format.
     * @return The formatted JSON string.
     */
    private String formatJson(String jsonStr) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            Object json = mapper.readValue(jsonStr, Object.class);
            ObjectWriter writer = mapper.writerWithDefaultPrettyPrinter();
            return writer.writeValueAsString(json);
        } catch (Exception e) {
            // If formatting fails, return the original string
            return jsonStr;
        }
    }

    /**
     * Minifies a JSON string by removing unnecessary whitespace.
     *
     * @param jsonStr The JSON string to minify.
     * @return The minified JSON string.
     */
    private String minifyJson(String jsonStr) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            Object json = mapper.readValue(jsonStr, Object.class);
            return mapper.writeValueAsString(json);
        } catch (Exception e) {
            // If minifying fails, return the original string
            return jsonStr;
        }
    }

    /**
     * Validates whether a string is valid JSON.
     *
     * @param jsonStr The JSON string to validate.
     * @return true if valid JSON, false otherwise.
     */
    private boolean isValidJson(String jsonStr) {
        try {
            new ObjectMapper().readTree(jsonStr);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
