package com.nccgroup.web3decoder.ui.editor;

import burp.api.montoya.logging.Logging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import javax.swing.BorderFactory;
import javax.swing.ButtonGroup;
import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JToggleButton;
import javax.swing.UIManager;
import javax.swing.border.EmptyBorder;

import java.awt.BorderLayout;
import java.awt.CardLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridLayout;
import java.awt.Insets;

/**
 * Composite editor pane that wraps the existing {@link Web3JsonEditor} (the editable
 * source of truth) with a read-only {@link StructuredDecodedView} and a top control bar:
 *
 * <ul>
 *   <li>NORTH: summary chips (chain · function · to) + segmented JSON / Structured toggle
 *       + Expand all / Collapse all (active only in Structured mode).</li>
 *   <li>CENTER: a {@link CardLayout} switching between the Structured tree (default) and
 *       the JSON editor.</li>
 * </ul>
 *
 * The JSON editor is the single source of truth — every {@link #setText(String)} forwards
 * to it AND rebuilds the structured projection from the same text. Toggling to Structured
 * re-parses from {@link Web3JsonEditor#getText()} so edits made in the JSON card are
 * always reflected. The structured view never feeds the re-encode path; callers should
 * keep calling {@link #getText()} which returns the JSON editor's text verbatim.
 */
public final class DecodedEditorPanel {

    private static final String CARD_STRUCTURED = "structured";
    private static final String CARD_JSON = "json";

    private final ObjectMapper mapper = new ObjectMapper();
    private final Web3JsonEditor jsonEditor;
    private final StructuredDecodedView structuredView = new StructuredDecodedView();
    private final SummaryBar summary = new SummaryBar();
    private final JToggleButton structuredBtn = new JToggleButton("Structured", true);
    private final JToggleButton jsonBtn = new JToggleButton("JSON");
    private final JButton expandBtn = new JButton("Expand");
    private final JButton collapseBtn = new JButton("Collapse");
    private final CardLayout cards = new CardLayout();
    private final JPanel body = new JPanel(cards);

    private final JPanel panel = new JPanel(new BorderLayout()) {
        @Override
        public void updateUI() {
            super.updateUI();
            // updateUI() fires from JPanel's own constructor before the outer `panel`
            // field is assigned. applyTheme() dereferences `panel`, so skip until it's
            // set; the constructor's explicit applyTheme() handles initial theming.
            // After construction this runs on genuine Look-and-Feel (light/dark) changes.
            if (panel != null) {
                applyTheme();
            }
        }
    };

    private TopBarLayoutPanel topBar;
    private EditorTheme theme = EditorTheme.resolve();
    private String currentText = "";
    private String currentCard = CARD_STRUCTURED;

    public DecodedEditorPanel(boolean editable, Logging logging) {
        this.jsonEditor = new Web3JsonEditor(editable, logging);

        body.add(structuredView, CARD_STRUCTURED);
        body.add(jsonEditor.getComponent(), CARD_JSON);

        wireToggles();
        wireExpandCollapse();

        buildTopBar();
        panel.add(topBar, BorderLayout.NORTH);
        panel.add(body, BorderLayout.CENTER);

        showCard(CARD_STRUCTURED);
        applyTheme();
    }

    // ---- public API (mirrors what callers used from Web3JsonEditor) ----

    public Component getComponent() {
        return panel;
    }

    public void setText(String text) {
        this.currentText = text != null ? text : "";
        jsonEditor.setText(currentText);
        structuredView.setSource(currentText);
        refreshSummary();
    }

    public String getText() {
        // The JSON editor is the source of truth — re-encode paths read this verbatim.
        return jsonEditor.getText();
    }

    public void setEditable(boolean editable) {
        jsonEditor.setEditable(editable);
    }

    public boolean isModified() {
        return jsonEditor.isModified();
    }

    public String getSelectedText() {
        return jsonEditor.getSelectedText();
    }

    public int selectionStart() {
        return jsonEditor.selectionStart();
    }

    /**
     * Hint the chain id of the decoded request. Wires the structured view's address
     * "explorer ↗" link to the matching block explorer. Pass &lt;= 0 to disable links.
     */
    public void setChainHint(int chainId) {
        if (chainId > 0) {
            structuredView.setAddressExplorerBuilder(addr -> BlockExplorer.addressUrl(chainId, addr));
        } else {
            structuredView.setAddressExplorerBuilder(null);
        }
        refreshSummary();
    }

    // ---- internals ----

    private void wireToggles() {
        ButtonGroup group = new ButtonGroup();
        group.add(structuredBtn);
        group.add(jsonBtn);
        structuredBtn.addActionListener(e -> showCard(CARD_STRUCTURED));
        jsonBtn.addActionListener(e -> showCard(CARD_JSON));
        Font small = compactButtonFont();
        for (JToggleButton b : new JToggleButton[] { structuredBtn, jsonBtn }) {
            b.setFocusPainted(false);
            b.setMargin(new Insets(2, 8, 2, 8));
            if (small != null) b.setFont(small);
        }
    }

