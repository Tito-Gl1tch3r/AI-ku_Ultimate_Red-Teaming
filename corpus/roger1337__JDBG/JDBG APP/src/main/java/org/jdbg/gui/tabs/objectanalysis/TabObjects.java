package org.jdbg.gui.tabs.objectanalysis;

import org.jdbg.gui.tabs.ClassTreeNode;

import javax.swing.*;
import java.awt.*;
import java.util.List;

public class TabObjects extends JSplitPane {

    JScrollPane hierarchy;
    ObjectAnalysisClassTree tree;
    SavedWorkspace workspace;

    MainHeapPanel mainHeapPanel;

    public TabObjects(ClassTreeNode node) {
        super(HORIZONTAL_SPLIT);
        setResizeWeight(0.15);

        workspace = new SavedWorkspace();

        hierarchy = new JScrollPane();
        tree = new ObjectAnalysisClassTree( new ClassTreeNode(null, false, "Heap Workspace"));
        hierarchy = new JScrollPane(tree, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS,  JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);

        JPanel panel = new JPanel();
        panel.setLayout(new GridLayout(2, 1));
        panel.add(hierarchy);
        panel.add(workspace);
        add(panel);

        this.mainHeapPanel = new MainHeapPanel(tree);
        add(mainHeapPanel);
    }


    public MainHeapPanel getMainHeapPanel() {
        return mainHeapPanel;
    }

    public SavedWorkspace getWorkspace() {
        return workspace;
    }

    public ObjectAnalysisClassTree getTree() {
        return tree;
    }
}
