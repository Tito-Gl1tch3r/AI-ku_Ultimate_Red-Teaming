package com.nccgroup.web3decoder.ui.editor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.Icon;
import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JLabel;
import javax.swing.JMenuItem;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.SwingConstants;
import javax.swing.Timer;
import javax.swing.UIManager;
import javax.swing.border.EmptyBorder;

import java.awt.BasicStroke;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Cursor;
import java.awt.Desktop;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Insets;
import java.awt.RenderingHints;
import java.awt.Toolkit;
import java.awt.datatransfer.StringSelection;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.font.TextAttribute;
import java.net.URI;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.regex.Pattern;

/**
 * Read-only, JSON→tree projection of the decoded editor text. Renders the same Jackson
 * tree the JSON editor displays, but as a collapsible Swing component hierarchy:
 *
 * <ul>
 *   <li>{@code function} → bold function-color label in the parent disclosure header.</li>
 *   <li>{@code decodeSource}/{@code status} → chip badges (foreground + tinted background)
 *       reusing the {@link EditorTheme} {@code SOURCE_*}/{@code STATUS_*} kinds.</li>
 *   <li>{@code reason} → error-color text row.</li>
 *   <li>Address strings (0x + 40 hex) → mono row with copy popup.</li>
 *   <li>Long hex (e.g. {@code callData}/{@code rawCallData}/{@code result}/{@code returnData})
 *       → dim, wrapping text (no horizontal scroll) with a byte-count suffix.</li>
 *   <li>{@code calls}/{@code nestedCalls} arrays → each element rendered as a collapsible
 *       call node whose header carries its function + decodeSource + status chips.</li>
 * </ul>
 *
 * The component is purely a projection: editing happens in the JSON editor and this view
 * is rebuilt via {@link #setSource(String)} every time the text changes, so it cannot
 * desync. Never throws on unexpected shapes: malformed JSON or unhandled types fall back
 * to showing the raw text.
 */
public final class StructuredDecodedView extends JPanel {

    private static final Pattern ADDRESS_PATTERN = Pattern.compile("^0x[0-9a-fA-F]{40}$");
    private static final Pattern HEX_PATTERN = Pattern.compile("^0x[0-9a-fA-F]+$");
    /**
     * Threshold above which an unknown-key hex string renders in its own collapsable
     * row. Sized so bytes32 IDs (66 chars) stay inline as a single string; raw calldata
     * or long return blobs are larger and get the row treatment.
     */
    private static final int LONG_HEX_THRESHOLD = 100;

    private final ObjectMapper mapper = new ObjectMapper();
    private final JPanel content = new JPanel();
    private final JScrollPane scrollPane;
    private final List<DisclosureNode> rootNodes = new ArrayList<>();

    private EditorTheme theme = EditorTheme.resolve();
    private String lastSource;
    private Function<String, String> addressExplorerBuilder;
    /**
     * Tracks how many "args"/"output" subtrees we are currently rendering inside.
     * When &gt; 0, keys and values are drawn bold — matching the existing JSON
     * editor convention where function-argument data is the focal payload.
     */
    private int boldDepth = 0;

    public StructuredDecodedView() {
        super(new BorderLayout());
        content.setLayout(new BoxLayout(content, BoxLayout.Y_AXIS));
        content.setBorder(new EmptyBorder(10, 14, 24, 14));
        content.setOpaque(true);

        scrollPane = new JScrollPane(content);
        scrollPane.setBorder(BorderFactory.createEmptyBorder());
        scrollPane.getVerticalScrollBar().setUnitIncrement(16);

        add(scrollPane, BorderLayout.CENTER);
        applyThemeColors();
    }

    /** Replace the source text and rebuild the structured tree. */
    public void setSource(String text) {
        this.lastSource = text;
        rebuild();
    }

    /** Recursively expand every disclosure node currently rendered. */
    public void expandAll() {
        for (DisclosureNode n : rootNodes) {
            n.setExpandedRecursively(true);
        }
    }

