package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.persist.Context;

public class HelperEvent extends Event {

    public HelperEvent(Context context, XmlElement source) {
        super(context, source);
    }

    @Override
    public void doApply() {
        throw new UnsupportedOperationException("Cannot apply " + this.getClass().getName());
    }

    @Override
    public void doRevert() {
        throw new UnsupportedOperationException("Cannot revert " + this.getClass().getName());
    }

    @Override
    protected void revertCommit() {
        throw new UnsupportedOperationException();
    }

    @Override
    public void doCommit() {
        throw new UnsupportedOperationException("Cannot commit " + this.getClass().getName());
    }

    @Override
    protected void dispatchEvent(JxpBackend backend) {
        throw new UnsupportedOperationException();
    }
}
