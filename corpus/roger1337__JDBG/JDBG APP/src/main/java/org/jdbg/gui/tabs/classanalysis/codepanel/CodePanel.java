package org.jdbg.gui.tabs.classanalysis.codepanel;


import org.fife.ui.rtextarea.RTextScrollPane;
import org.jdbg.gui.tabs.classanalysis.codepanel.comp.CodeText;

import javax.swing.*;
import java.awt.*;

public class CodePanel extends JPanel {

    CodeText text;
    protected RTextScrollPane scrollPane;
    public CodePanel() {
        setLayout(new GridLayout());
        text = new CodeText();
        scrollPane = new RTextScrollPane(text);
        scrollPane.getGutter().setBorderColor(UIManager.getColor("TextArea.background"));

        add(scrollPane);
    }


    public void setSyntax(String s) {
        text.setSyntaxEditingStyle(s);
    }



    public void setText(String s) {
        text.setText(s);
    }

    public CodeText getText() {
        return text;
    }
}
