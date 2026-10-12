package org.jdbg.core.bytecode.decompiler.vineflower;

import org.jetbrains.java.decompiler.main.extern.IFernflowerLogger;
import org.jdbg.logger.Logger;

public class VineflowerLogger extends IFernflowerLogger {

    public VineflowerLogger() {
    }

    @Override
    public void writeMessage(String message, Severity severity) {
        Logger.dbg("Fernflower - " + message);
    }

    @Override
    public void writeMessage(String message, Severity severity, Throwable throwable) {
        Logger.dbg("Fernflower - " + message + ": " + throwable.getMessage());
    }
}