package org.unixlibre.persistence.impl.jpa;

import org.unixlibre.persistence.Command;
import org.unixlibre.persistence.CommandExecutor;
import org.unixlibre.persistence.CommandManager;
import org.unixlibre.persistence.ExecutorContext;

import java.util.function.Function;

/**
 * Created by antoniovl on 13/05/17.
 */
public class JPACommandManager extends CommandManager {

    public JPACommandManager() {
    }

    public JPACommandManager(CommandExecutor executor) {
        super(executor);
    }

    @Override
    public <T> T execute(Function<ExecutorContext, T> impl) {
        JPACommand<T> cmd = new JPACommand<>();
        cmd.setImplementation(impl);
        return execute(cmd);
    }

    @Override
    public <T> T execute(Command<T> cmd) {
        getExecutor().executeCommand(cmd);
        return cmd.getResult();
    }
}