    /** Recursively collapse every disclosure node currently rendered. */
    public void collapseAll() {
        for (DisclosureNode n : rootNodes) {
            n.setExpandedRecursively(false);
        }
    }

    /**
     * Set the function used to build the "explorer ↗" link URL for an address. When
     * {@code null}, address rows render without an explorer link (copy still works).
     * Triggers a rebuild so existing rows pick up the new builder.
     */
    public void setAddressExplorerBuilder(Function<String, String> builder) {
        this.addressExplorerBuilder = builder;
        rebuild();
    }

    @Override
    public void updateUI() {
        super.updateUI();
        // updateUI() fires from JPanel's constructor before our fields are assigned; guard.
        if (scrollPane != null) {
            theme = EditorTheme.resolve();
            applyThemeColors();
            rebuild();
        }
    }

    private void applyThemeColors() {
        setBackground(theme.background);
        content.setBackground(theme.background);
        scrollPane.getViewport().setBackground(theme.background);
    }

    private void rebuild() {
        content.removeAll();
        rootNodes.clear();
        boldDepth = 0;

        if (lastSource == null || lastSource.isEmpty()) {
            content.revalidate();
            content.repaint();
            return;
        }

        JsonNode root = tryParseJsonRoot(lastSource);
        if (root == null) {
            content.add(plainText(lastSource));
            content.add(Box.createVerticalGlue());
            content.revalidate();
            content.repaint();
            return;
        }

        try {
            if (root.isArray()) {
                int i = 0;
                for (JsonNode el : root) {
                    DisclosureNode node = buildNodeForArrayElement(i, el);
                    rootNodes.add(node);
                    content.add(node);
                    i++;
                }
            } else if (root.isObject()) {
                DisclosureNode node = buildObjectNode((com.fasterxml.jackson.databind.node.ObjectNode) root, null, null);
                rootNodes.add(node);
                content.add(node);
            } else {
                content.add(plainText(root.asText()));
            }
        } catch (RuntimeException e) {
            content.removeAll();
            rootNodes.clear();
            content.add(plainText(lastSource));
        }

        content.add(Box.createVerticalGlue());
        content.revalidate();
        content.repaint();
    }

    private JsonNode tryParseJsonRoot(String text) {
        String trimmed = text.trim();
        if (trimmed.isEmpty()) return null;
        char first = trimmed.charAt(0);
        if (first != '{' && first != '[') return null;
        try {
            return mapper.readTree(text);
        } catch (Exception e) {
            return null;
        }
    }

    // ---- node builders ----

    private DisclosureNode buildNodeForArrayElement(int index, JsonNode node) {
        if (node.isObject()) {
            return buildObjectNode((com.fasterxml.jackson.databind.node.ObjectNode) node, null, "[" + index + "]");
        }
        DisclosureNode dn = new DisclosureNode(theme);
        dn.addHeaderText("[" + index + "]", theme.color(StyleKind.PUNCTUATION), false);
        dn.addChild(buildScalarRow(null, node));
        return dn;
    }

