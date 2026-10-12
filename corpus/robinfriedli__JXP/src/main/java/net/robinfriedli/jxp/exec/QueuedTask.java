package net.robinfriedli.jxp.exec;

import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.FutureTask;

import org.slf4j.Logger;

import net.robinfriedli.exec.Mode;
import net.robinfriedli.jxp.persist.Context;

/**
 * Task that encapsulates transactions happening sometime in the future. this may and often is used to queue tasks after
 * the current transaction to then run them in the same thread. For that reason those tasks do not run synchronised as
 * their parent task already does. Else this can be used to execute tasks in a separate thread, in this case the sync
 * mode should be applied, see {@link Context#futureInvoke(boolean, boolean, Mode, Callable)}.
 *
 * @param <E> the return type of the task.
 */
public class QueuedTask<E> extends FutureTask<E> {

    private final boolean cancelOnFailure;
    private final Logger logger;

    public QueuedTask(Context context, boolean cancelOnFailure, Mode mode, Callable<E> callable, Logger logger) {
        super(() -> context.invoke(mode, callable));
        this.cancelOnFailure = cancelOnFailure;
        this.logger = logger;
    }

    public void runLoggingErrors() {
        super.run();
        try {
            get();
        } catch (InterruptedException | ExecutionException e) {
            logger.error("Exception thrown by QueuedTask", e);
        }
    }

    public boolean isCancelOnFailure() {
        return cancelOnFailure;
    }
}
