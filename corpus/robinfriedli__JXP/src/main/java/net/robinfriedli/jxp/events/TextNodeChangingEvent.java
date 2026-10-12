package net.robinfriedli.jxp.events;

import net.robinfriedli.jxp.api.TextNode;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Text;

public class TextNodeChangingEvent extends ElementChangingEvent {

    private final TextNode textNode;

    private final String oldValue;
    private final String newValue;

    private Text physicalElem;

    public TextNodeChangingEvent(Context context, XmlElement source, TextNode textNode, String oldValue, String newValue) {
        super(context, source);
        this.textNode = textNode;
        this.oldValue = oldValue;
        this.newValue = newValue;
    }

    public TextNode getTextNode() {
        return textNode;
    }

    @Override
    public void doApply() {
        physicalElem = textNode.requireElement();
        super.doApply();
    }

    @Override
    public void handleCommit() {
        setTextValue(newValue);
    }

    public String getOldValue() {
        return oldValue;
    }

    public String getNewValue() {
        return newValue;
    }

    @Override
    protected void revertCommit() {
        setTextValue(oldValue);
    }

    private void setTextValue(String value) {
        physicalElem.setTextContent(value);
    }

}