    /**
     * Build a disclosure node for an object. The header carries: optional index prefix,
     * optional key, function-label, decodeSource chip, status chip; the body carries every
     * field except those already promoted to the header (function/decodeSource/status).
     */
    private DisclosureNode buildObjectNode(com.fasterxml.jackson.databind.node.ObjectNode obj,
                                          String key, String prefix) {
        DisclosureNode dn = new DisclosureNode(theme);

        if (prefix != null) {
            dn.addHeaderText(prefix, theme.color(StyleKind.PUNCTUATION), false);
        }
        if (key != null) {
            dn.addHeader(keyLabel(key));
        }

        JsonNode fn = obj.get("function");
        if (fn != null && fn.isTextual()) {
            dn.addHeaderText(fn.asText(), theme.color(StyleKind.FUNCTION), true);
        } else if (key == null && prefix == null) {
            // No identifying field at all — give the user something to grab onto.
            dn.addHeaderText("{ }", theme.color(StyleKind.PUNCTUATION), false);
        }

        JsonNode src = obj.get("decodeSource");
        if (src != null && src.isTextual()) {
            StyleKind sk = decodeSourceKind(src.asText());
            if (sk != null) {
                dn.addHeader(new Chip(src.asText(), sk, theme));
            }
        }

        JsonNode st = obj.get("status");
        if (st != null && st.isTextual()) {
            StyleKind sk = statusKind(st.asText());
            if (sk != null) {
                dn.addHeader(new Chip(st.asText(), sk, theme));
            }
        }

        // Presence of a "proxy" field means the call went through a proxy contract — surface
        // that as a chip in the header instead of showing the (often empty / unilluminating)
        // proxy details as a body field.
        if (obj.has("proxy")) {
            dn.addHeader(new Chip("proxied", StyleKind.STATUS_PROXIED, theme));
        }

        // We are entering the body of "args" or "output" — bold the keys/values rendered
        // beneath it, mirroring the JSON editor's args bold convention. The disclosure
        // header above already used the outer scope's normal weight.
        boolean enterBold = "args".equals(key) || "output".equals(key);
        if (enterBold) boldDepth++;

        // When the object exposes a decoded nestedCalls list, the raw args/calls payload
        // is redundant — collapse the args drawer by default so the focus stays on the
        // decoded inner calls. The user can still click to expand.
        boolean parentHasNestedCalls = obj.has("nestedCalls")
                && obj.get("nestedCalls").isArray()
                && obj.get("nestedCalls").size() > 0;

        try {
            Iterator<Map.Entry<String, JsonNode>> it = obj.fields();
            while (it.hasNext()) {
                Map.Entry<String, JsonNode> entry = it.next();
                String fk = entry.getKey();
                // Fields already shown in the header — don't repeat them in the body.
                if ("function".equals(fk) || "decodeSource".equals(fk)
                        || "status".equals(fk) || "proxy".equals(fk)) {
                    continue;
                }
                // Bookkeeping the user doesn't read for: nestedCalls tracking depth (it's
                // already visually obvious from the indentation) and Multicall3's
                // allowFailure flag (irrelevant to whoever's reading the decoded body).
                if ("depth".equals(fk) || "allowFailure".equals(fk)) {
                    continue;
                }
                Component child = buildField(fk, entry.getValue());
                if ("args".equals(fk) && parentHasNestedCalls && child instanceof DisclosureNode) {
                    ((DisclosureNode) child).setExpanded(false);
                }
                dn.addChild(child);
            }
        } finally {
            if (enterBold) boldDepth--;
        }
        dn.refreshAfterPopulate();
        return dn;
    }

    private Component buildField(String key, JsonNode value) {
        if (value == null || value.isNull()) {
            return scalarRow(key, "null", StyleKind.BOOL_NULL);
        }
        if (value.isObject()) {
            if (value.size() == 0) {
                return scalarRow(key, "{ }", StyleKind.PUNCTUATION);
            }
            return buildObjectNode((com.fasterxml.jackson.databind.node.ObjectNode) value, key, null);
        }
        if (value.isArray()) {
            if (value.size() == 0) {
                return scalarRow(key, "[ ]", StyleKind.PUNCTUATION);
            }
            return buildArrayField(key, value);
        }
        return buildScalarRow(key, value);
    }

    private Component buildArrayField(String key, JsonNode arr) {
        DisclosureNode dn = new DisclosureNode(theme);
        dn.addHeader(keyLabel(key));
        dn.addHeaderText("array (" + arr.size() + ")", theme.color(StyleKind.PUNCTUATION), false);

        boolean callsLike = "calls".equals(key) || "nestedCalls".equals(key);
        int i = 0;
        for (JsonNode el : arr) {
            if (callsLike || el.isObject() || el.isArray()) {
                dn.addChild(buildNodeForArrayElement(i, el));
            } else {
                dn.addChild(scalarRow("[" + i + "]", el.asText(), kindForScalar(el)));
            }
            i++;
        }
        dn.refreshAfterPopulate();
        return dn;
    }

