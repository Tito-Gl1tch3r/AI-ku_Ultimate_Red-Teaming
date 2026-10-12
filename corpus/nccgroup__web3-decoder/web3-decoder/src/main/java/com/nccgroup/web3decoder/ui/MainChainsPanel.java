// File: MainChainsPanel.java
package com.nccgroup.web3decoder.ui;

import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.CachedAbis;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import burp.api.montoya.MontoyaApi;

import javax.swing.BorderFactory;
import javax.swing.JComponent;
import javax.swing.JPanel;
import javax.swing.JSplitPane;
import java.awt.BorderLayout;
import java.awt.event.ComponentAdapter;

/**
 * Single Burp "Web3" tab. Layout:
 *   NORTH:  SettingsPanel (full-width Settings group)
 *   CENTER: horizontal split
 *           ├─ left: vertical split → Chains  +  (Cached | Detected) ABIs
 *           └─ right: vertical split → ABI Editor  +  Manual Decoder
 *
 * All grouped sections are wrapped with {@link PanelHeader}; action buttons
 * live inside their owning panel's toolbar (no floating buttons between
 * sections). Theme-aware via {@link Web3UiTheme}.
 */
public class MainChainsPanel extends JPanel {
    private final ExtensionConfig config;
    private final CachedAbis cachedAbis;

    private final ChainsListPanel chainsListPanel;
    private final CachedAbisListPanel cachedAbisListPanel;
    private final DetectedAbisListPanel detectedAbisListPanel;
    private final AbiEditorPanel abiEditorPanel;
    private final CalldataCodecPanel calldataCodecPanel;

    public MainChainsPanel(MontoyaApi api, ExtensionConfig config) {
        this(api, config, null);
    }

    public MainChainsPanel(MontoyaApi api, ExtensionConfig config, DetectedAbiStore detectedAbiStore) {
        this.config = config;
        this.cachedAbis = new CachedAbis(api);

        this.chainsListPanel = new ChainsListPanel(api, config);
        this.cachedAbisListPanel = new CachedAbisListPanel(api, config, cachedAbis);
        this.detectedAbisListPanel = detectedAbiStore == null
                ? null : new DetectedAbisListPanel(api, detectedAbiStore);
        this.abiEditorPanel = new AbiEditorPanel(api);
        this.calldataCodecPanel = new CalldataCodecPanel(api, config, cachedAbis, detectedAbiStore);

        initializeUI();
        loadData();

        addComponentListener(new ComponentAdapter() {
            @Override
            public void componentShown(java.awt.event.ComponentEvent e) {
                refreshCachedAbisList();
            }
        });
    }

    private void refreshCachedAbisList() {
        cachedAbisListPanel.loadData();
        if (detectedAbisListPanel != null) detectedAbisListPanel.loadData();
    }

    private void initializeUI() {
        setLayout(new BorderLayout(0, Web3UiTheme.GAP));
        setBorder(BorderFactory.createEmptyBorder(
                Web3UiTheme.OUTER_PADDING,
                Web3UiTheme.OUTER_PADDING,
                Web3UiTheme.OUTER_PADDING,
                Web3UiTheme.OUTER_PADDING));

        add(new SettingsPanel(config), BorderLayout.NORTH);

        // ---- LEFT column ----
        JComponent chainsGroup = wrap("Chains & API Keys", null, chainsListPanel, null);

        JComponent abisRow;
        if (detectedAbisListPanel != null) {
            JSplitPane abisSplit = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT,
                    wrap("Cached ABIs", null, cachedAbisListPanel, null),
                    wrap("Detected ABIs", "passive", detectedAbisListPanel, null));
            abisSplit.setResizeWeight(0.5);
            abisSplit.setContinuousLayout(true);
            abisSplit.setBorder(null);
            abisRow = abisSplit;
        } else {
            abisRow = wrap("Cached ABIs", null, cachedAbisListPanel, null);
        }

        JSplitPane leftSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, chainsGroup, abisRow);
        leftSplit.setResizeWeight(0.58);
        leftSplit.setContinuousLayout(true);
        leftSplit.setBorder(null);

        // ---- RIGHT column ----
        // ABI Editor: its Save button + context subtitle are docked into the
        // unified header instead of living inside the editor panel.
        PanelHeader editorHeader = new PanelHeader("ABI Editor");
        editorHeader.setTrailing(abiEditorPanel.getSaveButton());
        abiEditorPanel.getContextLabel().addPropertyChangeListener("text",
                e -> editorHeader.setSubtitle((String) e.getNewValue()));
        editorHeader.setSubtitle(abiEditorPanel.getContextLabel().getText());
        JComponent editorGroup = wrapWithHeader(editorHeader, abiEditorPanel);

        JComponent decoderGroup = wrap("Manual Decoder", "Calldata decode / re-encode",
                calldataCodecPanel, null);

        JSplitPane rightSplit = new JSplitPane(JSplitPane.VERTICAL_SPLIT, editorGroup, decoderGroup);
        rightSplit.setResizeWeight(0.72);
        rightSplit.setContinuousLayout(true);
        rightSplit.setBorder(null);

        // ---- Main split ----
        JSplitPane mainSplit = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, leftSplit, rightSplit);
        mainSplit.setResizeWeight(0.46);
        mainSplit.setContinuousLayout(true);
        mainSplit.setBorder(null);
        add(mainSplit, BorderLayout.CENTER);

        // ---- Selection wiring (preserved) ----
        cachedAbisListPanel.setAbiSelectionListener((chainId, contractAddress, abi) -> {
            abiEditorPanel.setAbi(chainId, contractAddress, abi);
            calldataCodecPanel.setContext(chainId, contractAddress, abi);
        });
        if (detectedAbisListPanel != null) {
            detectedAbisListPanel.setSelectionListener((fingerprint, firstSeenUrl, abi) -> {
                if (fingerprint == null) {
                    abiEditorPanel.setAbi(-1, null, "");
                } else {
                    abiEditorPanel.setDetectedAbi(fingerprint, firstSeenUrl, abi);
                }
            });
        }
        abiEditorPanel.setAbiSaveListener(cachedAbisListPanel);
    }

    private void loadData() {
        chainsListPanel.loadData();
        cachedAbisListPanel.loadData();
    }

    /**
     * Wraps a child panel inside a bordered group with an attached header bar.
     */
    private static JComponent wrap(String title, String subtitle, JPanel child, JComponent trailing) {
        PanelHeader header = new PanelHeader(title, subtitle);
        if (trailing != null) header.setTrailing(trailing);
        return wrapWithHeader(header, child);
    }

    private static JComponent wrapWithHeader(PanelHeader header, JPanel child) {
        JPanel group = new JPanel(new BorderLayout());
        group.setBorder(Web3UiTheme.panelBorder());
        group.add(header, BorderLayout.NORTH);
        group.add(child, BorderLayout.CENTER);
        return group;
    }
}
