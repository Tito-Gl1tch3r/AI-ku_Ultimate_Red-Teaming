package com.nccgroup.web3decoder.ui.editor;

import javax.swing.UIManager;
import java.awt.Color;
import java.awt.Font;
import java.util.EnumMap;
import java.util.Map;

/**
 * Resolves the editor palette and font from the current Look and Feel (FlatLaf in Burp).
 * A light/dark token palette is chosen by background luminance so the editor tracks Burp's
 * theme without per-token UIManager keys. Re-resolved on Look-and-Feel changes.
 */
final class EditorTheme {

    Color background;
    Color foreground;
    Color caret;
    Color selection;
    Color currentLine;
    Color bracket;
    Color searchMatch;
    Color currentMatch;
    Color gutterBackground;
    Color gutterForeground;
    Font font;

    private final Map<StyleKind, Color> tokenColors = new EnumMap<>(StyleKind.class);
    private final Map<StyleKind, Color> tokenBackgrounds = new EnumMap<>(StyleKind.class);

    private EditorTheme() {
    }

    Color color(StyleKind kind) {
        Color c = tokenColors.get(kind);
        return c != null ? c : foreground;
    }

    /** Optional chip-style background for the kind, or {@code null} when no backdrop applies. */
    Color background(StyleKind kind) {
        return tokenBackgrounds.get(kind);
    }

