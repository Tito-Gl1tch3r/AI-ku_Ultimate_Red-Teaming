/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package org.unixlibre.persistence;

import java.util.function.Function;

/**
 *
 * @author Antonio Varela Lizardi <antonio@icon.net.mx>
 */
public abstract class CommandManager {
    
    private CommandExecutor executor = new CommandExecutor() {
        @Override
        public <T> void executeCommand(Command<T> cmd) {
            throw new UnsupportedOperationException("CommandExecutor not implemented");
        }
    };

    public CommandManager() {
    }

    public CommandManager(CommandExecutor executor) {
        this.executor = executor;
    }

    public abstract <T> T execute(Function<ExecutorContext, T> impl);

    public abstract <T> T execute(Command<T> cmd);

    public CommandExecutor getExecutor() {
        return executor;
    }

    public void setExecutor(CommandExecutor executor) {
        if (executor != null) {
            this.executor = executor;
        }
    }
    
    
}
