package net.robinfriedli.jxp.events;

import java.util.List;

import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.api.XmlAttribute;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.ElementUtils;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

public class ElementCreatedEvent extends Event {

    private final XmlElement newParent;
    private final Node<?> refNode;
    private final boolean insertAfter;

    private Element createdElement;
    private XmlElement effectiveParent;
    private Element parentElem;

    public ElementCreatedEvent(Context context, XmlElement element, XmlElement newParent, Node<?> refNode, boolean insertAfter) {
        super(context, element);
        this.newParent = newParent;
        this.refNode = refNode;
        this.insertAfter = insertAfter;

        element.internal().setState(XmlElement.State.PERSISTING);
    }

    @Override
    public void doApply() {
        XmlElement source = getSource();

        if (newParent != null) {
            source.internal().setParent(newParent);
            if (refNode != null) {
                newParent.internal().adoptChild(source, refNode, insertAfter);
            } else {
                newParent.internal().adoptChild(source);
            }
        } else if (source.getParent() == null) {
            throw new PersistException("Cannot persist as root element, requires a parent.");
        }

        effectiveParent = source.getParent();
    }

    @Override
    protected void applyPhysical() {
        XmlElement source = getSource();
        Document document = getContext().getDocument();
        XmlElement.Internals internalControl = source.internal();

        createdElement = document.createElement(source.getTagName());
        List<XmlAttribute> attributes = source.getAttributes();
        for (XmlAttribute attribute : attributes) {
            createdElement.setAttribute(attribute.getAttributeName(), attribute.getValue());
        }

        internalControl.setElement(createdElement);

        parentElem = effectiveParent.getElement();
    }

    @Override
    public void doRevert() {
        XmlElement source = getSource();
        source.internal().removeElement();
        effectiveParent.internal().removeChild(source);
        source.internal().removeParent();

        source.internal().setState(XmlElement.State.CONCEPTION);
    }

    @Override
    protected void revertCommit() {
        ElementUtils.destroy(createdElement);
    }

    @Override
    public void doCommit() {
        if (createdElement == null) {
            throw new IllegalStateException("Element was never created. Event was never physically applied.");
        }

        XmlElement source = getSource();
        source.internal().addToDOM(createdElement, parentElem, refNode, insertAfter);

        if (!source.hasChanges()) {
            source.internal().setState(XmlElement.State.CLEAN);
        } else {
            source.internal().setState(XmlElement.State.TOUCHED);
        }
    }

    @Override
    protected void dispatchEvent(JxpBackend backend) {
        backend.fireElementCreating(this);
    }

    public XmlElement getNewParent() {
        return newParent;
    }
}
