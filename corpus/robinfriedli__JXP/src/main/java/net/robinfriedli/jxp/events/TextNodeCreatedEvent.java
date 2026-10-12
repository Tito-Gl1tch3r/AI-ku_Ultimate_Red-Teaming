package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.api.TextNode;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.ElementUtils;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Text;

public class TextNodeCreatedEvent extends ElementChangingEvent {

    private final boolean insertAfter;
    private final boolean insertToParent;
    private final Node<?> refNode;
    private final TextNode textNode;

    private Text createdElem;
    private Element parentElem;

    public TextNodeCreatedEvent(Context context, XmlElement source, boolean insertToParent, TextNode textNode, Node<?> refNode, boolean insertAfter) {
        super(context, source);
        this.insertAfter = insertAfter;
        this.insertToParent = insertToParent;
        this.refNode = refNode;
        this.textNode = textNode;
    }

    @Override
    protected void handleCommit() {
        if (createdElem == null) {
            throw new IllegalStateException("Element was never created. Event was never physically applied.");
        }

        textNode.internal().addToDOM(createdElem, parentElem, refNode, insertAfter);
    }

    @Override
    public void doApply() {
        if (insertToParent) {
            textNode.internal().setParent(getSource());
            // this adds the change to the source XmlElement, adding the text node to the child nodes
            super.doApply();
        }
    }

    @Override
    protected void applyPhysical() {
        Document document = getContext().getDocument();

        createdElem = document.createTextNode(textNode.getTextContent());
        textNode.internal().setElement(createdElem);

        parentElem = getSource().getElement();
    }

    @Override
    public void doRevert() {
        textNode.internal().removeElement();
        super.doRevert();
    }

    @Override
    protected void revertCommit() {
        ElementUtils.destroy(createdElem);
    }

    @Override
    public boolean shouldTreatAsPhysicalIfTransitioning() {
        return true;
    }

    public TextNode getTextNode() {
        return textNode;
    }

    public Node<?> getRefNode() {
        return refNode;
    }

    public boolean isInsertAfter() {
        return insertAfter;
    }
}
