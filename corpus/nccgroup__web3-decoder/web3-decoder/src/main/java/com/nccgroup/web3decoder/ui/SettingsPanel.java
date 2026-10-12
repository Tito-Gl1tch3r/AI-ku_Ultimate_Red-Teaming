package com.nccgroup.web3decoder.ui;

import com.nccgroup.web3decoder.persistence.ExtensionConfig;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JCheckBox;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JSeparator;
import javax.swing.SwingConstants;
import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;

/**
 * The "Settings" group at the top of the Web3 tab. Splits toggles into two
 * columns separated by a vertical divider: <b>General</b> (annotation) and
 * <b>External data sources</b> (block explorer + 4byte). Both external
 * toggles carry a small "EXTERNAL" tag so users know they reach the internet.
 */
class SettingsPanel extends JPanel {

    SettingsPanel(ExtensionConfig config) {
        super(new BorderLayout());
        setBorder(BorderFactory.createCompoundBorder(
                Web3UiTheme.panelBorder(),
                BorderFactory.createEmptyBorder()));

        PanelHeader header = new PanelHeader("Settings", "Applies to all decoded Web3 traffic");
        add(header, BorderLayout.NORTH);

        JPanel body = new JPanel(new GridBagLayout());
        body.setBorder(BorderFactory.createEmptyBorder(8, 14, 10, 14));

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.gridy = 0;
        gbc.fill = GridBagConstraints.BOTH;
        gbc.anchor = GridBagConstraints.NORTHWEST;

        // ---- General column ----
        gbc.gridx = 0;
        gbc.weightx = 0;
        gbc.insets = new Insets(0, 0, 0, 18);
        body.add(buildGeneralColumn(config), gbc);

        // ---- Vertical divider ----
        gbc.gridx = 1;
        gbc.weightx = 0;
        gbc.insets = new Insets(2, 0, 2, 0);
        JSeparator divider = new JSeparator(SwingConstants.VERTICAL);
        divider.setForeground(Web3UiTheme.dividerColor());
        divider.setPreferredSize(new Dimension(1, 1));
        body.add(divider, gbc);

        // ---- External column ----
        gbc.gridx = 2;
        gbc.weightx = 1.0;
        gbc.insets = new Insets(0, 18, 0, 0);
        body.add(buildExternalColumn(config), gbc);

        add(body, BorderLayout.CENTER);
    }

    private JPanel buildGeneralColumn(ExtensionConfig config) {
        JPanel col = new JPanel();
        col.setLayout(new BoxLayout(col, BoxLayout.Y_AXIS));
        col.setOpaque(false);
        col.add(sectionLabel("General"));
        col.add(toggle(
                "Annotate Web3 traffic in history",
                "Tag and highlight decoded Web3 requests in Proxy history.",
                false,
                config.isHistoryAnnotationEnabled(),
                config::setHistoryAnnotationEnabled));
        return col;
    }

    private JPanel buildExternalColumn(ExtensionConfig config) {
        JPanel col = new JPanel();
        col.setLayout(new BoxLayout(col, BoxLayout.Y_AXIS));
        col.setOpaque(false);
        col.add(sectionLabel("External data sources"));

        JPanel toggleRow = new JPanel();
        toggleRow.setLayout(new BoxLayout(toggleRow, BoxLayout.X_AXIS));
        toggleRow.setOpaque(false);
        toggleRow.setAlignmentX(Component.LEFT_ALIGNMENT);

        JPanel blockExplorer = toggle(
                "Search ABIs in Block Explorers",
                "Fetch verified contract ABIs from Etherscan-compatible explorers.",
                true,
                config.isBlockExplorerLookupEnabled(),
                config::setBlockExplorerLookupEnabled);
        blockExplorer.setAlignmentY(Component.TOP_ALIGNMENT);
        toggleRow.add(blockExplorer);

        toggleRow.add(Box.createHorizontalStrut(22));

        JPanel fourByte = toggle(
                "Search selectors in 4Byte database",
                "Resolve unknown function selectors via the 4byte.directory API.",
                true,
                config.isFourByteLookupEnabled(),
                config::setFourByteLookupEnabled);
        fourByte.setAlignmentY(Component.TOP_ALIGNMENT);
        toggleRow.add(fourByte);

        toggleRow.add(Box.createHorizontalGlue());
        col.add(toggleRow);
        return col;
    }

    private JLabel sectionLabel(String text) {
        JLabel label = new JLabel(text.toUpperCase());
        label.setForeground(Web3UiTheme.mutedFg());
        label.setFont(label.getFont().deriveFont(label.getFont().getStyle() | java.awt.Font.BOLD,
                Math.max(10f, label.getFont().getSize2D() - 2f)));
        label.setBorder(BorderFactory.createEmptyBorder(0, 0, 4, 0));
        label.setAlignmentX(Component.LEFT_ALIGNMENT);
        return label;
    }

    private JPanel toggle(String title, String description, boolean external,
                          boolean initiallyOn, java.util.function.Consumer<Boolean> onChange) {
        JPanel row = new JPanel();
        row.setLayout(new BoxLayout(row, BoxLayout.Y_AXIS));
        row.setOpaque(false);
        row.setAlignmentX(Component.LEFT_ALIGNMENT);
        row.setBorder(BorderFactory.createEmptyBorder(0, 0, 4, 0));

        JPanel titleRow = new JPanel();
        titleRow.setOpaque(false);
        titleRow.setLayout(new BoxLayout(titleRow, BoxLayout.X_AXIS));
        titleRow.setAlignmentX(Component.LEFT_ALIGNMENT);

        JCheckBox checkbox = new JCheckBox(title, initiallyOn);
        checkbox.setOpaque(false);
        checkbox.setAlignmentY(Component.CENTER_ALIGNMENT);
        checkbox.addActionListener(e -> onChange.accept(checkbox.isSelected()));
        titleRow.add(checkbox);

        if (external) {
            titleRow.add(Box.createHorizontalStrut(6));
            titleRow.add(externalTag());
        }
        row.add(titleRow);

        if (description != null && !description.isEmpty()) {
            JLabel desc = new JLabel(description);
            desc.setForeground(Web3UiTheme.mutedFg());
            desc.setFont(desc.getFont().deriveFont(desc.getFont().getSize2D() - 1f));
            desc.setBorder(BorderFactory.createEmptyBorder(0, 22, 0, 0));
            desc.setAlignmentX(Component.LEFT_ALIGNMENT);
            row.add(desc);
        }
        return row;
    }

    private JLabel externalTag() {
        JLabel tag = new JLabel("EXTERNAL");
        tag.setForeground(Web3UiTheme.mutedFg());
        tag.setFont(tag.getFont().deriveFont(java.awt.Font.BOLD,
                Math.max(9f, tag.getFont().getSize2D() - 3f)));
        tag.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(Web3UiTheme.dividerColor(), 1, true),
                BorderFactory.createEmptyBorder(1, 5, 1, 5)));
        tag.setAlignmentY(Component.CENTER_ALIGNMENT);
        return tag;
    }
}
