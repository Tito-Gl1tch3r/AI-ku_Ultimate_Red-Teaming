package org.jdbg.gui.tabs.classanalysis.breakpoint;

import org.jdbg.core.attach.breakpoint.BreakpointManager;
import org.jdbg.gui.util.InfoBorder;

import javax.swing.*;
import java.awt.*;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class ManageBreakpointDialog extends JDialog {


    JScrollPane breakpointTable;

    public ManageBreakpointDialog() {
        setTitle("Breakpoint Information");
        setLayout(new BoxLayout(getContentPane(), BoxLayout.Y_AXIS));
        setSize(new Dimension(300, 500));


    }

    public void update(Map<String, Set<BreakpointManager.Breakpoint>> breakpointList) {
        if(breakpointTable != null) {
            remove(breakpointTable);
        }
        int size = 0;

        for(Map.Entry<String, Set<BreakpointManager.Breakpoint>> breakpoint : breakpointList.entrySet()) {
            size += breakpoint.getValue().size();
        }

        String[][] str = new String[size][3];

        int i = 0;
        for(Map.Entry<String, Set<BreakpointManager.Breakpoint>> breakpoint : breakpointList.entrySet()) {
            for(BreakpointManager.Breakpoint bp : breakpoint.getValue()) {
                str[i][0] = breakpoint.getKey();
                str[i][1] = bp.identifier;
                str[i][2] = String.valueOf(bp.offset);
                i++;
            }
        }


        JTable table = new JTable(str, new String[] {"Class", "Method", "Offset"});
        JScrollPane scrollPane = new JScrollPane(table, ScrollPaneConstants.VERTICAL_SCROLLBAR_AS_NEEDED,
                ScrollPaneConstants.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        scrollPane.setBorder(new InfoBorder("Breakpoints"));
        add(scrollPane);
        breakpointTable = scrollPane;   
        revalidate();
    }
}
