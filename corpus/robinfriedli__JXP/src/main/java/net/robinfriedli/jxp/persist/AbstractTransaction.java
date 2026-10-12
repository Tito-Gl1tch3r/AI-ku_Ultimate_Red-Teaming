package net.robinfriedli.jxp.persist;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.stream.Collectors;

import org.slf4j.Logger;

import com.google.common.collect.Lists;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.events.ElementChangingEvent;
import net.robinfriedli.jxp.events.ElementCreatedEvent;
import net.robinfriedli.jxp.events.ElementDeletingEvent;
import net.robinfriedli.jxp.events.Event;
import net.robinfriedli.jxp.exceptions.CommitException;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.exec.QueuedTask;

/**
 * Base implementation for all transaction types. Holds all {@link Event}s that have been created within the current
 * transaction and applies them to the {@link XmlElement} instances when the transaction finishes if this is not an {@link InstantApplyTx}
 * and, if commit is true, saves them to the XML file. Also reverts changes if the transaction failed.
 * This implementation is collecting-apply, rather than instant-apply, meaning changes made to XmlElement instances
 * are not immediately visible but only when applying the transaction. However, when using {@link Context#invoke(Runnable)}
 * the instantApply parameter is true by default, meaning an {@link InstantApplyTx} is used.
 */
public abstract class AbstractTransaction implements Transaction {

    private final Context context;
    private final LinkedList<Event> changes;
    private final List<QueuedTask<?>> queuedTasks;

    private boolean isEmpty = true;
    private boolean rollback = false;
    private boolean failed = false;
    private State state;

    public AbstractTransaction(Context context) {
        this.context = context;
        this.changes = Lists.newLinkedList();
        state = State.RUNNING;
        queuedTasks = Lists.newArrayList();
    }

    @Override
    public Context getContext() {
        return context;
    }

    @Override
    public List<Event> getChanges() {
        return Collections.unmodifiableList(changes);
    }

    @Override
    public List<ElementCreatedEvent> getCreatedElements() {
        return changes.stream()
            .filter(change -> change instanceof ElementCreatedEvent)
            .map(change -> (ElementCreatedEvent) change)
            .collect(Collectors.toList());
    }

    @Override
    public List<ElementChangingEvent> getElementChanges() {
        return changes.stream()
            .filter(change -> change instanceof ElementChangingEvent)
            .map(change -> (ElementChangingEvent) change)
            .collect(Collectors.toList());
    }

    @Override
    public List<ElementChangingEvent> getChangesForElement(XmlElement element) {
        return getElementChanges().stream().filter(change -> change.getSource() == element).collect(Collectors.toList());
    }

    @Override
    public List<XmlElement> getChangedElements() {
        return getElementChanges().stream().map(Event::getSource).collect(Collectors.toList());
    }

    @Override
    public List<ElementDeletingEvent> getDeletedElements() {
        return changes.stream()
            .filter(change -> change instanceof ElementDeletingEvent)
            .map(change -> (ElementDeletingEvent) change)
            .collect(Collectors.toList());
    }

    @Override
    public List<XmlElement> getAffectedElements() {
        return changes.stream().map(Event::getSource).collect(Collectors.toList());
    }

    @Override
    public boolean isRollback() {
        return rollback;
    }

    @Override
    public void queueTask(QueuedTask<?> queuedTask) {
        queuedTasks.add(queuedTask);
    }

    @Override
    public List<QueuedTask<?>> getQueuedTasks() {
        return Collections.unmodifiableList(queuedTasks);
    }

    @Override
    public boolean isApplyOnly() {
        return false;
    }

    @Override
    public boolean isInstantApply() {
        return false;
    }

    @Override
    public boolean isActive() {
        if (isInstantApply()) {
            return getState().isUseable();
        } else {
            return getState() == State.RUNNING;
        }
    }

    @Override
    public boolean isEmpty() {
        return isEmpty;
    }

    @Override
    public State getState() {
        return state;
    }

    @Override
    public boolean failed() {
        return failed;
    }

    protected class DefaultInternalControl implements Internals {

        @Override
        public void addChange(Event change) {
            isEmpty = false;
            if (isActive()) {
                changes.add(change);
            } else {
                throw new IllegalStateException("Transaction is not recording changes");
            }
        }

        @Override
        public void addChanges(List<Event> changes) {
            isEmpty = false;
            if (isActive()) {
                AbstractTransaction.this.changes.addAll(changes);
            } else {
                throw new IllegalStateException("Transaction is not recording changes");
            }
        }

        @Override
        public void addChanges(Event... changes) {
            addChanges(Arrays.asList(changes));
        }

        @Override
        public void apply() {
            setState(State.APPLYING);
            for (Event change : changes) {
                try {
                    change.apply();
                } catch (Exception e) {
                    try {
                        rollback();
                    } catch (Exception e1) {
                        // log exception instead of re-throwing to not suppress the exception that caused applying to fail
                        Logger logger = context.getBackend().getLogger();
                        logger.error("Exception while trying to roll back changes", e1);
                    }
                    throw new PersistException("Exception while applying transaction. Rolled back.", e);
                }
            }

            setState(State.APPLIED);
            context.getBackend().fireTransactionApplied(AbstractTransaction.this);
        }

        @Override
        public void commit(boolean writeToFile) throws CommitException {
            if (!isRollback()) {
                try {
                    setState(State.COMMITTING);
                    flush();

                    if (writeToFile && context.isPersistent() && !isEmpty()) {
                        StaticXmlParser.writeToFile(context);
                    }

                    setState(State.COMMITTED);
                } catch (Exception e) {
                    try {
                        rollback();
                    } catch (Exception e1) {
                        // log exception instead of re-throwing to not suppress the exception that caused the commit to fail
                        Logger logger = context.getBackend().getLogger();
                        logger.error("Exception while trying to roll back changes", e1);
                    }
                    throw new CommitException("Exception during commit. Transaction rolled back.", e);
                }
            } else {
                throw new CommitException("Cannot commit transaction that was rolled back");
            }

            context.getBackend().fireTransactionCommitted(AbstractTransaction.this);
        }

        @Override
        public void flush() throws CommitException {
            context.getBackend().fireOnBeforeFlush(AbstractTransaction.this);
            for (Event change : changes) {
                if (change.isApplied()) {
                    change.commit();
                } else {
                    throw new CommitException("Trying to commit a change that has not been applied.");
                }
            }

            changes.clear();
        }

        @Override
        public void rollback() {
            setState(State.ROLLING_BACK);
            rollback = true;
            fail();
            // reverse list so that the first change added is the last one to get rolled back to restore data step by step correctly
            changes.descendingIterator().forEachRemaining(Event::revert);
            setState(State.ROLLED_BACK);
        }

        @Override
        public void assertRollback() {
            if (!rollback) {
                rollback();
            }
        }

        @Override
        public void setState(State state) {
            AbstractTransaction.this.state = state;
        }

        @Override
        public void fail() {
            failed = true;
        }

        @Override
        public List<Event> getInternalChangesList() {
            return changes;
        }

        @Override
        public List<QueuedTask<?>> getInternalQueuedTasksList() {
            return queuedTasks;
        }

    }

}