    static EditorTheme resolve() {
        EditorTheme t = new EditorTheme();

        Color bg = firstNonNull(
                UIManager.getColor("TextArea.background"),
                UIManager.getColor("EditorPane.background"),
                Color.WHITE);
        Color fg = firstNonNull(
                UIManager.getColor("TextArea.foreground"),
                UIManager.getColor("EditorPane.foreground"),
                Color.BLACK);
        boolean dark = luminance(bg) < 0.5;

        t.background = bg;
        t.foreground = fg;
        t.caret = fg;
        t.selection = firstNonNull(
                UIManager.getColor("TextArea.selectionBackground"),
                dark ? new Color(60, 90, 130) : new Color(180, 205, 240));
        t.font = resolveFont();

        if (dark) {
            t.currentLine = new Color(255, 255, 255, 18);
            t.bracket = new Color(120, 160, 220, 110);
            t.searchMatch = new Color(120, 110, 40);
            t.currentMatch = new Color(205, 160, 40);
            t.gutterBackground = scale(bg, 0.90);
            t.gutterForeground = new Color(125, 135, 145);
            t.tokenColors.put(StyleKind.KEY, new Color(120, 180, 230));
            t.tokenColors.put(StyleKind.STRING, new Color(140, 200, 140));
            t.tokenColors.put(StyleKind.NUMBER, new Color(220, 170, 110));
            t.tokenColors.put(StyleKind.BOOL_NULL, new Color(200, 130, 200));
            t.tokenColors.put(StyleKind.PUNCTUATION, new Color(150, 150, 150));
            t.tokenColors.put(StyleKind.FUNCTION, new Color(240, 200, 120));
            t.tokenColors.put(StyleKind.ERROR, new Color(235, 110, 100));
            t.tokenColors.put(StyleKind.ADDRESS, new Color(110, 205, 205));
            t.tokenColors.put(StyleKind.HEX, new Color(95, 130, 140));
            t.tokenColors.put(StyleKind.SOURCE_CACHE,     new Color(92, 192, 138));
            t.tokenColors.put(StyleKind.SOURCE_ETHERSCAN, new Color(79, 182, 199));
            t.tokenColors.put(StyleKind.SOURCE_FOURBYTE,  new Color(224, 163, 94));
            t.tokenColors.put(StyleKind.SOURCE_BUILTIN,   new Color(126, 156, 216));
            t.tokenColors.put(StyleKind.STATUS_OK,        new Color(92, 192, 138));
            t.tokenColors.put(StyleKind.STATUS_SKIPPED,   new Color(224, 163, 94));
            t.tokenColors.put(StyleKind.STATUS_PROXIED,   new Color(200, 157, 224));
            t.tokenBackgrounds.put(StyleKind.SOURCE_CACHE,     new Color(92, 192, 138, 33));
            t.tokenBackgrounds.put(StyleKind.SOURCE_ETHERSCAN, new Color(79, 182, 199, 33));
            t.tokenBackgrounds.put(StyleKind.SOURCE_FOURBYTE,  new Color(224, 163, 94, 36));
            t.tokenBackgrounds.put(StyleKind.SOURCE_BUILTIN,   new Color(126, 156, 216, 36));
            t.tokenBackgrounds.put(StyleKind.STATUS_OK,        new Color(92, 192, 138, 33));
            t.tokenBackgrounds.put(StyleKind.STATUS_SKIPPED,   new Color(224, 163, 94, 36));
            t.tokenBackgrounds.put(StyleKind.STATUS_PROXIED,   new Color(200, 157, 224, 36));
            t.tokenBackgrounds.put(StyleKind.ERROR,            new Color(235, 110, 100, 36));
        } else {
            t.currentLine = new Color(0, 0, 0, 12);
            t.bracket = new Color(80, 130, 200, 90);
            t.searchMatch = new Color(255, 235, 130);
            t.currentMatch = new Color(255, 190, 60);
            t.gutterBackground = scale(bg, 0.96);
            t.gutterForeground = new Color(140, 140, 140);
            t.tokenColors.put(StyleKind.KEY, new Color(40, 90, 160));
            t.tokenColors.put(StyleKind.STRING, new Color(40, 130, 60));
            t.tokenColors.put(StyleKind.NUMBER, new Color(160, 90, 20));
            t.tokenColors.put(StyleKind.BOOL_NULL, new Color(140, 50, 150));
            t.tokenColors.put(StyleKind.PUNCTUATION, new Color(110, 110, 110));
            t.tokenColors.put(StyleKind.FUNCTION, new Color(150, 90, 0));
            t.tokenColors.put(StyleKind.ERROR, new Color(190, 40, 40));
            t.tokenColors.put(StyleKind.ADDRESS, new Color(20, 130, 130));
            t.tokenColors.put(StyleKind.HEX, new Color(90, 130, 135));
            t.tokenColors.put(StyleKind.SOURCE_CACHE,     new Color(31, 157, 87));
            t.tokenColors.put(StyleKind.SOURCE_ETHERSCAN, new Color(29, 133, 151));
            t.tokenColors.put(StyleKind.SOURCE_FOURBYTE,  new Color(182, 106, 19));
            t.tokenColors.put(StyleKind.SOURCE_BUILTIN,   new Color(63, 95, 168));
            t.tokenColors.put(StyleKind.STATUS_OK,        new Color(31, 157, 87));
            t.tokenColors.put(StyleKind.STATUS_SKIPPED,   new Color(182, 106, 19));
            t.tokenColors.put(StyleKind.STATUS_PROXIED,   new Color(124, 77, 196));
            t.tokenBackgrounds.put(StyleKind.SOURCE_CACHE,     new Color(31, 157, 87, 25));
            t.tokenBackgrounds.put(StyleKind.SOURCE_ETHERSCAN, new Color(29, 133, 151, 25));
            t.tokenBackgrounds.put(StyleKind.SOURCE_FOURBYTE,  new Color(182, 106, 19, 30));
            t.tokenBackgrounds.put(StyleKind.SOURCE_BUILTIN,   new Color(63, 95, 168, 25));
            t.tokenBackgrounds.put(StyleKind.STATUS_OK,        new Color(31, 157, 87, 25));
            t.tokenBackgrounds.put(StyleKind.STATUS_SKIPPED,   new Color(182, 106, 19, 30));
            t.tokenBackgrounds.put(StyleKind.STATUS_PROXIED,   new Color(124, 77, 196, 25));
            t.tokenBackgrounds.put(StyleKind.ERROR,            new Color(190, 40, 40, 25));
        }
        t.tokenColors.put(StyleKind.PLAIN, fg);
        return t;
    }

    private static Font resolveFont() {
        Font base = UIManager.getFont("TextArea.font");
        int size = base != null ? base.getSize() : 13;
        return new Font(Font.MONOSPACED, Font.PLAIN, size);
    }

    private static double luminance(Color c) {
        return (0.299 * c.getRed() + 0.587 * c.getGreen() + 0.114 * c.getBlue()) / 255.0;
    }

    private static Color scale(Color c, double f) {
        return new Color(
                clamp((int) (c.getRed() * f)),
                clamp((int) (c.getGreen() * f)),
                clamp((int) (c.getBlue() * f)));
    }

    private static int clamp(int v) {
        return Math.max(0, Math.min(255, v));
    }

    private static Color firstNonNull(Color... colors) {
        for (Color c : colors) {
            if (c != null) return c;
        }
        return Color.GRAY;
    }
}
