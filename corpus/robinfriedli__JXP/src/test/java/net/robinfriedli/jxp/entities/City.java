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

public class City extends AbstractXmlElement {

    @SuppressWarnings("unused")
    public City(Element element, NodeList subElements, Context context) {
        super(element, subElements, context);
    }

    public City(String tagName, List<Node<?>> childNodes, Map<String, ?> attributeMap) {
        super(tagName, childNodes, attributeMap);
    }

    public City(String name, int population) {
        super("city", buildAttributes(name, population));
    }

    private static Map<String, ?> buildAttributes(String name, int population) {
        Map<String, Object> attributes = new HashMap<>();
        attributes.put("name", name);
        attributes.put("population", population);
        return attributes;
    }

    @Nullable
    @Override
    public String getId() {
        return getAttribute("name").getValue();
    }
}
