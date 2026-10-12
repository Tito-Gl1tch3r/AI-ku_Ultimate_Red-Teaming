package net.robinfriedli.jxp.events;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.ElementUtils;
import org.w3c.dom.Element;

public class ElementDeletingEvent extends Event {

    private final XmlElement.State oldState;

    private XmlElement oldParent;
    private Node<?> oldPreviousSibling;
    private Node<?> oldNextSibling;
    private Element oldElem;
    private org.w3c.dom.Node previousNeighbor;
    private org.w3c.dom.Node oldParentNode;

    public ElementDeletingEvent(Context context, XmlElement element, XmlElement.State oldState) {
        super(context, element);
        this.oldState = oldState;
        element.internal().setState(XmlElement.State.DELETION);
    }

    public Node<?> getOldPreviousSibling() {
        return oldPreviousSibling;
    }

    public Node<?> getOldNextSibling() {
        return oldNextSibling;
    }

    @Override
    public void doApply() {
        XmlElement source = getSource();

        oldParent = source.getParent();
        oldPreviousSibling = source.getPreviousSibling();
        oldNextSibling = source.getNextSibling();
        if (oldParent != null) {
            oldParent.internal().removeChild(source);
            source.internal().removeParent();
        } else {
            throw new UnsupportedOperationException("Cannot delete root document element");
        }
    }

    @Override
    protected void applyPhysical() {
        XmlElement source = getSource();
        oldElem = source.getElement();
        if (oldElem == null) {
            throw new PersistException(String.format("Cannot delete non-persistent element. %s has either never been persisted or has already been deleted. Previous state: %s", source.toString(), oldState));
        }
        previousNeighbor = oldElem.getNextSibling();
        source.internal().removeElement();
    }

    @Override
    public void doRevert() {
        XmlElement source = getSource();
        source.internal().setElement(oldElem);

        if (oldParent == null) {
            throw new IllegalStateException("Old parent of " + source.toString() + " null while reverting deletion");
        } else {
            oldParent.internal().adoptChild(source, oldPreviousSibling, true);
            source.internal().setParent(oldParent);
        }

        source.internal().setState(oldState);
    }

    @Override
    protected void revertCommit() {
        if (oldElem == null) {
            throw new IllegalStateException("Old element not known. Deletion was never physically applied");
        }
        if (oldParent == null) {
            throw new IllegalStateException("Old parent of " + getSource().toString() + " was null while reverting commit of deletion");
        }
        if (oldParentNode == null) {
            throw new IllegalStateException("Old parent node of " + getSource().toString() + " was null while reverting commit of deletion");
        }

        getSource().internal().addToDOM(oldElem, oldParentNode, previousNeighbor, false);
    }

    @Override
    public void doCommit() {
        oldParentNode = oldElem.getParentNode();
        ElementUtils.destroy(oldElem);
        getSource().internal().setState(XmlElement.State.PHANTOM);
    }

    @Override
    protected void dispatchEvent(JxpBackend backend) {
        backend.fireElementDeleting(this);
    }

    @Nullable
    public XmlElement getOldParent() {
        return oldParent;
    }

}
