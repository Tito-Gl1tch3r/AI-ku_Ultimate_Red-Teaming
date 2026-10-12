package net.robinfriedli.jxp.api;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.events.TextNodeChangingEvent;
import net.robinfriedli.jxp.events.TextNodeCreatedEvent;
import net.robinfriedli.jxp.events.TextNodeDeletingEvent;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Text;

/**
 * JXP representation for DOM {@link Text} instances.
 */
public class TextNode implements Node<Text> {

    private final InternalControl internalControl = new InternalControl();

    private Context context;
    private String textContent;
    private Text node;
    private XmlElement parent;
    private Node<?> previousSibling;
    private Node<?> nextSibling;

    public TextNode(String textContent) {
        this.textContent = textContent;
    }

    // initialize persistent TextNode
    public TextNode(Context context, Text node) {
        this.context = context;
        this.textContent = node.getTextContent();
        this.node = node;
    }

    @Override
    public void persist(Context context) {
        persist(context, context.getDocumentElement());
    }

    @Override
    public void persist(Context context, XmlElement newParent) {
        persist(context, newParent, null, true);
    }

    @Override
    public void persist(Context context, XmlElement newParent, @Nullable Node<?> refNode, boolean insertAfter) {
        this.context = context;

        if (parent == null && newParent == null) {
            throw new PersistException("TextNodes need a parent");
        }

        XmlElement source = parent != null ? parent : newParent;
        source.internal().addChange(new TextNodeCreatedEvent(context, source, newParent != null, this, refNode, insertAfter));
    }

    @Override
    public void delete() {
        if (isDetached()) {
            throw new PersistException("Cannot delete detached TextNode. This TextNode has never been persisted in the first place.");
        }

        if (parent != null) {
            parent.internal().addChange(new TextNodeDeletingEvent(context, parent, this));
        } else {
            throw new PersistException("TextNode does not have a parent, has probably never been persisted.");
        }
    }

    @Override
    public boolean isPersisted() {
        return node != null;
    }

    @Override
    public boolean isDetached() {
        return context == null;
    }

    @Nullable
    @Override
    public Context getContext() {
        return context;
    }

    @Override
    public TextNode copy(boolean deep, boolean instantiateContributedClass) {
        return new TextNode(textContent);
    }

    @Nullable
    @Override
    public Text getElement() {
        return node;
    }

    @Nullable
    @Override
    public Node<?> getPreviousSibling() {
        return previousSibling;
    }

    @Nullable
    @Override
    public Node<?> getNextSibling() {
        return nextSibling;
    }

    @Override
    public Internals<Text> internal() {
        return internalControl;
    }

    @Override
    public XmlElement getParent() {
        return parent;
    }

    public String getTextContent() {
        return textContent;
    }

    public void setTextContent(String textContent) {
        parent.internal().addChange(new TextNodeChangingEvent(parent.getContext(), parent, this, this.textContent, textContent));
    }

    public Text getNode() {
        return node;
    }

    public void setNode(Text node) {
        this.node = node;
    }

    public void applyChange(TextNodeChangingEvent event, boolean isRollback) {
        if (isRollback) {
            textContent = event.getOldValue();
        } else {
            textContent = event.getNewValue();
        }
    }

    private class InternalControl implements Internals<Text> {

        @Override
        public void setElement(Text element) {
            if (node != null && element != node) {
                throw new IllegalStateException(TextNode.this + " is already persisted as an element. Destroy the old element first.");
            }

            node = element;
        }

        @Override
        public void removeElement() {
            node = null;
        }

        @Override
        public void removeParent() {
            parent = null;
        }

        @Override
        public void setParent(XmlElement parent) {
            if (TextNode.this.parent != null && TextNode.this.parent != parent) {
                throw new IllegalStateException(TextNode.this.toString() + " already has a parent. Remove it from the old parent first.");
            }
            TextNode.this.parent = parent;
        }

        @Override
        public void setPreviousSibling(Node<?> node) {
            if (previousSibling != null && previousSibling != node) {
                throw new IllegalStateException(TextNode.this.toString() + " already has a previous sibling. Delete the element from its old location before inserting it to a different one.");
            }

            previousSibling = node;
        }

        @Override
        public void removePreviousSibling() {
            previousSibling = null;
        }

        @Override
        public void setNextSibling(Node<?> node) {
            if (nextSibling != null && nextSibling != node) {
                throw new IllegalStateException(TextNode.this.toString() + " already has a next sibling. Delete the element from its old location before inserting it to a different one.");
            }

            nextSibling = node;
        }

        @Override
        public void removeNextSibling() {
            nextSibling = null;
        }
    }

}
