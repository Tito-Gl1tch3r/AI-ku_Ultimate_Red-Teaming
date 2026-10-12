package org.jdbg.gui.tabs;

import javax.swing.*;
import javax.swing.plaf.basic.BasicTreeUI;
import javax.swing.tree.DefaultTreeModel;
import javax.swing.tree.TreeModel;
import javax.swing.tree.TreePath;
import java.awt.*;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.ArrayList;
import java.util.List;

public abstract class ClassTree extends JTree {


    ClassTreeNode prev = null;
    public ClassTree(ClassTreeNode node) {
        super(node);



        setUI(new BasicTreeUI());
        setFont(new Font(getFont().getName(), getFont().getStyle(), getFont().getSize()+2));
        addMouseListener(new MouseAdapter() {
            @Override
            public void mouseReleased(MouseEvent e) {
                ClassTreeNode node = (ClassTreeNode)getLastSelectedPathComponent();

                if(node!=null && node.isClass() && node != prev && SwingUtilities.isLeftMouseButton(e)) {
                    leftClick(node);
                    prev = node;
                }

                if(SwingUtilities.isRightMouseButton(e)) {
                    int r = getRowForLocation(e.getX(), e.getY());
                    ClassTreeNode rightClicked = (ClassTreeNode)getPathForRow(r).getLastPathComponent();
                    rightClick(rightClicked, e);


                }
            }
        });
    }

    void getExpandedTreePaths(JTree tree, TreePath current, List<TreePath> list) {
        TreeModel model = tree.getModel();
        Object node =  current.getLastPathComponent();
        int childCount = model.getChildCount(node);

        if(tree.isExpanded(current)) {
            list.add(current);
        }

        for (int i = 0; i < childCount; i++) {
            Object child = model.getChild(node, i);
            getExpandedTreePaths(tree, current.pathByAddingChild(child), list);
        }
    }


    public void reload() {
        List<TreePath> paths = new ArrayList<>();
        getExpandedTreePaths(this, new TreePath(getModel().getRoot()), paths);
        ((DefaultTreeModel)getModel()).reload();

        for(TreePath path: paths) {
            expandPath(path);
        }

    }

    protected abstract void rightClick(ClassTreeNode klass, MouseEvent e);

    protected abstract void leftClick(ClassTreeNode klass);


}
