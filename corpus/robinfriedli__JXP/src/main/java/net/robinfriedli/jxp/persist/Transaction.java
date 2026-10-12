package net.robinfriedli.jxp.persist;

import java.util.List;
import java.util.concurrent.Callable;

import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.events.ElementChangingEvent;
import net.robinfriedli.jxp.events.ElementCreatedEvent;
import net.robinfriedli.jxp.events.ElementDeletingEvent;
import net.robinfriedli.jxp.events.Event;
import net.robinfriedli.jxp.exceptions.CommitException;
import net.robinfriedli.jxp.exec.QueuedTask;

/**
 * Interface for classes that manage running a write-transaction that applies changes to XmlElement instances, commits
 * them to the DOM document and finally writes them to the file, if the Context is persistent.
 */
public interface Transaction {

    static Transaction createTx(Context context) {
        return new BaseTransaction(context);
    }

    static ApplyOnlyTx createApplyOnlyTx(Context context) {
        return new ApplyOnlyTx(context);
    }

    static InstantApplyTx createInstantApplyTx(Context context) {
        return new InstantApplyTx(context);
    }

    static InstantApplyOnlyTx createInstantApplyOnlyTx(Context context) {
        return new InstantApplyOnlyTx(context);
    }

    Context getContext();

    /**
     * @return an immutable view of all changes added to this transaction
     */
    List<Event> getChanges();

    /**
     * @return all elements created in this transaction since the last flush
     */
    List<ElementCreatedEvent> getCreatedElements();

    /**
     * @return all element changes made in this transaction since the last flush
     */
    List<ElementChangingEvent> getElementChanges();

    /**
     * @param element the XmlElement instance to check
     * @return all changes recorded for this XmlElement since the last flush
     */
    List<ElementChangingEvent> getChangesForElement(XmlElement element);

    /**
     * @return all elements for which changes were recorded since the last flush, i.e. in state TOUCHED
     */
    List<XmlElement> getChangedElements();

    /**
     * @return all elements that were deleted since the last flush
     */
    List<ElementDeletingEvent> getDeletedElements();

    /**
     * @return all elements that were affected in any way, created, changed or deleted, since the last flush
     */
    List<XmlElement> getAffectedElements();

    /**
     * @return true if the transaction failed an is rolling back
     */
    boolean isRollback();

    /**
     * Queue a task to run after this transaction finishes, used by {@link Context#futureInvoke(Callable)}
     *
     * @param queuedTask the queued task
     */
    void queueTask(QueuedTask<?> queuedTask);

    /**
     * @return an immutable view of all tasks queued to this transaction
     */
    List<QueuedTask<?>> getQueuedTasks();

    /**
     * @return true if this is an apply-only transaction, meaning no commit is made, since 0.7 this is largely deprecated,
     * see {@link ApplyOnlyTx}
     */
    boolean isApplyOnly();

    /**
     * @return true if this transaction applies changes as soon as they are added, see {@link InstantApplyTx}
     */
    boolean isInstantApply();

    /**
     * @return true if this transaction can still be used to make additional changes
     */
    boolean isActive();

    /**
     * @return true only if no change has ever been recorded by this transaction, otherwise return false even if those
     * changes have already been flushed.
     */
    boolean isEmpty();

    /**
     * @return the state if the transaction
     */
    State getState();

    boolean failed();

    Internals internal();

    enum State {

        /**
         * the Transaction has been created by the {@link Context#invoke(Runnable)} method and is listening for changes
         */
        RUNNING(true),

        /**
         * The Transaction is applying all changes added to it. For {@link InstantApplyOnlyTx} this state will never
         * occur.
         */
        APPLYING(true),

        /**
         * The changes from this Transaction have been applied to the XmlElements but the Transaction has not been
         * committed yet. Transaction applied event listeners will be fired after this.
         */
        APPLIED(true),

        /**
         * The Transaction is being committed.
         */
        COMMITTING(false),

        /**
         * This Transaction has been fully committed. Transaction committed event listeners will be fired after this.
         */
        COMMITTED(false),

        /**
         * An exception occurred while applying or committing the Transaction meaning all changes will be reverted.
         * This also means any queued tasks added by listeners will be cancelled if cancelOnFailure is true.
         */
        ROLLING_BACK(false),

        /**
         * This Transaction has finished rolling back.
         */
        ROLLED_BACK(false);

        private final boolean useable;

        State(boolean useable) {
            this.useable = useable;
        }

        public boolean isUseable() {
            return useable;
        }

    }

    /**
     * Sub interface for methods intended for internal use to clearly separate them from the regular API while still allowing
     * access.
     */
    interface Internals {

        /**
         * Capture a change, creation or deletion of an XmlElement
         *
         * @param change the event to add to this transaction
         */
        void addChange(Event change);

        void addChanges(List<Event> changes);

        void addChanges(Event... changes);

        /**
         * Apply all recorded changes to XmlElement instances. In case of an {@link InstantApplyTx} each event is applied as
         * soon as it's added to the transaction. Else this is called after the task finished, meaning changes are not visible
         * during the task.
         */
        void apply();

        /**
         * Flushes all recorded changes and, if the Context is persistent, writes to the file.
         *
         * @param writeToFile whether the changes should be written to the file afterwards if necessary
         */
        void commit(boolean writeToFile) throws CommitException;

        default void commit() throws CommitException {
            commit(true);
        }

        /**
         * Flushes changes to the DOM document and clears recorded changes. Regularly this happens during the commit but in
         * case of a {@link SequentialTx} this can happen several times during the transaction. This does not write to the
         * file.
         */
        void flush() throws CommitException;

        /**
         * Revert all changes when the transaction fails and prevents it from being committed
         */
        void rollback();

        /**
         * Roll back the transaction if not already rolling back
         */
        void assertRollback();

        void setState(State state);

        /**
         * set the status of this transaction to failed, relevant for queued tasks
         */
        void fail();

        List<Event> getInternalChangesList();

        List<QueuedTask<?>> getInternalQueuedTasksList();

    }

}
