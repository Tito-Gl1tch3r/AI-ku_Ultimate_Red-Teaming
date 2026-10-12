package org.jdbg.core.pipeline;

import com.sun.jna.platform.win32.Kernel32;
import com.sun.jna.platform.win32.WinBase;
import com.sun.jna.platform.win32.WinNT;
import com.sun.jna.ptr.IntByReference;
import org.jdbg.logger.Logger;

public class Pipeline {


    private final int BUFFER_SIZE = 50000000;
     byte[] buffer = new byte[BUFFER_SIZE];

     Object test;
    private String pipeName;
    protected WinNT.HANDLE pipeHandle;


    public Pipeline(String pipeName) {
        this.pipeName = pipeName;
        createPipe();
    }
    protected void createPipe() {
        if(pipeHandle != null) {
            Kernel32.INSTANCE.CloseHandle(pipeHandle);
        }

        pipeHandle = Kernel32.INSTANCE.CreateNamedPipe(pipeName,
                WinBase.PIPE_ACCESS_DUPLEX,
                WinBase.PIPE_TYPE_BYTE,
                1,
                0,
                0,
                0,
                null);

        if(pipeHandle==null || pipeHandle == WinBase.INVALID_HANDLE_VALUE) {
            Logger.log("Failed to create pipe for: " + getClass().getName());
            return;
        }

        Logger.log("Created pipe");
    }

    protected void sendData(byte[] bytes) {
        IntByReference ref = new IntByReference(0);
        Kernel32.INSTANCE.WriteFile(pipeHandle, bytes, bytes.length, ref, null);

        if(ref.getValue() != bytes.length) {
            Logger.log("Send data was not equal?");
        }
    }



    protected byte[] readMessage() {
        IntByReference bytesRead = new IntByReference(0);
        Kernel32.INSTANCE.ReadFile(pipeHandle, buffer, BUFFER_SIZE, bytesRead, null);

        byte[] response = new byte[bytesRead.getValue()];
        System.arraycopy(buffer, 0, response, 0, bytesRead.getValue());
        return response;
    }

    public void shutdown() {
        Kernel32.INSTANCE.DisconnectNamedPipe(pipeHandle);
        Kernel32.INSTANCE.CloseHandle(pipeHandle);
    }



}
