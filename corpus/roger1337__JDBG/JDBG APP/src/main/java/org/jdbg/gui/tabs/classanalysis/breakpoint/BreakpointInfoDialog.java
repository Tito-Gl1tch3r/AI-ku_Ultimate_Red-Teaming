package org.jdbg.gui.tabs.classanalysis.breakpoint;

import org.jdbg.MiscUtil;
import org.jdbg.core.Util;
import org.jdbg.core.pipeline.impl.PipelineBreakpoint;
import org.jdbg.gui.buttonbar.process.Process;
import org.jdbg.gui.util.InfoBorder;

import javax.swing.*;
import java.awt.*;
import java.util.List;

public class BreakpointInfoDialog extends JDialog {

    public BreakpointInfoDialog(PipelineBreakpoint.BreakpointResponse response) {
        setTitle("Breakpoint Information");
        setLayout(new BoxLayout(getContentPane(), BoxLayout.Y_AXIS));
        setSize(new Dimension(300, 500));


        String origin = response.klassSignature + " -> " +  response.methodName + " : " + response.methodSignature;

        JTextArea area = new JTextArea(origin);
        area.setEditable(false);
        area.setBorder(new InfoBorder("Breakpoint Origin"));
        add(area);
        area.setMaximumSize(new Dimension(10000, 200));


        createStackTrace(response);
        createLocals(response);
    }

    void createLocals(PipelineBreakpoint.BreakpointResponse response) {
        JList<String> localVars = new JList<>();
        DefaultListModel<String> model = new DefaultListModel<>();
        for(PipelineBreakpoint.LocalVariableElement elm : response.localVars) {
            String line = MiscUtil.getBetterType(elm.signature) + " " + elm.name + " = " + elm.value;
            model.addElement(line);
        }

        localVars.setModel(model);
        JScrollPane stackPaneScrollPane = new JScrollPane(localVars, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS,  JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        stackPaneScrollPane.setBorder(new InfoBorder("Local Variables"));
        add(stackPaneScrollPane);
    }




    void createStackTrace(PipelineBreakpoint.BreakpointResponse response) {
        JList<String> stackTrace = new JList<>();
        DefaultListModel<String> model = new DefaultListModel<>();
        int idx = 1;
        for(PipelineBreakpoint.MyStackTraceElement elm : response.stackTrace) {
            String stackTraceLine = idx + ". " + format(elm.klassSignature, elm.methodName, elm.methodSignature);
            model.addElement(stackTraceLine);
            idx++;
        }
        stackTrace.setModel(model);
        JScrollPane stackPaneScrollPane = new JScrollPane(stackTrace, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS,  JScrollPane.HORIZONTAL_SCROLLBAR_AS_NEEDED);
        stackPaneScrollPane.setBorder(new InfoBorder("Stack Trace"));
        add(stackPaneScrollPane);
    }

    String format(String klassSignature, String methodName,String methodSignature) {
        return klassSignature + " -> " + methodName + " : " + methodSignature;
    }
}