    private Component buildScalarRow(String key, JsonNode value) {
        if (value.isTextual()) {
            String s = value.asText();
            if ("reason".equals(key)) {
                return errorTextRow(key, s);
            }
            if (isAddressLike(s)) {
                return addressRow(key, s);
            }
            if (isHexLike(s) && (s.length() > LONG_HEX_THRESHOLD || isHexValueKey(key))) {
                return hexRow(key, s);
            }
            return scalarRow(key, s, StyleKind.STRING);
        }
        if (value.isNumber()) {
            return scalarRow(key, value.asText(), StyleKind.NUMBER);
        }
        if (value.isBoolean()) {
            return scalarRow(key, value.asText(), StyleKind.BOOL_NULL);
        }
        return scalarRow(key, value.asText(), StyleKind.STRING);
    }

    // ---- row factories ----

    private Component scalarRow(String key, String value, StyleKind valueKind) {
        JPanel row = newRow();
        if (key != null) row.add(keyLabel(key));
        JLabel v = new JLabel(value);
        v.setForeground(theme.color(valueKind));
        v.setFont(monoFont());
        row.add(v);
        return row;
    }

    private Component errorTextRow(String key, String text) {
        JPanel row = new JPanel(new BorderLayout(6, 0)) {
            @Override
            public Dimension getMaximumSize() {
                Dimension pref = getPreferredSize();
                return new Dimension(Integer.MAX_VALUE, pref.height);
            }
        };
        row.setOpaque(false);
        row.setAlignmentX(LEFT_ALIGNMENT);
        if (key != null) {
            JPanel north = newRow();
            north.add(keyLabel(key));
            row.add(north, BorderLayout.NORTH);
        }
        JTextArea ta = wrappedTextArea(text);
        ta.setForeground(theme.color(StyleKind.ERROR));
        row.add(ta, BorderLayout.CENTER);
        return row;
    }

    private Component addressRow(String key, String addr) {
        JPanel row = newRow();
        if (key != null) row.add(keyLabel(key));
        JLabel v = new JLabel(addr);
        v.setForeground(theme.color(StyleKind.ADDRESS));
        v.setFont(monoFont());
        attachCopyMenu(v, addr);
        row.add(v);
        row.add(copyIconButton(addr));
        String url = addressExplorerBuilder != null ? addressExplorerBuilder.apply(addr) : null;
        if (url != null && !url.isEmpty()) {
            row.add(explorerLink(url));
        }
        return row;
    }