    private void wireExpandCollapse() {
        expandBtn.addActionListener(e -> structuredView.expandAll());
        collapseBtn.addActionListener(e -> structuredView.collapseAll());
        Font small = compactButtonFont();
        for (JButton b : new JButton[] { expandBtn, collapseBtn }) {
            b.setFocusPainted(false);
            b.setMargin(new Insets(2, 8, 2, 8));
            if (small != null) b.setFont(small);
        }
    }

    private static Font compactButtonFont() {
        Font base = UIManager.getFont("Button.font");
        if (base == null) return null;
        return base.deriveFont((float) Math.max(11, base.getSize() - 1));
    }

    private void showCard(String name) {
        this.currentCard = name;
        if (CARD_STRUCTURED.equals(name)) {
            // Re-parse current JSON text so edits made on the JSON card show up.
            structuredView.setSource(jsonEditor.getText());
            refreshSummary();
        }
        cards.show(body, name);
        boolean structured = CARD_STRUCTURED.equals(name);
        expandBtn.setEnabled(structured);
        collapseBtn.setEnabled(structured);
        structuredBtn.setSelected(structured);
        jsonBtn.setSelected(!structured);
    }

    private void refreshSummary() {
        String fn = null;
        String to = null;
        try {
            String text = jsonEditor.getText();
            if (text != null && !text.isEmpty()) {
                String trimmed = text.trim();
                if (!trimmed.isEmpty() && (trimmed.charAt(0) == '{' || trimmed.charAt(0) == '[')) {
                    JsonNode root = mapper.readTree(text);
                    if (root != null && root.isObject()) {
                        JsonNode fnNode = root.get("function");
                        if (fnNode != null && fnNode.isTextual()) fn = fnNode.asText();
                        JsonNode toNode = root.get("to");
                        if (toNode != null && toNode.isTextual()) to = toNode.asText();
                    }
                }
            }
        } catch (Exception ignored) {
            // Malformed JSON: leave summary empty.
        }
        summary.update(fn, to);
    }

    private JPanel buildTopBar() {
        JPanel right = new JPanel(new FlowLayout(FlowLayout.RIGHT, 6, 0));
        right.setOpaque(false);

        JPanel seg = new JPanel(new GridLayout(1, 2, 0, 0));
        seg.setBorder(BorderFactory.createLineBorder(borderColor()));
        seg.add(jsonBtn);
        seg.add(structuredBtn);
        right.add(seg);
        right.add(expandBtn);
        right.add(collapseBtn);

        topBar = new TopBarLayoutPanel(summary, right);
        applyTopBarChrome();
        return topBar;
    }

