package org.jdbg.gui.tabs.objectanalysis.objlist;

import org.jdbg.core.CoreInterface;
import org.jdbg.gui.MainFrame;
import org.jdbg.gui.tabs.objectanalysis.ObjectAnalysisClassTree;
import org.jdbg.logger.Logger;

import javax.swing.*;
import javax.swing.border.Border;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.List;
import java.util.stream.Collectors;

public class ObjectListPanel extends JPanel {

    JList<TagItem> tagsList = new JList<>();
    public ObjectListPanel(ObjectAnalysisClassTree tree) {
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));
        setBackground(UIManager.getColor("TextArea.background"));
        Border verticalBorder =  new JTextField().getBorder();
        setFont(new Font(getFont().getName(), getFont().getStyle(), getFont().getSize()+2));

        setBorder(verticalBorder);



        add(new ObjectFilterBar(tree, this));
        JScrollPane scrollPane =
                new JScrollPane(tagsList, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS, JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);

        //TODO Bruh
        //swing sizes are genuinely wack so this will have to do
        setMaximumSize(new Dimension(200, 100000));
        setMinimumSize(new Dimension(200, 100000));

        setPreferredSize(new Dimension(200, 0));
        scrollPane.setMaximumSize(getMaximumSize());
        add(scrollPane);
        setupClick();

    }

    void setupClick() {
        tagsList.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                if(SwingUtilities.isRightMouseButton(e)) {

                    handleRightClick(e, tagsList.getModel().getElementAt(tagsList.locationToIndex(new Point(e.getX(), e.getY()))));

                }

                if(SwingUtilities.isLeftMouseButton(e)) {
                    handleLeftClick(e, tagsList.getModel().getElementAt(tagsList.locationToIndex(new Point(e.getX(), e.getY()))));
                }
            }
        });
    }

    void handleLeftClick(MouseEvent e, TagItem tagItem) {
        MainFrame.getInstance().getMainPane().getTabObjects().getMainHeapPanel().initObjectInfo(tagItem);
    }
    void handleRightClick(MouseEvent e, TagItem tagItem) {
        JPopupMenu menu = new JPopupMenu();
        JMenuItem item = new JMenuItem(new AbstractAction("Add \"" + tagItem.toString() + "\" to Object Workspace") {
            @Override
            public void actionPerformed(ActionEvent e) {
                MainFrame.getInstance().getMainPane().getTabObjects().getWorkspace().addTag(tagItem);
            }
        });

        menu.add(item);
        menu.show(this, e.getX(), e.getY());
    }

    public void setTags(List<Integer> tags, String klass, String name) {
        DefaultListModel<TagItem> model = new DefaultListModel<>();
        model.addAll(tags.stream().map(tag -> new TagItem(tag, klass, name)).collect(Collectors.toList()));
        tagsList.setModel(model);
    }
}
