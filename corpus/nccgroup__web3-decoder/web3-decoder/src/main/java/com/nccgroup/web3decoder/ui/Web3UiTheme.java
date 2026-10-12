package com.nccgroup.web3decoder.ui;

import javax.swing.BorderFactory;
import javax.swing.UIManager;
import javax.swing.border.Border;
import javax.swing.border.EmptyBorder;
import java.awt.Color;
import java.awt.Font;
import java.awt.Insets;

/**
 * Theme-aware color/border/spacing constants for the Web3 tab. Pulls from
 * UIManager so the same code reads correctly under both Burp dark and light
 * (FlatLaf). The single accent — Burp orange — is the only hard-coded color,
 * and even that defers to the LAF if a "Burp.accentColor" key is present.
 */
final class Web3UiTheme {

    static final int OUTER_PADDING = 8;
    static final int GAP = 8;

    private static final Color BURP_ORANGE_FALLBACK = new Color(0xff6633);

    private Web3UiTheme() {}

    /** Accent color (Burp orange). Defers to LAF when available. */
    static Color accent() {
        Color c = UIManager.getColor("Burp.accentColor");
        return c != null ? c : BURP_ORANGE_FALLBACK;
    }

    /** Foreground color used on the accent button. */
    static Color accentForeground() {
        Color c = UIManager.getColor("Burp.accentForeground");
        return c != null ? c : Color.WHITE;
    }

    /** Soft background used for attached panel header bars. */
    static Color panelHeaderBg() {
        Color c = firstNonNull(
                UIManager.getColor("TableHeader.background"),
                UIManager.getColor("Panel.background"));
        return c != null ? c : UIManager.getColor("control");
    }

    /** Dim/muted foreground for subtitles, descriptions, EXTERNAL tag. */
    static Color mutedFg() {
        Color c = firstNonNull(
                UIManager.getColor("Label.disabledForeground"),
                UIManager.getColor("textInactiveText"));
        if (c != null) return c;
        Color fg = UIManager.getColor("Label.foreground");
        return fg != null ? new Color(fg.getRed(), fg.getGreen(), fg.getBlue(), 160) : Color.GRAY;
    }

    /** Theme-appropriate divider color for vertical/horizontal separators. */
    static Color dividerColor() {
        Color c = firstNonNull(
                UIManager.getColor("Separator.foreground"),
                UIManager.getColor("Component.borderColor"));
        return c != null ? c : Color.GRAY;
    }

    /** 1px border for grouped panels. Theme-aware. */
    static Border panelBorder() {
        Color c = firstNonNull(
                UIManager.getColor("Component.borderColor"),
                UIManager.getColor("Separator.foreground"));
        return BorderFactory.createLineBorder(c != null ? c : Color.GRAY, 1);
    }

    /** Border that draws only a 1px line on the bottom — for header bars. */
    static Border headerBottomDivider() {
        Color c = firstNonNull(
                UIManager.getColor("Component.borderColor"),
                UIManager.getColor("Separator.foreground"));
        return BorderFactory.createMatteBorder(0, 0, 1, 0, c != null ? c : Color.GRAY);
    }

    /** Standard inner padding for panel bodies. */
    static EmptyBorder panelInsets() {
        return new EmptyBorder(0, 0, 0, 0);
    }

    static Insets headerInsets() {
        return new Insets(6, 10, 6, 10);
    }

    /** Bold UI font ~12px, used for the uppercase title in panel headers. */
    static Font panelTitleFont(Font base) {
        Font f = base != null ? base : UIManager.getFont("Label.font");
        if (f == null) f = new Font(Font.SANS_SERIF, Font.PLAIN, 12);
        return f.deriveFont(Font.BOLD, Math.max(11f, f.getSize2D() - 1f));
    }

    static Font monoFont(Font base, float size) {
        Font f = UIManager.getFont("TextArea.font");
        if (f == null) f = new Font(Font.MONOSPACED, Font.PLAIN, 12);
        return f.deriveFont(size);
    }

    private static Color firstNonNull(Color... cs) {
        for (Color c : cs) if (c != null) return c;
        return null;
    }
}
