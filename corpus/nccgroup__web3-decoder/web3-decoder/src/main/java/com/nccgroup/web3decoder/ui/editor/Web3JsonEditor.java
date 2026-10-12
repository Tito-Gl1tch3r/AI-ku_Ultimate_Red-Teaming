package com.nccgroup.web3decoder.ui.editor;

import burp.api.montoya.logging.Logging;

import javax.swing.AbstractAction;
import javax.swing.BorderFactory;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextPane;
import javax.swing.KeyStroke;
import javax.swing.Timer;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;
import javax.swing.text.AbstractDocument;
import javax.swing.text.BadLocationException;
import javax.swing.text.BoxView;
import javax.swing.text.ComponentView;
import javax.swing.text.DefaultHighlighter;
import javax.swing.text.Element;
import javax.swing.text.Highlighter;
import javax.swing.text.IconView;
import javax.swing.text.LabelView;
import javax.swing.text.ParagraphView;
import javax.swing.text.SimpleAttributeSet;
import javax.swing.text.StyleConstants;
import javax.swing.text.StyledDocument;
import javax.swing.text.StyledEditorKit;
import javax.swing.text.View;
import javax.swing.text.ViewFactory;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Graphics;
import java.awt.Toolkit;
import java.awt.event.ActionEvent;
import java.awt.event.KeyEvent;
import java.awt.geom.Rectangle2D;
import java.util.List;
import java.util.Optional;

/**
 * A reusable, theme-matched JSON editor: syntax + semantic highlighting, a line-number
 * gutter, current-line and bracket highlighting, live JSON-validity, and a search bar.
 * Drop-in replacement for Burp's RawEditor at the call sites that render Web3 JSON.
 */
public final class Web3JsonEditor {

    private static final int RESTYLE_DEBOUNCE_MS = 200;

    private final Logging logging;
    private final JsonStyleScanner scanner = new JsonStyleScanner();
    private final JsonValidator validator = new JsonValidator();
    private final BracketMatcher bracketMatcher = new BracketMatcher();

    private EditorTheme theme = EditorTheme.resolve();
    private Color currentLineColor = theme.currentLine;

    private final JTextPane textPane = new JTextPane() {
        @Override
        protected void paintComponent(Graphics g) {
            // Non-opaque so we control the background; paint bg + current-line tint
            // beneath the text the UI draws in super.paintComponent.
            g.setColor(getBackground());
            g.fillRect(0, 0, getWidth(), getHeight());
            if (currentLineColor != null && getCaretPosition() >= 0) {
                try {
                    Rectangle2D r = modelToView2D(getCaretPosition());
                    if (r != null) {
                        g.setColor(currentLineColor);
                        g.fillRect(0, (int) r.getY(), getWidth(), (int) r.getHeight());
                    }
                } catch (BadLocationException ignored) {
                }
            }
            super.paintComponent(g);
        }
    };

    private final JScrollPane scrollPane = new JScrollPane(textPane);
    private final LineNumberGutter gutter = new LineNumberGutter(textPane, theme);
    private final SearchBar searchBar = new SearchBar(textPane, theme);

    private final JPanel panel = new JPanel(new BorderLayout()) {
        @Override
        public void updateUI() {
            super.updateUI();
            // updateUI() fires from JPanel's own constructor, which runs *before* the
            // `panel` field is assigned. applyTheme() dereferences `panel` (and other
            // fields), so skip it until `panel` is set; the constructor body and field
            // initializers handle the initial theming. After construction, this runs on
            // genuine Look-and-Feel (light/dark) changes.
            if (panel != null) {
                applyTheme();
            }
        }
    };

    private final Timer restyleTimer;

    private boolean programmaticEdit = false;
    private boolean modified = false;

    private Object bracketTag1;
    private Object bracketTag2;
    private Object errorTag;

