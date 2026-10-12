package net.robinfriedli.jxp.events;

import java.util.List;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.persist.Context;

public abstract class ElementChangingEvent extends Event {

    public ElementChangingEvent(Context context, XmlElement source) {
        super(context, source);
    }

    @Nullable
    public AttributeChangingEvent getAttributeChange() {
        return unwrap(AttributeChangingEvent.class);
    }

    @Nullable
    public AttributeDeletedEvent getAttributeDeletion() {
        return unwrap(AttributeDeletedEvent.class);
    }

    @Nullable
    public AttributeCreatedEvent getAddedAttribute() {
        return unwrap(AttributeCreatedEvent.class);
    }

    @Nullable
    public TextNodeChangingEvent getChangedTextContent() {
        return unwrap(TextNodeChangingEvent.class);
    }

    @Nullable
    public TextNodeCreatedEvent getAddedTextNode() {
        return unwrap(TextNodeCreatedEvent.class);
    }

    @Nullable
    public TextNodeDeletingEvent getDeletedTextNode() {
        return unwrap(TextNodeDeletingEvent.class);
    }

    @Nullable
    public <E extends ElementChangingEvent> E unwrap(Class<E> type) {
        if (type.isInstance(this)) {
            return type.cast(this);
        }

        return null;
    }

    @Override
    public void doApply() {
        getSource().internal().applyChange(this);
    }

    @Nullable
    @Deprecated
    public List<AttributeChangingEvent> getChangedAttributes() {
        return null;
    }

    @Override
    public void doRevert() {
        getSource().internal().revertChange(this);
        if (!isCommitted()) {
            getSource().internal().removeChange(this);
        }
    }

    protected abstract void handleCommit();

    @Override
    public void doCommit() {
        handleCommit();
        getSource().internal().removeChange(this);
    }

    @Override
    protected void dispatchEvent(JxpBackend backend) {
        backend.fireElementChanging(this);
    }

    @Deprecated
    public boolean isEmpty() {
        return false;
    }

    public boolean shouldTreatAsPhysicalIfTransitioning() {
        return false;
    }

    public boolean attributeChanged(String attributeName) {
        AttributeChangingEvent attributeChange = getAttributeChange();
        if (attributeChange != null) {
            return attributeChange.getAttribute().getAttributeName().equals(attributeName);
        }

        return false;
    }

    public AttributeChangingEvent getAttributeChange(String attributeName) {
        AttributeChangingEvent attributeChange = getAttributeChange();
        if (attributeChange != null && attributeChange.getAttribute().getAttributeName().equals(attributeName)) {
            return attributeChange;
        }

        return null;
    }

    public boolean textContentChanged() {
        return getChangedTextContent() != null;
    }

}
