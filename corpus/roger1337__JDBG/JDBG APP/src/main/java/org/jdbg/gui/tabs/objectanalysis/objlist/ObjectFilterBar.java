package org.jdbg.gui.tabs.objectanalysis.objlist;

import org.jdbg.core.CoreInterface;
import org.jdbg.gui.tabs.objectanalysis.ObjectAnalysisClassTree;
import org.jdbg.gui.util.PlaceholderTextField;
import org.jdbg.logger.Logger;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class ObjectFilterBar extends JPanel {

    JButton filterButton = new JButton("Filter");
    PlaceholderTextField filterField;

    ObjectAnalysisClassTree tree;

    ObjectListPanel objectList;
    public ObjectFilterBar(ObjectAnalysisClassTree tree, ObjectListPanel list) {
        this.tree = tree;
        this.objectList = list;
        add(filterButton);
        filterField = new PlaceholderTextField();
        filterField.setPlaceholder("E.g. obj.f3 > 3");
        add(filterField);
        setBackground(UIManager.getColor("TextArea.background"));

        filterButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String filter = filterField.getText();
                Logger.log("Filter: " + filter);

                if(tree.getActiveClass() != null) {

                    objectList.setTags(CoreInterface.getInstance().getObjectTags(tree.getActiveClass().getFullDir(), filter),
                            tree.getActiveClass().getFullDir(),
                            tree.getActiveClass().getName());
                } else {
                    Logger.log("No active class.");
                }


            }
        });
        filterField.setMinimumSize(new Dimension(50, 23));

        filterField.setPreferredSize(new Dimension(100, 23));
        setMaximumSize(new Dimension(200, 100));
    }
}
