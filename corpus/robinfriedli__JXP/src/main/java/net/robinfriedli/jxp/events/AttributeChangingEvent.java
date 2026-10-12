package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.XmlAttribute;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Element;

public class AttributeChangingEvent extends ElementChangingEvent {

    private final XmlAttribute attribute;
    private final String oldValue;
    private final String newValue;

    private Element persistentElem;

    public AttributeChangingEvent(Context context, XmlAttribute attribute, String newValue) {
        super(context, attribute.getParentElement());
        this.attribute = attribute;
        oldValue = attribute.getValue();
        this.newValue = newValue;
    }

    @Override
    public void doApply() {
        persistentElem = getSource().getElement();
        super.doApply();
    }

    @Override
    public void handleCommit() {
        if (persistentElem != null) {
            persistentElem.setAttribute(attribute.getAttributeName(), newValue);
        }
    }

    public XmlAttribute getAttribute() {
        return attribute;
    }

    public String getOldValue() {
        return oldValue;
    }

    public String getNewValue() {
        return newValue;
    }

    @Override
    protected void revertCommit() {
        if (persistentElem != null) {
            persistentElem.setAttribute(attribute.getAttributeName(), oldValue);
        }
    }
}
