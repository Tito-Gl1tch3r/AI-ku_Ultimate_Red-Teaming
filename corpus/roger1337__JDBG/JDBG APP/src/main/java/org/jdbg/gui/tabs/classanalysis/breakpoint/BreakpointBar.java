package org.jdbg.gui.tabs.classanalysis.breakpoint;

import org.jdbg.MiscUtil;
import org.jdbg.core.attach.AttachManager;
import org.jdbg.core.pipeline.impl.PipelineBreakpoint;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class BreakpointBar extends JPanel {

    boolean hit = false;

    JButton playButton;

    JTextPane breakpointsText;

    JButton viewBreakpointInfoButton;

    JButton manageBreakpoints;

    BreakpointInfoDialog dialog;

    ManageBreakpointDialog manageDialog;


    public BreakpointBar() {
        int HEIGHT = 33;
        setBackground(UIManager.getColor("TextArea.background"));
        setBorder(BorderFactory.createMatteBorder(0, 1, 1, 1, UIManager.getColor("Button.borderColor")));
        setPreferredSize(new Dimension(10000, HEIGHT));
        setMaximumSize(new Dimension(10000, HEIGHT));
        setMinimumSize(new Dimension(0, HEIGHT));

        setLayout(new FlowLayout(FlowLayout.LEFT));

        breakpointsText = new JTextPane();
        playButton = new JButton();
        setNotHit();

        manageDialog = new ManageBreakpointDialog();

        add(breakpointsText);
        add(playButton);

        manageBreakpoints = new JButton("Manage Breakpoints");

        manageBreakpoints.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                manageDialog.update(AttachManager.getInstance().getBreakpointManager().getBreakpoints());
                manageDialog.setVisible(true);
            }
        });
        add(manageBreakpoints);

        playButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                PipelineBreakpoint.getInstance().continueExecution();
                setNotHit();
            }
        });
    }

    void setNotHit() {
        Icon icon = MiscUtil.getIcon("assets/icons/arrow-big-right-lines-deactivated.png", 16, 16);
        breakpointsText.setText("Breakpoints");
        playButton.setIcon(icon);
        if(viewBreakpointInfoButton != null) {
            viewBreakpointInfoButton.setVisible(false);
        }
    }

    public void breakpointHit(PipelineBreakpoint.BreakpointResponse response) {
        hit = true;

        dialog = new BreakpointInfoDialog(response);
        Icon icon = MiscUtil.getIcon("assets/icons/arrow-big-right-lines.png", 16, 16);
        playButton.setIcon(icon);
        breakpointsText.setText("Breakpoint Hit! : " + response.klassSignature + "#" + response.methodName);


        viewBreakpointInfoButton = new JButton("View");
        viewBreakpointInfoButton.setVisible(true);

        viewBreakpointInfoButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                dialog.setVisible(true);
            }
        });

        add(viewBreakpointInfoButton);
    }

}
