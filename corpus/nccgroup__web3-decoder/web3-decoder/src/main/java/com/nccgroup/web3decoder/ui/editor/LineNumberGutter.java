package com.nccgroup.web3decoder.ui.editor;

import javax.swing.JComponent;
import javax.swing.JTextPane;
import javax.swing.text.BadLocationException;
import javax.swing.text.Element;

import java.awt.Dimension;
import java.awt.FontMetrics;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Point;
import java.awt.Rectangle;
import java.awt.geom.Rectangle2D;

/** Row-header component that paints right-aligned line numbers for a JTextPane. */
final class LineNumberGutter extends JComponent {

    private static final int PAD = 8;

    private final JTextPane textPane;
    private EditorTheme theme;

    LineNumberGutter(JTextPane textPane, EditorTheme theme) {
        this.textPane = textPane;
        this.theme = theme;
        setFont(theme.font);
    }

    void setTheme(EditorTheme theme) {
        this.theme = theme;
        setFont(theme.font);
        revalidate();
        repaint();
    }

    @Override
    public Dimension getPreferredSize() {
        int lines = textPane.getDocument().getDefaultRootElement().getElementCount();
        FontMetrics fm = getFontMetrics(theme.font);
        int digits = Math.max(2, String.valueOf(Math.max(1, lines)).length());
        int width = fm.charWidth('0') * digits + PAD * 2;
        int height = Math.max(textPane.getHeight(), 1);
        return new Dimension(width, height);
    }

    @Override
    protected void paintComponent(Graphics g) {
        Graphics2D g2 = (Graphics2D) g.create();
        try {
            Rectangle clip = g2.getClipBounds();
            g2.setColor(theme.gutterBackground);
            g2.fillRect(clip.x, clip.y, clip.width, clip.height);
            g2.setColor(theme.gutterForeground);
            g2.setFont(theme.font);

            Element root = textPane.getDocument().getDefaultRootElement();
            FontMetrics fm = getFontMetrics(theme.font);
            int ascent = fm.getAscent();

            int startOffset = textPane.viewToModel2D(new Point(0, clip.y));
            int endOffset = textPane.viewToModel2D(new Point(0, clip.y + clip.height));
            int startLine = root.getElementIndex(Math.max(0, startOffset));
            int endLine = root.getElementIndex(Math.max(0, endOffset));

            for (int line = startLine; line <= endLine && line >= 0; line++) {
                Element el = root.getElement(line);
                if (el == null) break;
                Rectangle2D r = textPane.modelToView2D(el.getStartOffset());
                if (r == null) continue;
                String num = String.valueOf(line + 1);
                int textWidth = fm.stringWidth(num);
                int x = getWidth() - PAD - textWidth;
                int y = (int) r.getY() + ascent;
                g2.drawString(num, x, y);
            }
        } catch (BadLocationException ignored) {
            // best effort
        } finally {
            g2.dispose();
        }
    }
}
