package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.persist.Context;

public class ValueChangingEvent<V> extends HelperEvent {

    private final V oldValue;
    private final V newValue;

    public ValueChangingEvent(Context context, XmlElement source, V oldValue, V newValue) {
        super(context, source);
        this.oldValue = oldValue;
        this.newValue = newValue;
    }

    public V getOldValue() {
        return oldValue;
    }

    public V getNewValue() {
        return newValue;
    }
}
