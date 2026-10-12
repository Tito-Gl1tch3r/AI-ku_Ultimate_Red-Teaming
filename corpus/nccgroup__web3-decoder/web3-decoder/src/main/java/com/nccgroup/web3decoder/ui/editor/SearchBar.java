package com.nccgroup.web3decoder.ui.editor;

import javax.swing.AbstractAction;
import javax.swing.BorderFactory;
import javax.swing.Icon;
import javax.swing.JButton;
import javax.swing.JCheckBoxMenuItem;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JTextField;
import javax.swing.JTextPane;
import javax.swing.KeyStroke;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;
import javax.swing.text.BadLocationException;
import javax.swing.text.DefaultHighlighter;
import javax.swing.text.Highlighter;

import java.awt.BasicStroke;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Insets;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.event.ActionEvent;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;
import java.awt.geom.Rectangle2D;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * Find bar styled to match Burp's native editor search: a settings (gear) popup with
 * Case sensitive / Regex / Auto-scroll toggles, back/forward arrows, a "Search"
 * placeholder field with a magnifier, and an "N highlights" label. Matches are painted
 * on the pane's Highlighter. Uses FlatLaf client properties (Burp's Look-and-Feel);
 * these degrade harmlessly under any other L&F.
 */
final class SearchBar extends JPanel {

    private final JTextPane textPane;
    private final JsonSearchEngine engine = new JsonSearchEngine();
    private EditorTheme theme;

    private final JTextField queryField = new JTextField();
    private final JLabel highlightsLabel = new JLabel("0 highlights");
    private final JButton settingsButton = new JButton("⚙");   // gear
    private final JButton prevButton = new JButton("←");       // back arrow
    private final JButton nextButton = new JButton("→");       // forward arrow
    private final JPopupMenu settingsMenu = new JPopupMenu();
    private final JCheckBoxMenuItem caseItem = new JCheckBoxMenuItem("Case sensitive");
    private final JCheckBoxMenuItem regexItem = new JCheckBoxMenuItem("Regex");
    private final JCheckBoxMenuItem autoScrollItem =
            new JCheckBoxMenuItem("Auto-scroll to match when text changes");

    private List<Range> matches = new ArrayList<>();
    private final List<Object> tags = new ArrayList<>();
    private int current = -1;

    SearchBar(JTextPane textPane, EditorTheme theme) {
        super(new BorderLayout(6, 0));
        this.textPane = textPane;
        this.theme = theme;
        // Always visible, like Burp's native editor search; Ctrl/Cmd-F just focuses it.
        build();
    }

