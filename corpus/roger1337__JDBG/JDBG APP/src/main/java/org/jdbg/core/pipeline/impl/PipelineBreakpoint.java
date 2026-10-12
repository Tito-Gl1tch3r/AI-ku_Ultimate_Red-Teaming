package org.jdbg.core.pipeline.impl;

import com.fasterxml.jackson.annotation.JsonClassDescription;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.jna.platform.win32.Kernel32;
import org.jdbg.core.pipeline.ListenerPipe;
import org.jdbg.core.pipeline.Pipeline;
import org.jdbg.core.pipeline.response.SubGraphData;
import org.jdbg.gui.MainFrame;
import org.jdbg.gui.log.logs.impl.LogAgent;
import org.jdbg.logger.Logger;

import javax.swing.*;
import java.util.List;
import java.util.Map;

public class PipelineBreakpoint extends ListenerPipe {

    public static class MyStackTraceElement {
        public String signature;

        public String klassSignature;
        public String methodName;
        public String methodSignature;
        public int location;
    }

    public static class LocalVariableElement {
        public String signature;
        public String name;
        public String value;
    }
    public static class BreakpointResponse {
        public String klassSignature;
        public String methodName;
        public String methodSignature;
        public List<MyStackTraceElement> stackTrace;
        public List<LocalVariableElement> localVars;

    }

    public static PipelineBreakpoint instance;
    public PipelineBreakpoint() {
        super("\\\\.\\pipe\\jdbg_breakpoint");
    }

    private volatile boolean continueBreakpoint = false;


    @Override
    protected void onStart() {
        Logger.log("Awaiting breakpoint pipe");

        if(Kernel32.INSTANCE.ConnectNamedPipe(pipeHandle, null)) {
            Logger.log("Client connected to breakpoint pipe.");
        } else {
            Logger.dbg("ConnectNamedPipe returned false for Breakpoint Pipeline");

        }
    }
    @Override

    public boolean loop() {
        try {
            continueBreakpoint = false;
            byte[] bytes = readMessage();

            if(bytes.length == 0) {
                return false;
            }
            ObjectMapper mapper = new ObjectMapper();
            Logger.log("Got a Breakpoint msg: " + new String(bytes));
            BreakpointResponse data = mapper.readValue(new String(bytes), new TypeReference<BreakpointResponse>() {});

            SwingUtilities.invokeLater(() -> {
                MainFrame.getInstance().getMainPane().getTabClasses().getBreakpointBar().breakpointHit(data);
            });

            while(!continueBreakpoint) {
                synchronized (this) {
                    wait();
                }
            }

            // Send some random stuff to stop blocking
            sendData(new byte[1]);

        } catch (Exception e) {
            e.printStackTrace();
        }

        return true;
    }

    public static void init() {
        instance = new PipelineBreakpoint();
    }

    public void continueExecution() {
        continueBreakpoint = true;
        synchronized (this) {
            notifyAll();
        }
    }


    public static PipelineBreakpoint getInstance() {
        return instance;
    }
}
