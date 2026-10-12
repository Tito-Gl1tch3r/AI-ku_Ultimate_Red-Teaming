package com.nccgroup.web3decoder.ui;

import javax.swing.BorderFactory;
import javax.swing.BoxLayout;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.SwingConstants;
import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.Dimension;

/**
 * Attached panel header bar: left-aligned bold uppercase title, optional
 * mono-dim subtitle next to the title, optional right-aligned trailing
 * component (used by the ABI Editor to dock its Save button into the header).
 * Replaces the floating centered JLabels the original UI used. Theme-aware
 * via {@link Web3UiTheme}.
 */
class PanelHeader extends JPanel {

    private final JLabel titleLabel;
    private final JLabel subtitleLabel;
    private final JPanel trailingSlot;

    PanelHeader(String title) {
        this(title, null);
    }

    PanelHeader(String title, String subtitle) {
        super(new BorderLayout(8, 0));
        setOpaque(true);
        setBackground(Web3UiTheme.panelHeaderBg());
        setBorder(BorderFactory.createCompoundBorder(
                Web3UiTheme.headerBottomDivider(),
                BorderFactory.createEmptyBorder(
                        Web3UiTheme.headerInsets().top,
                        Web3UiTheme.headerInsets().left,
                        Web3UiTheme.headerInsets().bottom,
                        Web3UiTheme.headerInsets().right)));

        JPanel left = new JPanel();
        left.setOpaque(false);
        left.setLayout(new BoxLayout(left, BoxLayout.X_AXIS));

        titleLabel = new JLabel(title == null ? "" : title.toUpperCase());
        titleLabel.setFont(Web3UiTheme.panelTitleFont(titleLabel.getFont()));
        titleLabel.setAlignmentY(Component.CENTER_ALIGNMENT);
        left.add(titleLabel);

        subtitleLabel = new JLabel(subtitle == null ? "" : subtitle);
        subtitleLabel.setForeground(Web3UiTheme.mutedFg());
        subtitleLabel.setFont(Web3UiTheme.monoFont(subtitleLabel.getFont(), 11f));
        subtitleLabel.setHorizontalAlignment(SwingConstants.LEFT);
        subtitleLabel.setAlignmentY(Component.CENTER_ALIGNMENT);
        subtitleLabel.setBorder(BorderFactory.createEmptyBorder(0, 10, 0, 0));
        subtitleLabel.setVisible(subtitle != null && !subtitle.isEmpty());
        left.add(subtitleLabel);

        add(left, BorderLayout.WEST);

        trailingSlot = new JPanel();
        trailingSlot.setOpaque(false);
        trailingSlot.setLayout(new BoxLayout(trailingSlot, BoxLayout.X_AXIS));
        add(trailingSlot, BorderLayout.EAST);
    }

    void setSubtitle(String subtitle) {
        if (subtitle == null || subtitle.isEmpty()) {
            subtitleLabel.setText("");
            subtitleLabel.setVisible(false);
        } else {
            subtitleLabel.setText(subtitle);
            subtitleLabel.setVisible(true);
        }
    }

    /** Dock a component (typically a button) to the header's right side. */
    void setTrailing(JComponent component) {
        trailingSlot.removeAll();
        if (component != null) {
            trailingSlot.add(component);
        }
        trailingSlot.revalidate();
        trailingSlot.repaint();
    }

    @Override
    public Dimension getMaximumSize() {
        Dimension pref = getPreferredSize();
        return new Dimension(Integer.MAX_VALUE, pref.height);
    }
}