    private void applyTopBarChrome() {
        if (topBar == null) return;
        topBar.setBackground(headerBg());
        topBar.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createMatteBorder(0, 0, 1, 0, borderColor()),
                new EmptyBorder(6, 12, 6, 12)));
    }

    private void applyTheme() {
        theme = EditorTheme.resolve();
        Color bg = panelBg();
        panel.setBackground(bg);
        for (Component c : panel.getComponents()) {
            if (c instanceof JPanel) {
                ((JPanel) c).setOpaque(true);
                // The top bar paints itself with the header background; everything else
                // inherits the panel background.
                if (c != topBar) {
                    c.setBackground(bg);
                }
                for (Component cc : ((JPanel) c).getComponents()) {
                    if (cc instanceof JPanel && cc != topBar) cc.setBackground(bg);
                }
            }
        }
        applyTopBarChrome();
        summary.applyTheme(theme);
        panel.repaint();
    }

    private Color panelBg() {
        Color c = UIManager.getColor("Panel.background");
        return c != null ? c : theme.background;
    }

    private Color headerBg() {
        // The "header strip" colour FlatLaf uses for table headers and tab strips —
        // a slightly darker (dark theme) or lighter (light theme) shade than the panel
        // body, exactly the visual separation the mock calls for.
        Color c = UIManager.getColor("TableHeader.background");
        if (c != null) return c;
        c = UIManager.getColor("ToolBar.background");
        if (c != null) return c;
        return panelBg();
    }

    private Color borderColor() {
        Color c = UIManager.getColor("Component.borderColor");
        if (c != null) return c;
        c = UIManager.getColor("Separator.foreground");
        return c != null ? c : new Color(80, 84, 88);
    }

    // ---- inner classes ----

    /** Left-side cluster: top-level function signature + abbreviated "to" address. */
    static final class SummaryBar extends JPanel {

        private final JLabel fnLabel = new JLabel();
        private final JLabel toLabel = new JLabel();

        SummaryBar() {
            super(new FlowLayout(FlowLayout.LEFT, 9, 0));
            setOpaque(false);
            fnLabel.setVisible(false);
            toLabel.setVisible(false);
            add(fnLabel);
            add(toLabel);
        }

        void applyTheme(EditorTheme theme) {
            Font mono = theme.font;
            fnLabel.setForeground(theme.color(StyleKind.FUNCTION));
            fnLabel.setFont(mono.deriveFont(Font.BOLD));
            toLabel.setForeground(theme.color(StyleKind.ADDRESS));
            toLabel.setFont(mono);
        }

        void update(String functionSignature, String toAddress) {
            if (functionSignature != null && !functionSignature.isEmpty()) {
                fnLabel.setText(functionSignature);
                fnLabel.setVisible(true);
            } else {
                fnLabel.setText("");
                fnLabel.setVisible(false);
            }
            if (toAddress != null && !toAddress.isEmpty()) {
                toLabel.setText("→ " + abbreviateAddress(toAddress));
                toLabel.setVisible(true);
            } else {
                toLabel.setText("");
                toLabel.setVisible(false);
            }
            revalidate();
            repaint();
        }

        String functionText() {
            return fnLabel.getText();
        }

        String toText() {
            return toLabel.getText();
        }

        private static String abbreviateAddress(String addr) {
            if (addr == null || addr.length() <= 12) return addr;
            return addr.substring(0, 6) + "…" + addr.substring(addr.length() - 4);
        }
    }

    /**
     * Two-child layout for the top bar: left summary + right controls, vertically centered
     * side-by-side when they fit; when too narrow, the controls cluster wraps above the
     * summary so neither side gets clipped or overlaps. Reports the right preferred height
     * for the current parent width so the enclosing BorderLayout NORTH slot resizes with it.
     */
    static final class TopBarLayoutPanel extends JPanel {

        private static final int HGAP = 14;
        private static final int VGAP = 6;

        private final JComponent left;
        private final JComponent right;

        TopBarLayoutPanel(JComponent left, JComponent right) {
            super(null);
            this.left = left;
            this.right = right;
            setOpaque(true);
            add(left);
            add(right);
        }

        boolean isStackedForTesting() {
            return stackedAt(currentAvailableWidth());
        }

        @Override
        public void doLayout() {
            Insets ins = getInsets();
            int width = getWidth() - ins.left - ins.right;
            int height = getHeight() - ins.top - ins.bottom;
            Dimension lp = left.getPreferredSize();
            Dimension rp = right.getPreferredSize();

            if (!stackedAt(width)) {
                int rowH = Math.max(lp.height, rp.height);
                int top = ins.top + Math.max(0, (height - rowH) / 2);
                int lY = top + (rowH - lp.height) / 2;
                int rY = top + (rowH - rp.height) / 2;
                left.setBounds(ins.left, lY, Math.min(lp.width, width - HGAP - rp.width), lp.height);
                right.setBounds(ins.left + width - rp.width, rY, rp.width, rp.height);
            } else {
                // Title on top, controls below — keeps the most identifying signal anchored
                // to the natural reading position rather than tucking it under the buttons.
                int lw = Math.min(lp.width, width);
                left.setBounds(ins.left, ins.top, lw, lp.height);
                int rw = Math.min(rp.width, width);
                right.setBounds(ins.left + width - rw, ins.top + lp.height + VGAP, rw, rp.height);
            }
        }

        @Override
        public Dimension getPreferredSize() {
            Insets ins = getInsets();
            Dimension lp = left.getPreferredSize();
            Dimension rp = right.getPreferredSize();
            int avail = currentAvailableWidth();
            int height = stackedAt(avail)
                    ? rp.height + VGAP + lp.height
                    : Math.max(lp.height, rp.height);
            int width = Math.max(lp.width, rp.width);
            return new Dimension(width + ins.left + ins.right, height + ins.top + ins.bottom);
        }

        @Override
        public Dimension getMinimumSize() {
            // Equal to the stacked-layout footprint so the parent doesn't squeeze us below it.
            Insets ins = getInsets();
            Dimension lp = left.getPreferredSize();
            Dimension rp = right.getPreferredSize();
            int height = rp.height + VGAP + lp.height;
            int width = Math.max(lp.width, rp.width);
            return new Dimension(width + ins.left + ins.right, height + ins.top + ins.bottom);
        }

        private int currentAvailableWidth() {
            Insets ins = getInsets();
            int w = getWidth();
            if (w <= 0 && getParent() != null) {
                w = getParent().getWidth();
            }
            return w - ins.left - ins.right;
        }

        private boolean stackedAt(int availableWidth) {
            if (availableWidth <= 0) return false;
            Dimension lp = left.getPreferredSize();
            Dimension rp = right.getPreferredSize();
            return lp.width + HGAP + rp.width > availableWidth;
        }
    }

    // ---- test hooks (package-private) ----

    StructuredDecodedView structuredViewForTesting() {
        return structuredView;
    }

    Web3JsonEditor jsonEditorForTesting() {
        return jsonEditor;
    }

    SummaryBar summaryForTesting() {
        return summary;
    }

    String currentCardForTesting() {
        return currentCard;
    }

    JToggleButton structuredButtonForTesting() {
        return structuredBtn;
    }

    JToggleButton jsonButtonForTesting() {
        return jsonBtn;
    }

    JButton expandButtonForTesting() {
        return expandBtn;
    }

    JButton collapseButtonForTesting() {
        return collapseBtn;
    }

    void showCardForTesting(String name) {
        showCard(name);
    }
}