    public Web3JsonEditor(boolean editable, Logging logging) {
        this.logging = logging;

        textPane.setOpaque(false);
        // Install the wrapping kit before anything attaches to the document — setEditorKit
        // installs a fresh document, so the DocumentListener below must run after this.
        textPane.setEditorKit(new WrapEditorKit());
        textPane.setEditable(editable);
        applyThemeToPane();
        scrollPane.getViewport().setBackground(theme.background);
        scrollPane.setRowHeaderView(gutter);
        scrollPane.setBorder(BorderFactory.createEmptyBorder());

        panel.add(scrollPane, BorderLayout.CENTER);
        panel.add(searchBar, BorderLayout.SOUTH);

        restyleTimer = new Timer(RESTYLE_DEBOUNCE_MS, e -> restyle());
        restyleTimer.setRepeats(false);

        textPane.getDocument().addDocumentListener(new DocumentListener() {
            public void insertUpdate(DocumentEvent e) { onEdit(); }
            public void removeUpdate(DocumentEvent e) { onEdit(); }
            public void changedUpdate(DocumentEvent e) { /* attribute change: ignore */ }
        });

        textPane.addCaretListener(e -> {
            updateBracketHighlight();
            textPane.repaint();
        });

        int menuMask = Toolkit.getDefaultToolkit().getMenuShortcutKeyMaskEx();
        textPane.getInputMap().put(KeyStroke.getKeyStroke(KeyEvent.VK_F, menuMask), "web3-find");
        textPane.getActionMap().put("web3-find", new AbstractAction() {
            public void actionPerformed(ActionEvent e) {
                searchBar.open();
            }
        });
    }

    // ---- public API (mirrors what the call sites used from RawEditor) ----

    public Component getComponent() {
        return panel;
    }

    public void setText(String text) {
        programmaticEdit = true;
        try {
            textPane.setText(text != null ? text : "");
            textPane.setCaretPosition(0);
        } finally {
            programmaticEdit = false;
        }
        modified = false;
        restyle();
        gutter.revalidate();
        gutter.repaint();
        searchBar.refresh();
    }

    public String getText() {
        return textPane.getText();
    }

    public void setEditable(boolean editable) {
        textPane.setEditable(editable);
    }

    public boolean isModified() {
        return modified;
    }

    public String getSelectedText() {
        return textPane.getSelectedText();
    }

    public int selectionStart() {
        return textPane.getSelectionStart();
    }

    // ---- internals ----

    private void onEdit() {
        if (!programmaticEdit) {
            modified = true;
        }
        restyleTimer.restart();
        gutter.revalidate();
        gutter.repaint();
        searchBar.refresh();
    }

    private void restyle() {
        // Styling runs on the EDT; an unexpected failure here would otherwise vanish into
        // the EDT's default handler, so log it to Burp's extension error log.
        try {
            String text = textPane.getText();
            StyledDocument doc = textPane.getStyledDocument();

            SimpleAttributeSet def = new SimpleAttributeSet();
            StyleConstants.setForeground(def, theme.foreground);
            StyleConstants.setBold(def, false);
            doc.setCharacterAttributes(0, doc.getLength(), def, true);

            List<StyleSpan> spans = scanner.scan(text);
            int len = doc.getLength();
            for (StyleSpan s : spans) {
                if (s.start < 0 || s.start >= len) continue;
                int spanLen = Math.min(s.end, len) - s.start;
                if (spanLen <= 0) continue;
                doc.setCharacterAttributes(s.start, spanLen, attrFor(s), false);
            }
            updateErrorIndicator(text);
        } catch (RuntimeException e) {
            if (logging != null) {
                logging.logToError("Web3JsonEditor restyle failed: " + e);
            }
        }
    }

    private SimpleAttributeSet attrFor(StyleSpan span) {
        SimpleAttributeSet a = new SimpleAttributeSet();
        StyleConstants.setForeground(a, theme.color(span.kind));
        Color bg = theme.background(span.kind);
        boolean chip = bg != null;
        if (chip) {
            StyleConstants.setBackground(a, bg);
        }
        StyleConstants.setBold(a, span.bold || span.kind == StyleKind.FUNCTION || chip);
        return a;
    }

    private void updateBracketHighlight() {
        Highlighter h = textPane.getHighlighter();
        if (bracketTag1 != null) {
            h.removeHighlight(bracketTag1);
            bracketTag1 = null;
        }
        if (bracketTag2 != null) {
            h.removeHighlight(bracketTag2);
            bracketTag2 = null;
        }
        String text = textPane.getText();
        int caret = textPane.getCaretPosition();
        int self = bracketMatcher.selectedBracketIndex(text, caret);
        if (self < 0) return;
        int partner = bracketMatcher.match(text, caret);
        if (partner < 0) return;
        Highlighter.HighlightPainter p = new DefaultHighlighter.DefaultHighlightPainter(theme.bracket);
        try {
            bracketTag1 = h.addHighlight(self, self + 1, p);
            bracketTag2 = h.addHighlight(partner, partner + 1, p);
        } catch (BadLocationException ignored) {
        }
    }