    private void build() {
        setBorder(BorderFactory.createEmptyBorder(3, 4, 3, 4));

        styleToolBarButton(settingsButton, "Search settings");
        styleToolBarButton(prevButton, "Previous match (Shift+Enter)");
        styleToolBarButton(nextButton, "Next match (Enter)");
        // The default button font renders these glyphs tiny; scale them up (arrows bold
        // since the thin arrow glyphs read faint at small sizes).
        settingsButton.setFont(settingsButton.getFont().deriveFont(18f));
        prevButton.setFont(prevButton.getFont().deriveFont(Font.BOLD, 18f));
        nextButton.setFont(nextButton.getFont().deriveFont(Font.BOLD, 18f));

        settingsMenu.add(caseItem);
        settingsMenu.add(regexItem);
        settingsMenu.add(autoScrollItem);

        JPanel left = new JPanel(new FlowLayout(FlowLayout.LEFT, 2, 0));
        left.setOpaque(false);
        left.add(settingsButton);
        left.add(prevButton);
        left.add(nextButton);

        queryField.putClientProperty("JTextField.placeholderText", "Search");
        applyFieldStyle();

        add(left, BorderLayout.WEST);
        add(queryField, BorderLayout.CENTER);
        add(highlightsLabel, BorderLayout.EAST);

        settingsButton.addActionListener(e ->
                settingsMenu.show(settingsButton, 0, -settingsMenu.getPreferredSize().height));
        caseItem.addActionListener(e -> recompute(true));
        regexItem.addActionListener(e -> recompute(true));
        prevButton.addActionListener(e -> navigate(-1));
        nextButton.addActionListener(e -> navigate(1));

        queryField.getDocument().addDocumentListener(new DocumentListener() {
            public void insertUpdate(DocumentEvent e) { recompute(true); }
            public void removeUpdate(DocumentEvent e) { recompute(true); }
            public void changedUpdate(DocumentEvent e) { recompute(true); }
        });

        queryField.addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                if (e.getKeyCode() == KeyEvent.VK_ENTER) {
                    navigate(e.isShiftDown() ? -1 : 1);
                    e.consume();
                } else if (e.getKeyCode() == KeyEvent.VK_ESCAPE) {
                    clearAndReturnFocus();
                    e.consume();
                }
            }
        });

        // Esc clears the query (dropping highlights) and returns focus to the editor.
        getInputMap(WHEN_ANCESTOR_OF_FOCUSED_COMPONENT)
                .put(KeyStroke.getKeyStroke(KeyEvent.VK_ESCAPE, 0), "web3-clear-search");
        getActionMap().put("web3-clear-search", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                clearAndReturnFocus();
            }
        });

        updateCount();
    }

    private void styleToolBarButton(JButton b, String tooltip) {
        b.setToolTipText(tooltip);
        b.putClientProperty("JButton.buttonType", "toolBarButton"); // FlatLaf: flat/borderless
        b.setFocusable(false);
        b.setMargin(new Insets(2, 8, 2, 8));
    }

    /** Apply theme-dependent field styling (placeholder magnifier + muted count colour). */
    private void applyFieldStyle() {
        queryField.putClientProperty("JTextField.trailingIcon",
                new MagnifierIcon(theme.gutterForeground, 16));
        highlightsLabel.setForeground(theme.gutterForeground);
    }

    /** Move focus into the query field (e.g. on Ctrl/Cmd-F) and re-highlight the query. */
    void open() {
        queryField.requestFocusInWindow();
        queryField.selectAll();
        recompute(true);
    }

    /** Esc: clear the query (drops highlights) and hand focus back to the editor. */
    private void clearAndReturnFocus() {
        queryField.setText(""); // triggers recompute() via the document listener
        textPane.requestFocusInWindow();
    }

    /** Re-run the current query (e.g. after the document text changed). */
    void refresh() {
        recompute(autoScrollItem.isSelected());
    }

    void setTheme(EditorTheme theme) {
        this.theme = theme;
        applyFieldStyle();
        repaintHighlights();
    }

    private void recompute(boolean scroll) {
        clearTags();
        String q = queryField.getText();
        matches = engine.find(textPane.getText(), q, caseItem.isSelected(), regexItem.isSelected());

        boolean validRegex = true;
        if (regexItem.isSelected() && !q.isEmpty()) {
            try {
                Pattern.compile(q);
            } catch (PatternSyntaxException ex) {
                validRegex = false;
            }
        }
        // FlatLaf red outline for an invalid regex; cleared otherwise.
        queryField.putClientProperty("JComponent.outline", validRegex ? null : "error");

        current = matches.isEmpty() ? -1 : 0;
        repaintHighlights();
        if (scroll) scrollToCurrent();
        updateCount();
    }

    private void navigate(int delta) {
        if (matches.isEmpty()) return;
        current = (current + delta + matches.size()) % matches.size();
        repaintHighlights();
        scrollToCurrent();
        updateCount();
    }

    private void clearTags() {
        Highlighter h = textPane.getHighlighter();
        for (Object t : tags) h.removeHighlight(t);
        tags.clear();
    }

    private void repaintHighlights() {
        clearTags();
        Highlighter h = textPane.getHighlighter();
        Highlighter.HighlightPainter normal = new DefaultHighlighter.DefaultHighlightPainter(theme.searchMatch);
        Highlighter.HighlightPainter strong = new DefaultHighlighter.DefaultHighlightPainter(theme.currentMatch);
        int len = textPane.getDocument().getLength();
        for (int i = 0; i < matches.size(); i++) {
            Range r = matches.get(i);
            if (r.start < 0 || r.end > len) continue;
            try {
                tags.add(h.addHighlight(r.start, r.end, i == current ? strong : normal));
            } catch (BadLocationException ignored) {
            }
        }
    }

    private void scrollToCurrent() {
        if (current < 0 || current >= matches.size()) return;
        try {
            Rectangle2D r = textPane.modelToView2D(matches.get(current).start);
            if (r != null) {
                Rectangle bounds = new Rectangle((int) r.getX(), (int) r.getY(),
                        (int) r.getWidth(), (int) r.getHeight());
                textPane.scrollRectToVisible(bounds);
            }
        } catch (BadLocationException ignored) {
        }
    }

    private void updateCount() {
        int n = matches.size();
        highlightsLabel.setText(n == 1 ? "1 highlight" : n + " highlights");
    }

    /** A small magnifying-glass glyph drawn to sit inside the search field's trailing edge. */
    private static final class MagnifierIcon implements Icon {
        private final Color color;
        private final int size;

        MagnifierIcon(Color color, int size) {
            this.color = color != null ? color : Color.GRAY;
            this.size = size;
        }

        @Override
        public int getIconWidth() {
            return size;
        }

        @Override
        public int getIconHeight() {
            return size;
        }

        @Override
        public void paintIcon(Component c, Graphics g, int x, int y) {
            Graphics2D g2 = (Graphics2D) g.create();
            try {
                g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
                g2.setColor(color);
                g2.setStroke(new BasicStroke(1.4f));
                int d = size - 5; // lens diameter
                g2.drawOval(x, y, d, d);
                g2.drawLine(x + d - 1, y + d - 1, x + size - 1, y + size - 1); // handle
            } finally {
                g2.dispose();
            }
        }
    }
}
