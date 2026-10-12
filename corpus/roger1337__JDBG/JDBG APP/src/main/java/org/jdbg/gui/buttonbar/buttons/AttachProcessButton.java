package org.jdbg.gui.buttonbar.buttons;

import org.jdbg.gui.buttonbar.process.ProcessSelectDialog;

import javax.swing.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class AttachProcessButton extends JButton {
    public AttachProcessButton() {
        super("Attach Process");
        addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                handleClick(e);
            }
        });
    }

    void handleClick(ActionEvent e) {

        ProcessSelectDialog dialog = new ProcessSelectDialog();
        dialog.setVisible(true);
    }


}
