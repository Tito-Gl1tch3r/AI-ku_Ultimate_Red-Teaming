package net.robinfriedli.jxp.entities;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.AbstractXmlElement;
import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.collections.NodeList;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Element;

public class Continent extends AbstractXmlElement {

    public Continent(String name) {
        super("continent", getAttributeMap(name));
    }

    @SuppressWarnings("unused")
    public Continent(Element element, NodeList subElements, Context context) {
        super(element, subElements, context);
    }

    public Continent(String tagName, List<Node<?>> childNodes, Map<String, ?> attributeMap) {
        super(tagName, childNodes, attributeMap);
    }

    private static Map<String, ?> getAttributeMap(String name) {
        Map<String, Object> attributeMap = new HashMap<>();
        attributeMap.put("name", name);

        return attributeMap;
    }

    @Nullable
    @Override
    public String getId() {
        return getAttribute("name").getValue();
    }

}
