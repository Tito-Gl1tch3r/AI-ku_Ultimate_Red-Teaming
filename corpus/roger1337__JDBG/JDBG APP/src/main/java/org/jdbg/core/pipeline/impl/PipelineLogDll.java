package org.jdbg.core.pipeline.impl;

import com.sun.jna.platform.win32.Kernel32;
import org.jdbg.core.pipeline.ListenerPipe;
import org.jdbg.core.pipeline.Pipeline;
import org.jdbg.gui.log.logs.impl.LogAgent;
import org.jdbg.logger.Logger;

import java.util.List;

public class PipelineLogDll extends ListenerPipe {

    static PipelineLogDll instance;

    public PipelineLogDll() {
        super("\\\\.\\pipe\\jdbg_log");
    }

    @Override
    protected void onStart() {
        if(Kernel32.INSTANCE.ConnectNamedPipe(pipeHandle, null)) {
            Logger.log("Client connected to log pipe");
        } else {
            Logger.dbg("ConnectNamedPipe returned false for Log Pipeline");
        }
    }
    @Override

    public boolean loop() {
        byte[] bytes = readMessage();

        if(bytes.length==0) {
            return false;
        }
        Logger.log("Got a log msg");
        LogAgent.getInstance().addLog(new String(bytes));
        return true;
    }

    public static void init() {
        instance = new PipelineLogDll();
    }

    public static PipelineLogDll getInstance() {
        return instance;
    }
}
