package org.jdbg.gui.tabs.classanalysis.codepanel;

import javax.swing.*;
import java.awt.*;

public class PaddedIcon implements Icon {
    private final Icon baseIcon;
    private final int padding;

    public PaddedIcon(Icon baseIcon, int padding) {
        this.baseIcon = baseIcon;
        this.padding = padding;
    }

    @Override
    public void paintIcon(Component c, Graphics g, int x, int y) {
        baseIcon.paintIcon(c, g, x + padding, y + padding);
    }

    @Override
    public int getIconWidth() {
        return baseIcon.getIconWidth() + (2 * padding);
    }

    @Override
    public int getIconHeight() {
        return baseIcon.getIconHeight() + (2 * padding);
    }
}