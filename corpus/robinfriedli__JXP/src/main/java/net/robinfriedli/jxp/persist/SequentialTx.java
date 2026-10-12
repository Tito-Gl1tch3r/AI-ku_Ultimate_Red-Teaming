package net.robinfriedli.jxp.persist;

import net.robinfriedli.jxp.events.Event;
import net.robinfriedli.jxp.exceptions.CommitException;
import net.robinfriedli.jxp.exceptions.PersistException;

/**
 * Transaction extension that flushes and clears all changes each time the defined number of changes is reached.
 * In case of a {@link LazyContext} this also clears stored created and deleted elements. Used to reduce memory usage
 * for massive transactions.
 */
public class SequentialTx extends InstantApplyTx {

    private final int sequence;

    public SequentialTx(Context context, int sequence) {
        super(context);
        this.sequence = sequence;
    }

    @Override
    protected InstantApplyInternalControl createControl() {
        return new InternalControl();
    }

    private class InternalControl extends InstantApplyInternalControl {

        @Override
        public void addChange(Event change) {
            if (getChanges().size() == sequence) {
                try {
                    flush();
                } catch (CommitException e) {
                    throw new PersistException("Exception in flush", e);
                }
            }
            super.addChange(change);
        }

    }

}
