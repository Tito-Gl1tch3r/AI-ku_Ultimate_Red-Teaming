package org.jdbg.gui.tabs.objectanalysis.objinfo;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionListener;

public class ObjectInfoInput extends JPanel {

    JButton button;
    JTextField field;
    public ObjectInfoInput(String info, String defaultValue, String buttonText) {
        setPreferredSize(new Dimension(200, 30));
        setLayout(new FlowLayout(FlowLayout.LEFT, 0, 0));
        setBorder(BorderFactory.createEmptyBorder(0, 0, 0, 0));


        JTextArea inf = new JTextArea(info);
        inf.setEditable(false);
        add(inf);
        field = new JTextField();
        field.setText(defaultValue);
        add(field);

        button = new JButton(buttonText);
        add(button);
    }

    public String getText() {
        return field.getText();
    }

    public void addActionListener(ActionListener listener) {
        button.addActionListener(listener);
    }


}
