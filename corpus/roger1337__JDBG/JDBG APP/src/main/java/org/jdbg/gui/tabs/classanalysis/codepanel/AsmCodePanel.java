package org.jdbg.gui.tabs.classanalysis.codepanel;

import org.fife.ui.rtextarea.Gutter;
import org.jdbg.core.attach.AttachManager;
import org.jdbg.core.attach.breakpoint.BreakpointManager;

import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

public class AsmCodePanel extends CodePanel {

    String parentClass;
    int idx;
    public AsmCodePanel( String parentClass, int idx) {
        super();

        scrollPane.setIconRowHeaderEnabled(true);
        scrollPane.getGutter().setIconRowHeaderInheritsGutterBackground(true);
        scrollPane.getGutter().setBookmarkingEnabled(true);
        scrollPane.getGutter().setBookmarkIcon(createBreakpointIcon());


        if(scrollPane.getGutter().getIconRowListenerCount()==0) {
                scrollPane.getGutter().addIconRowListener(AttachManager.getInstance().getBreakpointManager());
        }

        this.parentClass = parentClass;
        this.idx =idx;

    }

    @Override
    public void setText(String s) {
        super.setText(s);

        Set<BreakpointManager.Breakpoint> breakpoints = AttachManager.getInstance().getBreakpointManager().getBreakpoints(parentClass);
        List<Integer> toToggle = new ArrayList<>();

        final int pass = idx;
        breakpoints.forEach((breakpoint) -> {
            if(breakpoint.methodIdx == pass)
                toToggle.add(breakpoint.line);
        });

        for(Integer i  : toToggle) {
            try {
                scrollPane.getGutter().toggleBookmark(i);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

    }

    public Gutter getGutter() {
        return scrollPane.getGutter();
    }

    /**
     * Creates a simple red circle icon to represent a breakpoint.
     */
    private Icon createBreakpointIcon() {
        int size = 12;
        BufferedImage image = new BufferedImage(size, size, BufferedImage.TYPE_INT_ARGB);
        Graphics2D g2 = image.createGraphics();
        // Enable antialiasing for a smoother circle.
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2.setColor(new Color(255, 0, 0, 128));
        g2.fillOval(0, 0, size, size);
        g2.dispose();
        return new PaddedIcon(new ImageIcon(image), 4);
    }
}
