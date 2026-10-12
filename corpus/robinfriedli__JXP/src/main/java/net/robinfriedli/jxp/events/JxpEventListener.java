package net.robinfriedli.jxp.events;


import java.util.EventListener;

import net.robinfriedli.jxp.persist.SequentialTx;
import net.robinfriedli.jxp.persist.Transaction;

@SuppressWarnings("unused")
public abstract class JxpEventListener implements EventListener {

    private final boolean mayInterrupt;

    protected JxpEventListener() {
        this(false);
    }

    protected JxpEventListener(boolean mayInterrupt) {
        this.mayInterrupt = mayInterrupt;
    }

    /**
     * Fired when an {@link ElementCreatedEvent} was applied
     *
     * @param event the ElementCreatedEvent
     */
    public void elementCreating(ElementCreatedEvent event) {
    }

    /**
     * Fired when an {@link ElementDeletingEvent} was applied
     *
     * @param event the ElementDeletingEvent
     */
    public void elementDeleting(ElementDeletingEvent event) {
    }

    /**
     * Fired when an {@link ElementChangingEvent} was applied
     *
     * @param event the ElementChangingEvent
     */
    public void elementChanging(ElementChangingEvent event) {
    }

    /**
     * Fired after a {@link Transaction} has been applied (to the in memory elements)
     *
     * @param transaction the transaction that has been applied
     */
    public void transactionApplied(Transaction transaction) {
    }

    /**
     * Fired after a {@link Transaction} has been committed (to the XML file). Note that this happens after the flush, so
     * you can't access the changes committed by this transaction anymore. If you need to access these changes see
     * {@link #onBeforeFlush(Transaction)}
     *
     * @param transaction the transaction that has been committed
     */
    public void transactionCommitted(Transaction transaction) {
    }

    /**
     * Fired before a {@link Transaction} is flushed. Usually happens during a commit or during a {@link SequentialTx}.
     *
     * @param transaction the transaction that has been flushed
     */
    public void onBeforeFlush(Transaction transaction) {
    }

    /**
     * the mayInterrupt parameter defines if an exception thrown by this listener should interrupt the transaction or
     * be ignored
     */
    public boolean mayInterrupt() {
        return mayInterrupt;
    }
}
