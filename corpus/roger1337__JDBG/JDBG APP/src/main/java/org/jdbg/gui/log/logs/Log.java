package org.jdbg.gui.log.logs;

import javax.swing.*;
import java.awt.*;

public abstract class Log extends JTextArea {



    public Log() {
        setBackground(UIManager.getColor("Table.background"));
        setEditable(false);
        setMargin(new Insets(0, 20, 30, 0));

    }


    public abstract void addLog(String text);



}
