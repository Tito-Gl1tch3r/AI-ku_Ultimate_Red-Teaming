package org.jdbg.gui.buttonbar.process.buttons;

import org.jdbg.core.CoreInterface;
import org.jdbg.gui.MainFrame;
import org.jdbg.gui.buttonbar.process.ProcessList;
import org.jdbg.gui.buttonbar.process.ProcessSelectDialog;
import org.jdbg.gui.tabs.ClassTreeNode;
import org.jdbg.logger.Logger;

import javax.swing.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.List;

public class AttachButton extends JButton {
    ProcessList list;
    ProcessSelectDialog parent;
    public AttachButton(ProcessList list, ProcessSelectDialog parent) {
        super("Attach");
        this.list = list;
        this.parent = parent;
        addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                handleClick(e);
            }
        });
    }


    //TODO implement attach
    void handleClick(ActionEvent e) {

        Logger.log("Selected: " + list.getSelectedValue());
        if(CoreInterface.getInstance().attach((int)list.getSelectedValue().id)) {

            List<String> classNames = CoreInterface.getInstance().getLoadedClassNames();
            ClassTreeNode node = ClassTreeNode.constructTree(classNames);
            MainFrame.getInstance().getMainPane().init(node);

            parent.dispose();
        }
    }
}
