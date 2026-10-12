package org.jdbg.gui;

import org.jdbg.gui.tabs.classanalysis.TabClasses;
import org.jdbg.gui.tabs.ClassTreeNode;
import org.jdbg.gui.tabs.objectanalysis.ObjectAnalysisClassTree;
import org.jdbg.gui.tabs.objectanalysis.TabObjects;

import javax.swing.*;
import javax.swing.tree.DefaultTreeModel;
import java.awt.*;

public class MainTabbedPane extends JTabbedPane {

    JPanel tabClasses = new JPanel();
    JPanel tabObjects = new JPanel();
    TabClasses classes;
    TabObjects objects;
    public MainTabbedPane() {
        tabClasses.setLayout(new GridLayout());
        tabObjects.setLayout(new GridLayout());
        addTab("Class Analysis", tabClasses);
        addTab("Heap Analysis", tabObjects);

    }
    public void init(ClassTreeNode node) {
        tabClasses.removeAll();
        classes = new TabClasses(node);
        tabClasses.add(classes);
        tabClasses.revalidate();

        tabObjects.removeAll();
        objects = new TabObjects(node);
        tabObjects.add(objects);
        tabObjects.revalidate();
    }

    public void addToObjectWorkspace(String className) {
        ObjectAnalysisClassTree tree = objects.getTree();
        ClassTreeNode.addToTree((ClassTreeNode)tree.getModel().getRoot(), className);
        ((DefaultTreeModel)tree.getModel()).reload();
        tree.revalidate();
    }


    public TabObjects getTabObjects() {
        return objects;
    }

    public TabClasses getTabClasses() {
        return classes;
    }

    public void initClass(String klassName, String dec, byte[] klass) {
        classes.init(klassName, dec, klass);
    }


}
