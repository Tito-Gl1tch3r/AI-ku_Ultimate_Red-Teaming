package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.XmlAttribute;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Element;

public class AttributeCreatedEvent extends ElementChangingEvent {

    private final String value;
    private final XmlAttribute attribute;

    private Element persistentElem;

    public AttributeCreatedEvent(Context context, XmlAttribute attribute) {
        super(context, attribute.getParentElement());
        this.value = attribute.getValue();
        this.attribute = attribute;
    }

    public XmlAttribute getAttribute() {
        return attribute;
    }

    @Override
    public void doApply() {
        persistentElem = getSource().getElement();
        super.doApply();
    }

    @Override
    protected void handleCommit() {
        if (persistentElem != null) {
            persistentElem.setAttribute(attribute.getAttributeName(), value);
        }
    }

    @Override
    protected void revertCommit() {
        if (persistentElem != null) {
            persistentElem.removeAttribute(attribute.getAttributeName());
        }
    }
}
