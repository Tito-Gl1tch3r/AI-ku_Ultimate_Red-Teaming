package org.jdbg.gui.tabs.objectanalysis;

import org.jdbg.core.CoreInterface;
import org.jdbg.gui.MainFrame;
import org.jdbg.gui.tabs.ClassTree;
import org.jdbg.gui.tabs.ClassTreeNode;
import org.jdbg.logger.Logger;

import java.awt.event.MouseEvent;

public class ObjectAnalysisClassTree extends ClassTree {


    ClassTreeNode activeClass;
    public ObjectAnalysisClassTree(ClassTreeNode node) {
        super(node);
    }

    @Override
    protected void leftClick(ClassTreeNode klass) {
        Logger.log("Left: " + klass.getName());
        Logger.log("Getting: " + klass.getFullDir());
        activeClass = klass;

        // TODO adds objects to the ObjectList

        MainFrame.getInstance().getMainPane().getTabObjects().getMainHeapPanel().getObjectList().setTags(
                CoreInterface.getInstance().getObjectTags(klass.getFullDir()), klass.getFullDir(), klass.getName()
        );
    }


    public ClassTreeNode getActiveClass() {
        return activeClass;
    }

    @Override
    protected void rightClick(ClassTreeNode klass, MouseEvent e) {
        // No functionality planned for now
    }


}