    /**
     * Collapsable hex row: header shows {@code key: 0xdeadbeef… N bytes [expand] [⧉]}
     * with the full hex hidden by default. Click "expand" to reveal the wrapping
     * full-content text area below; the link toggles back to "collapse". Matches the
     * mock's single-line preview behaviour so callData / rawCallData / large returnData
     * blobs no longer push the rest of the tree off-screen.
     */
    private Component hexRow(String key, String hex) {
        JPanel row = new JPanel() {
            @Override
            public Dimension getMaximumSize() {
                Dimension pref = getPreferredSize();
                return new Dimension(Integer.MAX_VALUE, pref.height);
            }
        };
        row.setLayout(new BoxLayout(row, BoxLayout.Y_AXIS));
        row.setOpaque(false);
        row.setAlignmentX(LEFT_ALIGNMENT);

        JPanel header = newRow();
        if (key != null) header.add(keyLabel(key));

        // Single-line preview shown when collapsed.
        JLabel preview = new JLabel(shortHexPreview(hex));
        preview.setName("hex-preview");
        preview.setForeground(theme.color(StyleKind.HEX));
        preview.setFont(monoFont());
        preview.setToolTipText(hex);
        attachCopyMenu(preview, hex);
        header.add(preview);

        int bytes = hex.startsWith("0x") ? (hex.length() - 2) / 2 : hex.length() / 2;
        JLabel bl = new JLabel(bytes + " bytes");
        bl.setFont(smallUiFont());
        bl.setForeground(theme.color(StyleKind.PUNCTUATION));
        header.add(bl);

        // Full wrapping content — hidden until the user expands.
        JTextArea hexArea = wrappedTextArea(hex);
        hexArea.setName("hex-full");
        hexArea.setForeground(theme.color(StyleKind.HEX));
        hexArea.setFont(monoFont());
        hexArea.setVisible(false);
        attachCopyMenu(hexArea, hex);

        JLabel toggle = new JLabel("expand");
        toggle.setName("hex-toggle");
        toggle.setToolTipText("Show full content");
        styleAsLink(toggle);
        toggle.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                if (e.getButton() != MouseEvent.BUTTON1) return;
                boolean nowExpanded = !hexArea.isVisible();
                hexArea.setVisible(nowExpanded);
                preview.setVisible(!nowExpanded);
                toggle.setText(nowExpanded ? "collapse" : "expand");
                toggle.setToolTipText(nowExpanded ? "Hide full content" : "Show full content");
                row.revalidate();
                row.repaint();
            }
        });
        header.add(toggle);
        header.add(copyIconButton(hex));

        row.add(header);
        row.add(hexArea);
        return row;
    }

    /** A short {@code 0xdeadbeef…} preview — first ~6 bytes of the hex, then ellipsis. */
    private static String shortHexPreview(String hex) {
        if (hex == null) return "";
        if (hex.length() <= 14) return hex;
        return hex.substring(0, 14) + "…";
    }

    /**
     * Icon-only "⧉" copy label. Click → write {@code value} to the clipboard and briefly
     * swap to "✓" feedback before reverting. Width is locked so the row doesn't reflow
     * during the swap.
     */
    private JLabel copyIconButton(String value) {
        final String idle = "⧉";
        final String done = "✓";
        JLabel l = new JLabel(idle);
        l.setName("copy-button");
        l.setToolTipText("Copy to clipboard");
        styleAsLink(l);
        java.awt.FontMetrics fm = l.getFontMetrics(l.getFont());
        int w = Math.max(fm.stringWidth(idle), fm.stringWidth(done)) + 14;
        Dimension size = new Dimension(w, l.getPreferredSize().height);
        l.setPreferredSize(size);
        l.setMinimumSize(size);
        l.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                if (e.getButton() != MouseEvent.BUTTON1) return;
                copyToClipboard(value);
                l.setText(done);
                Timer t = new Timer(1200, evt -> l.setText(idle));
                t.setRepeats(false);
                t.start();
            }
        });
        return l;
    }

    /**
     * "explorer ↗" link. The arrow is a custom-painted Icon so it renders identically
     * regardless of whether the L&F's UI font ships the U+2197 glyph. Click → open
     * {@code url} in the system browser.
     */
    private JLabel explorerLink(String url) {
        JLabel l = new JLabel("explorer");
        l.setName("explorer-link");
        l.setToolTipText(url);
        styleAsLink(l);
        int iconSize = Math.max(9, l.getFont().getSize() - 2);
        l.setIcon(makeNeArrowIcon(theme.color(StyleKind.SOURCE_ETHERSCAN), iconSize));
        l.setHorizontalTextPosition(SwingConstants.LEADING);
        l.setIconTextGap(3);
        l.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                if (e.getButton() == MouseEvent.BUTTON1) openInBrowser(url);
            }
        });
        return l;
    }

    /** A simple painted north-east arrow ↗ — antialiased, color-bound to the link's foreground. */
    private static Icon makeNeArrowIcon(Color color, int size) {
        return new Icon() {
            @Override
            public void paintIcon(Component c, Graphics g, int x, int y) {
                Graphics2D g2 = (Graphics2D) g.create();
                g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
                g2.setStroke(new BasicStroke(1.4f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                g2.setColor(color);
                int inset = 1;
                int x1 = x + inset, y1 = y + size - inset;
                int x2 = x + size - inset, y2 = y + inset;
                g2.drawLine(x1, y1, x2, y2);
                int head = Math.max(3, size * 2 / 5);
                g2.drawLine(x2, y2, x2 - head, y2);
                g2.drawLine(x2, y2, x2, y2 + head);
                g2.dispose();
            }

            @Override
            public int getIconWidth() { return size; }

            @Override
            public int getIconHeight() { return size; }
        };
    }

    /**
     * Make a JLabel look and behave like a hyperlink: link-color foreground, hand cursor,
     * underline-on-hover via a Font deriveFont attribute swap. Avoids HTML labels because
     * switching text between plain and HTML mid-life can leak raw markup.
     */
    private void styleAsLink(JLabel l) {
        Font base = UIManager.getFont("Label.font");
        final Font normal = base != null ? base : new Font(Font.SANS_SERIF, Font.PLAIN, 12);
        Map<TextAttribute, Object> attrs = new HashMap<>();
        for (Map.Entry<TextAttribute, ?> e : normal.getAttributes().entrySet()) {
            attrs.put(e.getKey(), e.getValue());
        }
        attrs.put(TextAttribute.UNDERLINE, TextAttribute.UNDERLINE_ON);
        final Font underlined = normal.deriveFont(attrs);
        l.setFont(normal);
        l.setForeground(theme.color(StyleKind.SOURCE_ETHERSCAN));
        l.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        l.setBorder(new EmptyBorder(0, 2, 0, 2));
        l.addMouseListener(new MouseAdapter() {
            @Override public void mouseEntered(MouseEvent e) { l.setFont(underlined); }
            @Override public void mouseExited(MouseEvent e) { l.setFont(normal); }
        });
    }

    private static void copyToClipboard(String value) {
        if (value == null) return;
        try {
            Toolkit.getDefaultToolkit().getSystemClipboard()
                    .setContents(new StringSelection(value), null);
        } catch (RuntimeException ignored) {
            // Clipboard may be unavailable in headless tests; ignore.
        }
    }

    private static void openInBrowser(String url) {
        if (url == null || url.isEmpty()) return;
        try {
            if (Desktop.isDesktopSupported() && Desktop.getDesktop().isSupported(Desktop.Action.BROWSE)) {
                Desktop.getDesktop().browse(URI.create(url));
            }
        } catch (Exception ignored) {
            // Browser launch can fail (no desktop, no handler); silently no-op.
        }
    }

    private JLabel keyLabel(String key) {
        JLabel l = new JLabel(key + ":");
        l.setForeground(theme.color(StyleKind.KEY));
        l.setFont(monoFont());
        return l;
    }

    /** Theme mono font, bold when we are rendering inside an args/output subtree. */
    private Font monoFont() {
        Font base = theme.font;
        return boldDepth > 0 ? base.deriveFont(Font.BOLD) : base;
    }

    private JPanel newRow() {
        // BoxLayout.Y_AXIS distributes vertical slack into any child whose maximum height
        // exceeds its preferred height. Clamp it dynamically so rows stay tight even when
        // sibling disclosures collapse/expand and free up space.
        JPanel p = new JPanel(new FlowLayout(FlowLayout.LEFT, 4, 1)) {
            @Override
            public Dimension getMaximumSize() {
                Dimension pref = getPreferredSize();
                return new Dimension(Integer.MAX_VALUE, pref.height);
            }
        };
        p.setOpaque(false);
        p.setAlignmentX(LEFT_ALIGNMENT);
        return p;
    }

    private JTextArea wrappedTextArea(String text) {
        JTextArea ta = new JTextArea(text);
        ta.setLineWrap(true);
        ta.setWrapStyleWord(false);
        ta.setEditable(false);
        ta.setOpaque(false);
        ta.setBorder(null);
        ta.setFont(theme.font);
        ta.setAlignmentX(LEFT_ALIGNMENT);
        ta.setMaximumSize(new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE));
        ta.setColumns(16);
        ta.setHighlighter(null);
        return ta;
    }

    private Component plainText(String text) {
        JTextArea ta = wrappedTextArea(text);
        ta.setForeground(theme.foreground);
        return ta;
    }

    private void attachCopyMenu(JComponent c, String value) {
        JPopupMenu menu = new JPopupMenu();
        JMenuItem copy = new JMenuItem("Copy");
        copy.addActionListener(e -> copyToClipboard(value));
        menu.add(copy);
        c.setComponentPopupMenu(menu);
        c.setCursor(Cursor.getPredefinedCursor(Cursor.TEXT_CURSOR));
    }

    private Font smallUiFont() {
        Font base = UIManager.getFont("Label.font");
        int size = base != null ? Math.max(10, base.getSize() - 2) : 10;
        return new Font(base != null ? base.getFamily() : "Dialog", Font.PLAIN, size);
    }

    // ---- classification helpers (kept local; the scanner's own copies stay private) ----

    private static StyleKind decodeSourceKind(String content) {
        switch (content) {
            case "cache":     return StyleKind.SOURCE_CACHE;
            case "etherscan": return StyleKind.SOURCE_ETHERSCAN;
            case "4byte":     return StyleKind.SOURCE_FOURBYTE;
            case "builtin":   return StyleKind.SOURCE_BUILTIN;
            default:          return null;
        }
    }

    private static StyleKind statusKind(String content) {
        switch (content) {
            case "decoded": return StyleKind.STATUS_OK;
            case "skipped": return StyleKind.STATUS_SKIPPED;
            case "error":   return StyleKind.ERROR;
            default:        return null;
        }
    }

    private static boolean isAddressLike(String s) {
        return s != null && ADDRESS_PATTERN.matcher(s).matches();
    }

    private static boolean isHexLike(String s) {
        return s != null && HEX_PATTERN.matcher(s).matches();
    }

    private static boolean isHexValueKey(String key) {
        return "callData".equals(key) || "rawCallData".equals(key)
                || "result".equals(key) || "returnData".equals(key)
                || "data".equals(key);
    }

    private static StyleKind kindForScalar(JsonNode el) {
        if (el.isNumber()) return StyleKind.NUMBER;
        if (el.isBoolean() || el.isNull()) return StyleKind.BOOL_NULL;
        return StyleKind.STRING;
    }

    // ---- inner classes ----

    /**
     * A collapsible row: a horizontal header (caret + label/chip components) plus a vertical
     * children container that's hidden when collapsed. Header click toggles the disclosure.
     */
    static final class DisclosureNode extends JPanel {

        private final JButton caret;
        private final JPanel header;
        private final JPanel children;
        private final EditorTheme theme;
        private boolean expanded = true;

        DisclosureNode(EditorTheme theme) {
            super(new BorderLayout());
            this.theme = theme;
            setOpaque(false);
            setAlignmentX(LEFT_ALIGNMENT);

            header = new JPanel(new FlowLayout(FlowLayout.LEFT, 4, 1));
            header.setOpaque(false);
            header.setAlignmentX(LEFT_ALIGNMENT);
            header.setMaximumSize(new Dimension(Integer.MAX_VALUE, Short.MAX_VALUE));

            caret = new JButton("▾");
            caret.setBorder(new EmptyBorder(0, 0, 0, 0));
            caret.setMargin(new Insets(0, 0, 0, 0));
            caret.setContentAreaFilled(false);
            caret.setFocusPainted(false);
            caret.setForeground(theme.color(StyleKind.PUNCTUATION));
            caret.setFont(theme.font);
            caret.setHorizontalAlignment(SwingConstants.CENTER);
            caret.setPreferredSize(new Dimension(14, 14));
            caret.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
            caret.addActionListener(e -> toggle());
            header.add(caret);

            // Whole-header click also toggles, so users don't have to hit the small caret.
            header.addMouseListener(new MouseAdapter() {
                @Override
                public void mouseClicked(MouseEvent e) {
                    if (e.getButton() == MouseEvent.BUTTON1 && e.getClickCount() == 1) {
                        toggle();
                    }
                }
            });

            children = new JPanel();
            children.setLayout(new BoxLayout(children, BoxLayout.Y_AXIS));
            children.setOpaque(false);
            children.setAlignmentX(LEFT_ALIGNMENT);

            JPanel childWrap = new JPanel(new BorderLayout());
            childWrap.setOpaque(false);
            childWrap.add(Box.createHorizontalStrut(18), BorderLayout.WEST);
            childWrap.add(children, BorderLayout.CENTER);

            add(header, BorderLayout.NORTH);
            add(childWrap, BorderLayout.CENTER);
        }

        boolean isExpanded() {
            return expanded;
        }

        void setExpanded(boolean v) {
            expanded = v;
            boolean hasBody = children.getComponentCount() > 0;
            caret.setVisible(hasBody);
            if (hasBody) {
                caret.setText(v ? "▾" : "▸");
                children.setVisible(v);
            }
            revalidate();
            repaint();
        }

        void toggle() {
            setExpanded(!expanded);
        }

        void setExpandedRecursively(boolean v) {
            setExpanded(v);
            for (Component c : children.getComponents()) {
                if (c instanceof DisclosureNode) {
                    ((DisclosureNode) c).setExpandedRecursively(v);
                }
            }
        }

        /**
         * Re-applies visibility state after the body has been populated. Hides the caret
         * and the children area when there's nothing to disclose so an empty drawer
         * doesn't leave a blank gap below the header.
         */
        void refreshAfterPopulate() {
            setExpanded(expanded);
        }

        @Override
        public Dimension getMaximumSize() {
            Dimension pref = getPreferredSize();
            return new Dimension(Integer.MAX_VALUE, pref.height);
        }

        void addHeader(Component c) {
            header.add(c);
        }

        void addHeaderText(String text, Color color, boolean bold) {
            JLabel l = new JLabel(text);
            l.setForeground(color);
            Font f = theme.font;
            l.setFont(bold ? f.deriveFont(Font.BOLD) : f);
            header.add(l);
        }

        void addChild(Component c) {
            if (c instanceof JComponent) {
                ((JComponent) c).setAlignmentX(LEFT_ALIGNMENT);
            }
            children.add(c);
        }

        JPanel headerForTesting() {
            return header;
        }

        JPanel childrenContainerForTesting() {
            return children;
        }
    }

    /** Foreground-colored, tinted-background pill — reuses the theme's SOURCE / STATUS palette. */
    static final class Chip extends JLabel {

        private final StyleKind kind;
        private final EditorTheme theme;

        Chip(String text, StyleKind kind, EditorTheme theme) {
            super(text.toUpperCase());
            this.kind = kind;
            this.theme = theme;
            setForeground(theme.color(kind));
            setOpaque(false);
            setBorder(new EmptyBorder(1, 6, 1, 6));

            Font base = UIManager.getFont("Label.font");
            int size = base != null ? Math.max(10, base.getSize() - 2) : 10;
            String family = base != null ? base.getFamily() : "Dialog";
            setFont(new Font(family, Font.BOLD, size));
        }

        StyleKind kind() {
            return kind;
        }

        @Override
        protected void paintComponent(Graphics g) {
            Color bg = theme.background(kind);
            if (bg != null) {
                Graphics2D g2 = (Graphics2D) g.create();
                g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
                g2.setColor(bg);
                g2.fillRoundRect(0, 0, getWidth(), getHeight(), 6, 6);
                Color fg = theme.color(kind);
                if (fg != null) {
                    g2.setColor(fg);
                    g2.drawRoundRect(0, 0, getWidth() - 1, getHeight() - 1, 6, 6);
                }
                g2.dispose();
            }
            super.paintComponent(g);
        }
    }
}
