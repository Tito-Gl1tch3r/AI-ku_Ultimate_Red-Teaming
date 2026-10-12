package org.jdbg.gui.tabs.classanalysis;

import org.jdbg.gui.tabs.classanalysis.asm.AsmTabbedPane;
import org.jdbg.gui.tabs.classanalysis.breakpoint.BreakpointBar;
import org.jdbg.gui.tabs.classanalysis.codepanel.AsmCodePanel;
import org.jdbg.gui.tabs.classanalysis.codepanel.CodePanel;
import org.jdbg.gui.tabs.ClassTreeNode;
import org.jdbg.gui.tabs.classanalysis.tabbed.factory.AsmTabbedFactory;
import org.jdbg.gui.tabs.classanalysis.tabbed.factory.BytecodeViewFactory;
import org.jdbg.gui.tabs.classanalysis.tree.ClassAnalysisPanel;
import org.jdbg.gui.tabs.classanalysis.tree.ClassAnalysisTree;

import javax.swing.*;

public class TabClasses extends JSplitPane {

    JScrollPane hierarchy;
    BytecodeViewTabbedPane panel;

    BreakpointBar bar;
    public TabClasses(ClassTreeNode node) {
        super(JSplitPane.HORIZONTAL_SPLIT);
        setResizeWeight(0.15);


        ClassAnalysisTree tree = new ClassAnalysisTree(node);
        ClassAnalysisPanel analysisPanel = new ClassAnalysisPanel(tree);


        this.panel = (BytecodeViewTabbedPane)new BytecodeViewFactory(new CodePanel(), (AsmTabbedPane) new AsmTabbedFactory().makePane()).makePane();
        this.bar = new BreakpointBar();
        JPanel container = new JPanel();
        container.setLayout(new BoxLayout(container, BoxLayout.Y_AXIS));
        container.add(bar);
        container.add(panel);

        setFocusable(false);
        panel.setBackground(new JFrame().getBackground());
        add(analysisPanel);
        add(container);
    }

    public void init(String klassName, String dec, byte[] klass) {
        panel.getDec().setText(dec);
        panel.getAsm().init(klassName, klass);
    }


    public BreakpointBar getBreakpointBar() {
        return bar;
    }
}
