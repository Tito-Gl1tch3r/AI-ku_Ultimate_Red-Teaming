package net.robinfriedli.jxp.api;

import net.robinfriedli.jxp.events.AttributeChangingEvent;
import net.robinfriedli.jxp.events.AttributeCreatedEvent;
import net.robinfriedli.jxp.events.AttributeDeletedEvent;

public class XmlAttribute {

    private final XmlElement parentElement;
    private final String attributeName;
    private String value;

    public XmlAttribute(XmlElement parentElement, String attributeName) {
        this.parentElement = parentElement;
        this.attributeName = attributeName;
        this.value = "";
    }

    public XmlAttribute(XmlElement parentElement, String attributeName, Object value) {
        this.parentElement = parentElement;
        this.attributeName = attributeName;
        this.value = value instanceof String ? (String) value : StringConverter.reverse(value);
    }

    public XmlElement getParentElement() {
        return this.parentElement;
    }

    public String getAttributeName() {
        return this.attributeName;
    }

    public String getValue() {
        return value;
    }

    public void setValue(Object value) {
        String stringValue = value instanceof String ? (String) value : StringConverter.reverse(value);
        parentElement.internal().addChange(new AttributeChangingEvent(parentElement.getContext(), this, stringValue));
    }

    public void remove() {
        parentElement.internal().addChange(new AttributeDeletedEvent(parentElement.getContext(), parentElement, this));
    }

    public <V> V getValue(Class<V> target) {
        return StringConverter.convert(value, target);
    }

    public int getInt() {
        return getValue(Integer.class);
    }

    public boolean getBool() {
        return getValue(Boolean.class);
    }

    public float getFloat() {
        return getValue(Float.class);
    }

    public long getLong() {
        return getValue(Long.class);
    }

    public void applyChange(AttributeChangingEvent change) throws UnsupportedOperationException {
        applyChange(change, false);
    }

    public void revertChange(AttributeChangingEvent change) {
        applyChange(change, true);
    }

    @Override
    public String toString() {
        return "XmlAttribute:" + getAttributeName() + "@" + getParentElement().getTagName();
    }

    private void applyChange(AttributeChangingEvent change, boolean isRollback) {
        if (change.getAttribute() != this) {
            throw new UnsupportedOperationException("Change can't be applied to this XmlAttribute since the change does not refer to this attribute");
        }

        if (isRollback) {
            value = change.getOldValue();
            if (change.isCommitted() && parentElement.isPersisted()) {
                parentElement.requireElement().setAttribute(attributeName, change.getOldValue());
            }
        } else {
            value = change.getNewValue();
        }
    }

    /**
     * Used when {@link XmlElement#getAttribute(String)} is called for an attribute that does not exist on this element.
     * This is a temporary XmlAttribute that is only added to the XmlElement instance once it is written to.
     * This enables calling any of the #getValue methods on an attribute that does not exist on this element without
     * an exception being thrown.
     */
    public static class Provisional extends XmlAttribute {

        // the definitive attribute that was added to the XmlElement instance, should this attribute be written to
        private XmlAttribute definitiveAttribute;

        public Provisional(XmlElement parentElement, String attributeName) {
            super(parentElement, attributeName);
        }

        @Override
        public String getValue() {
            recheck();
            if (definitiveAttribute == null) {
                return "";
            } else {
                return definitiveAttribute.getValue();
            }
        }

        @Override
        public void setValue(Object value) {
            recheck();
            if (definitiveAttribute == null) {
                XmlElement parentElement = getParentElement();
                definitiveAttribute = new XmlAttribute(parentElement, getAttributeName(), value);
                if (parentElement.isDetached()) {
                    parentElement.internal().getInternalAttributeMap().put(getAttributeName(), definitiveAttribute);
                } else {
                    parentElement.internal().addChange(new AttributeCreatedEvent(parentElement.getContext(), definitiveAttribute));
                }
            } else {
                definitiveAttribute.setValue(value);
            }
        }

        @Override
        public void remove() {
            recheck();
            if (definitiveAttribute == null) {
                throw new IllegalArgumentException(String.format("No such attribute '%s' on '%s'", getAttributeName(), getParentElement()));
            }

            definitiveAttribute.remove();
        }

        @Override
        public <V> V getValue(Class<V> target) {
            recheck();
            if (definitiveAttribute == null) {
                return StringConverter.getEmptyValue(target);
            }
            return definitiveAttribute.getValue(target);
        }

        @Override
        public void applyChange(AttributeChangingEvent change) throws UnsupportedOperationException {
            throw new UnsupportedOperationException();
        }

        @Override
        public void revertChange(AttributeChangingEvent change) {
            throw new UnsupportedOperationException();
        }

        /**
         * Check again if the attribute exists now
         */
        private void recheck() {
            if (definitiveAttribute == null) {
                definitiveAttribute = getParentElement().internal().getInternalAttributeMap().get(getAttributeName());
            }
        }
    }

}
