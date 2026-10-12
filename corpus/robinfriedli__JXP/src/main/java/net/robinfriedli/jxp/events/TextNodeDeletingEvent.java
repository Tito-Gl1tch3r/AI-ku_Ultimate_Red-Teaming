package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.api.TextNode;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.ElementUtils;
import org.w3c.dom.Text;

public class TextNodeDeletingEvent extends ElementChangingEvent {

    private final TextNode textNode;

    private XmlElement oldParent;
    private Node<?> oldPreviousSibling;
    private Text oldElem;
    private org.w3c.dom.Node previousNeighbor;
    private org.w3c.dom.Node oldParentNode;

    public TextNodeDeletingEvent(Context context, XmlElement source, TextNode textNode) {
        super(context, source);
        this.textNode = textNode;
    }

    @Override
    protected void handleCommit() {
        oldParentNode = oldElem.getParentNode();
        ElementUtils.destroy(oldElem);
    }

    @Override
    protected void revertCommit() {
        if (oldElem == null) {
            throw new IllegalStateException("Old element not known. Deletion was never physically applied");
        }

        textNode.internal().addToDOM(oldElem, oldParentNode, previousNeighbor, false);
    }

    @Override
    public void doApply() {
        oldParent = textNode.getParent();
        oldPreviousSibling = textNode.getPreviousSibling();
        super.doApply();
    }

    @Override
    protected void applyPhysical() {
        oldElem = textNode.getElement();
        if (oldElem == null) {
            throw new PersistException(String.format("Cannot delete non-persistent element. %s has either never been persisted or has already been deleted.", textNode));
        }
        previousNeighbor = oldElem.getNextSibling();
        textNode.internal().removeElement();
    }

    @Override
    public void doRevert() {
        textNode.internal().setElement(oldElem);
        super.doRevert();
    }

    @Override
    public boolean shouldTreatAsPhysicalIfTransitioning() {
        return true;
    }

    public TextNode getTextNode() {
        return textNode;
    }

    public XmlElement getOldParent() {
        return oldParent;
    }

    public Node<?> getOldPreviousSibling() {
        return oldPreviousSibling;
    }
}
