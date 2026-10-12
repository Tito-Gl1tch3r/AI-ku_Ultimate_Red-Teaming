package org.jdbg.gui.tabs.objectanalysis;

import org.jdbg.Main;
import org.jdbg.WrapperTest;
import org.jdbg.gui.tabs.objectanalysis.objlist.ObjectListPanel;
import org.jdbg.gui.tabs.objectanalysis.objlist.TagItem;

import javax.swing.*;
import java.awt.*;
import java.util.List;

public class SavedWorkspace extends JPanel {

    JList<TagItem> tagsList;

    public SavedWorkspace() {
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));

        setBackground(UIManager.getColor("TextArea.background"));
        JTextArea text = new JTextArea("Saved Object Workspace");
        text.setFont(new Font(getFont().getName(), getFont().getStyle(), getFont().getSize()+2));
        text.setMaximumSize(new Dimension(1000, 40));
        text.setBorder(BorderFactory.createMatteBorder(0, 1, 0, 1, UIManager.getColor("Button.borderColor")));
        add(text);

        tagsList = new JList<>();
        JScrollPane scrollPane =
                new JScrollPane(tagsList, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS, JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);

        tagsList.setModel(new DefaultListModel<>());


        add(scrollPane);
    }

    public void addTag(Integer tag, String klass, String name) {
        TagItem item = new TagItem(tag, klass, name);
        addTag(item);
    }


    public void addTag(TagItem it) {
        TagItem item = new TagItem(it);
        item.setIncludeDir(true);

        DefaultListModel<TagItem> model =(DefaultListModel<TagItem>)tagsList.getModel();
        model.add(model.size(), item);
        tagsList.setModel(model);
    }
}
