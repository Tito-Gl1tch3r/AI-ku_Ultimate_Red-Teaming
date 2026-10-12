package net.robinfriedli.jxp.events;

import java.util.List;

import com.google.common.collect.Lists;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.exec.QueuedTask;
import net.robinfriedli.jxp.persist.AbstractTransaction;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.Transaction;

public abstract class Event {

    private final Context context;
    private final XmlElement source;

    private boolean isVirtual;

    private boolean applied = false;

    private boolean committed = false;

    public Event(Context context, XmlElement source) {
        this.context = context;
        this.source = source;
    }

    /**
     * Set all events captured while running the provided task to virtual. This used when operating on an element or
     * a child element of an element that is neither detached nor persistent, meaning the steps required for a persistent
     * element are not required. Most common use cases is persisting or deleting a child element of a non persistent and
     * non detached element.
     *
     * @param runnable the task to run
     * @param context  the persist context of the current transaction
     */
    public static void virtualiseEvents(Runnable runnable, Context context) {
        Transaction transaction = context.getTransaction();
        // if the transaction is apply-only VirtualEvents are not required anyway
        if (transaction == null || !transaction.isApplyOnly()) {
            List<Event> virtualEvents = Lists.newArrayList();
            TransactionMock transactionMock = new TransactionMock(context, virtualEvents, transaction == null || transaction.isInstantApply());

            context.internal().setTransaction(transactionMock);
            runnable.run();
            if (transaction != null) {
                transaction.internal().getInternalChangesList().addAll(virtualEvents);
            }

            if (!transactionMock.getQueuedTasks().isEmpty()) {
                for (QueuedTask<?> queuedTask : transactionMock.getQueuedTasks()) {
                    if (transaction != null) {
                        transaction.queueTask(queuedTask);
                    } else {
                        queuedTask.runLoggingErrors();
                    }
                }
            }

            context.internal().setTransaction(transaction);
        } else {
            runnable.run();
        }
    }

    public Context getContext() {
        return context;
    }

    public XmlElement getSource() {
        return this.source;
    }

    public final void apply() {
        if (isApplied()) {
            throw new PersistException("Change has already been applied");
        }

        doApply();
        if (!isVirtual) {
            applyPhysical();
        }

        setApplied(true);
        // context not null for non-detached XmlElement instance
        //noinspection ConstantConditions
        dispatchEvent(getSource().getContext().getBackend());
    }

    /**
     * Method used by Events that execute additional steps when applying a change to an element in physical state.
     * Default implementation is empty as most events to not require this step.
     */
    protected void applyPhysical() {
    }

    protected abstract void doApply();

    public final void revert() {
        if (isApplied()) {
            doRevert();
        }

        if (isCommitted()) {
            revertCommit();
        }
    }

    protected abstract void doRevert();

    protected abstract void revertCommit();

    public final void commit() {
        if (!isVirtual) {
            doCommit();
            setCommitted(true);
        }
    }

    protected abstract void doCommit();

    public boolean isApplied() {
        return applied;
    }

    public void setApplied(boolean applied) {
        this.applied = applied;
    }

    protected abstract void dispatchEvent(JxpBackend backend);

    public boolean isCommitted() {
        return committed;
    }

    public void setCommitted(boolean committed) {
        this.committed = committed;
    }

    public void setVirtual(boolean virtual) {
        isVirtual = virtual;
    }

    private static class TransactionMock extends AbstractTransaction {

        private final TransactionMock.InternalControl internalControl = new TransactionMock.InternalControl();

        private final List<Event> capturedEvents;
        private final boolean instantApply;

        private TransactionMock(Context context, List<Event> capturedEvents, boolean instantApply) {
            super(context);
            this.capturedEvents = capturedEvents;
            this.instantApply = instantApply;
        }

        @Override
        public boolean isEmpty() {
            return capturedEvents.isEmpty();
        }

        @Override
        public Internals internal() {
            return internalControl;
        }

        private class InternalControl extends DefaultInternalControl {

            @Override
            public void addChange(Event event) {
                event.setVirtual(true);
                capturedEvents.add(event);
                if (instantApply) {
                    event.apply();
                }
            }

            @Override
            public void addChanges(List<Event> events) {
                events.forEach(this::addChange);
            }

            @Override
            public void apply() {
                throw new UnsupportedOperationException();
            }

            @Override
            public void commit(boolean writeToFile) {
                throw new UnsupportedOperationException();
            }

        }

    }
}
