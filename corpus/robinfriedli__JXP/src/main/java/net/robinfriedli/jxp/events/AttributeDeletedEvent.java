package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.XmlAttribute;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Element;

public class AttributeDeletedEvent extends ElementChangingEvent {

    private final XmlAttribute attribute;

    private Element persistentElement;

    public AttributeDeletedEvent(Context context, XmlElement source, XmlAttribute attribute) {
        super(context, source);
        this.attribute = attribute;
    }

    @Override
    public void doApply() {
        persistentElement = getSource().getElement();
        super.doApply();
    }

    @Override
    public void handleCommit() {
        if (persistentElement != null) {
            persistentElement.removeAttribute(attribute.getAttributeName());
        }
    }

    public XmlAttribute getAttribute() {
        return attribute;
    }

    @Override
    protected void revertCommit() {
        if (persistentElement != null) {
            persistentElement.setAttribute(attribute.getAttributeName(), attribute.getValue());
        }
    }
}
