package org.jdbg.gui.tabs.classanalysis.tree;

import org.jdbg.gui.tabs.ClassTreeNode;
import org.jdbg.gui.util.PlaceholderTextField;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.tree.DefaultTreeModel;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyAdapter;
import java.awt.event.KeyEvent;

public class ClassAnalysisPanel extends JPanel {



    ClassAnalysisTree tree;

    public ClassAnalysisPanel(ClassAnalysisTree tree) {
        this.tree = tree;
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));

        JScrollPane pane = new JScrollPane(tree, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS,  JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        pane.setBorder(BorderFactory.createMatteBorder(0, 1, 0, 1, UIManager.getColor("Button.borderColor")));

        pane.setFocusable(false);
        add(pane);

        JPanel filter = new JPanel();
        filter.setLayout(new BorderLayout());
        filter.setBorder(new EmptyBorder(3, 3, 3, 3));
        PlaceholderTextField field = new PlaceholderTextField();
        field.setPlaceholder("Filter Class Name");
        field.addKeyListener(new KeyAdapter() {
            @Override
            public void keyReleased(KeyEvent e) {
                String s = field.getText();


                for(ClassTreeNode node : tree.getLeaves()) {



                    if(node.getFullDir().contains(s)) {
                        ( (ClassTreeNode)node.getParent()).add(node);
                    } else {
                        ( (ClassTreeNode)node.getParent()).removeFromVisible(node);
                    }
                }

                tree.reload();

            }
        });



        filter.setMaximumSize(new Dimension(100000, 100));
        filter.add(field);

        add(filter);

    }


}
