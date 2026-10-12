package org.jdbg.core.pipeline;

import com.sun.jna.platform.win32.Kernel32;
import org.jdbg.core.pipeline.jna.Kernel32Additional;

import java.awt.image.Kernel;

public abstract class ListenerPipe extends Pipeline implements Runnable {

    private volatile boolean running = true;

    public ListenerPipe(String s) {
        super(s);
    }
    @Override
    public void run() {
        running = true;
        onStart();
        while(running) {
            if(!loop()) {
                break;
            }
        }
    }

    protected abstract void onStart();
    protected abstract boolean loop();

    public void cease() {
        Kernel32Additional.INSTANCE.CancelIoEx(pipeHandle, null);
        Kernel32.INSTANCE.CloseHandle(pipeHandle);
        createPipe();
        running = false;
    }
}