    private void updateErrorIndicator(String text) {
        Highlighter h = textPane.getHighlighter();
        if (errorTag != null) {
            h.removeHighlight(errorTag);
            errorTag = null;
        }
        Optional<JsonValidator.ParseError> err = validator.validate(text);
        if (err.isEmpty()) {
            textPane.setToolTipText(null);
            return;
        }
        JsonValidator.ParseError pe = err.get();
        textPane.setToolTipText("JSON error: " + pe.message);
        int len = textPane.getDocument().getLength();
        if (pe.offset < 0 || len == 0) return;
        int start = Math.max(0, Math.min(pe.offset, len - 1));
        try {
            errorTag = h.addHighlight(start, Math.min(start + 1, len),
                    new UnderlinePainter(theme.color(StyleKind.ERROR)));
        } catch (BadLocationException ignored) {
        }
    }

    private void applyTheme() {
        theme = EditorTheme.resolve();
        currentLineColor = theme.currentLine;
        applyThemeToPane();
        scrollPane.getViewport().setBackground(theme.background);
        gutter.setTheme(theme);
        searchBar.setTheme(theme);
        restyle();
        panel.repaint();
    }

    private void applyThemeToPane() {
        textPane.setBackground(theme.background);
        textPane.setForeground(theme.foreground);
        textPane.setCaretColor(theme.caret);
        textPane.setSelectionColor(theme.selection);
        textPane.setFont(theme.font);
    }

    /**
     * StyledEditorKit whose LabelView reports zero minimum X-span, so the ParagraphView
     * is willing to break long unbreakable runs (e.g. hex calldata) mid-token instead of
     * extending the line. Only the layout changes — document content is identical.
     */
    private static final class WrapEditorKit extends StyledEditorKit {
        private final ViewFactory factory = new WrapColumnFactory();
        @Override public ViewFactory getViewFactory() { return factory; }
    }

    private static final class WrapColumnFactory implements ViewFactory {
        @Override public View create(Element elem) {
            String kind = elem.getName();
            if (kind != null) {
                switch (kind) {
                    case AbstractDocument.ContentElementName:
                        return new WrapLabelView(elem);
                    case AbstractDocument.ParagraphElementName:
                        return new ParagraphView(elem);
                    case AbstractDocument.SectionElementName:
                        return new BoxView(elem, View.Y_AXIS);
                    case StyleConstants.ComponentElementName:
                        return new ComponentView(elem);
                    case StyleConstants.IconElementName:
                        return new IconView(elem);
                    default:
                        break;
                }
            }
            return new LabelView(elem);
        }
    }

    private static final class WrapLabelView extends LabelView {
        WrapLabelView(Element elem) { super(elem); }
        @Override public float getMinimumSpan(int axis) {
            return axis == View.X_AXIS ? 0f : super.getMinimumSpan(axis);
        }
    }

    /** Draws a flat underline under a [p0, p1) range, for the live JSON-error marker. */
    private static final class UnderlinePainter implements Highlighter.HighlightPainter {
        private final Color color;

        UnderlinePainter(Color color) {
            this.color = color;
        }

        @Override
        public void paint(Graphics g, int p0, int p1, java.awt.Shape bounds, javax.swing.text.JTextComponent c) {
            try {
                Rectangle2D r = c.modelToView2D(p0);
                if (r == null) return;
                Rectangle2D r2 = c.modelToView2D(Math.max(p0 + 1, p1));
                int y = (int) (r.getY() + r.getHeight()) - 1;
                int x1 = (int) r.getX();
                int x2 = r2 != null ? (int) r2.getX() : x1 + 6;
                g.setColor(color);
                g.drawLine(x1, y, Math.max(x2, x1 + 6), y);
            } catch (BadLocationException ignored) {
            }
        }
    }
}
