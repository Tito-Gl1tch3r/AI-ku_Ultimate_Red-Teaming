package org.jdbg.gui.tabs.classanalysis.tree;

import org.jdbg.core.CoreInterface;
import org.jdbg.core.bytecode.decompiler.vineflower.VineflowerDecompiler;
import org.jdbg.gui.MainFrame;
import org.jdbg.gui.tabs.ClassTree;
import org.jdbg.gui.tabs.ClassTreeNode;
import org.jdbg.logger.Logger;

import javax.swing.*;
import javax.swing.tree.TreeNode;
import java.awt.event.ActionEvent;
import java.awt.event.MouseEvent;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

public class ClassAnalysisTree extends ClassTree {


    List<ClassTreeNode> leaves = new ArrayList<>();


    void explore(ClassTreeNode node) {
        if(node.isLeaf()) {
            leaves.add(node);
            return;
        }

        Iterator<? extends TreeNode> it = node.allChildren().asIterator();
        while(it.hasNext()) {
            explore((ClassTreeNode) it.next());
        }
    }
    public ClassAnalysisTree(ClassTreeNode node) {
        super(node);
        explore(node);
    }

    @Override
    protected void leftClick(ClassTreeNode klass) {
        byte[] bytes = CoreInterface.getInstance().getClassData(klass.getFullDir());
        Logger.log("Getting: " + klass.getFullDir());

        VineflowerDecompiler decompiler = new VineflowerDecompiler(bytes, klass.getFullDir());
        String s = decompiler.decompile();
        MainFrame.getInstance().getMainPane().initClass(klass.getFullDir(), s, bytes);
    }

    @Override
    protected void rightClick(ClassTreeNode klass, MouseEvent e) {
        JPopupMenu menu = new JPopupMenu();
        JMenuItem item = new JMenuItem(new AbstractAction("Add \"" + klass.getName() + "\" to Object Analysis") {
            @Override
            public void actionPerformed(ActionEvent e) {
                MainFrame.getInstance().getMainPane().addToObjectWorkspace(klass.getFullDir());
            }
        });

        menu.add(item);


        menu.show(this, e.getX(), e.getY());
    }


    public List<ClassTreeNode> getLeaves() {
        return leaves;
    }
}
