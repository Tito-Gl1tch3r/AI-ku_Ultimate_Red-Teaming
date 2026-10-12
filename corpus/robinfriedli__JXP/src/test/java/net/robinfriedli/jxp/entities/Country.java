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

public class Country extends AbstractXmlElement {

    // invoked by JXP
    @SuppressWarnings("unused")
    public Country(Element element, NodeList subElements, Context context) {
        super(element, subElements, context);
    }

    public Country() {
        super("country");
    }

    public Country(String name, String englishName, boolean sovereign) {
        super("country", buildAttributes(name, englishName, sovereign));
    }

    public Country(String name, String englishName, boolean sovereign, List<City> cities) {
        super("country", buildAttributes(name, englishName, sovereign), cities);
    }

    public Country(String tagName, List<Node<?>> childNodes, Map<String, ?> attributeMap) {
        super(tagName, childNodes, attributeMap);
    }

    private static Map<String, ?> buildAttributes(String name, String englishName, boolean sovereign) {
        Map<String, Object> attributes = new HashMap<>();
        attributes.put("name", name);
        attributes.put("englishName", englishName);
        attributes.put("sovereign", sovereign);
        return attributes;
    }

    @Nullable
    @Override
    public String getId() {
        return getAttribute("englishName").getValue();
    }
}
