package org.jdbg.gui.tabs.classanalysis;

import org.jdbg.gui.tabs.classanalysis.asm.AsmTabbedPane;
import org.jdbg.gui.tabs.classanalysis.codepanel.AsmCodePanel;
import org.jdbg.gui.tabs.classanalysis.codepanel.CodePanel;
import org.jdbg.gui.tabs.classanalysis.tabbed.ThinTabbedPane;

import javax.swing.*;

public class BytecodeViewTabbedPane extends ThinTabbedPane {

    CodePanel dec;
    AsmTabbedPane asm;
    public BytecodeViewTabbedPane(CodePanel decompiled, AsmTabbedPane assembly) {
        addTab("Assembly View", assembly);
        addTab("Decompiled View", decompiled);
        this.dec = decompiled;
        this.asm = assembly;

        dec.getText().setBorder(BorderFactory.createMatteBorder(0, 1, 1, 1, UIManager.getColor("Button.borderColor")));

        //asm.setBorder(BorderFactory.createMatteBorder(0, 1, 0, 1, UIManager.getColor("Button.borderColor")));


    }

    public CodePanel getDec() {
        return dec;
    }

    public AsmTabbedPane getAsm() {
        return asm;
    }
}
