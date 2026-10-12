package net.robinfriedli.jxp.persist;

import org.w3c.dom.Element;

/**
 * Type of transaction used by the Context#apply method. Use cautiously when dealing with changes that would break a
 * regular commit one way or the other. Was used before JXP v0.7 to deal with duplicate Elements because the XmlPersister
 * could not find / uniquely identify the {@link Element} that needed to be changed. But then 0.7 eliminated the need to
 * locate the Element in the first place meaning all obvious use cases for this class vanished. Only use if you know
 * what you are doing.
 */
public class ApplyOnlyTx extends AbstractTransaction {

    private final InternalControl internalControl = new InternalControl();

    public ApplyOnlyTx(Context context) {
        super(context);
    }

    @Override
    public boolean isApplyOnly() {
        return true;
    }

    @Override
    public Internals internal() {
        return internalControl;
    }

    private class InternalControl extends DefaultInternalControl {

        @Override
        public void commit(boolean writeToFile) {
            throw new UnsupportedOperationException("Attempting to commit an apply-only Transaction");
        }

    }

}
