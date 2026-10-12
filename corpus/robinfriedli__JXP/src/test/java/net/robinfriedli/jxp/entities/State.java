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

public class State extends AbstractXmlElement {

    @SuppressWarnings("unused")
    public State(Element element, NodeList subElements, Context context) {
        super(element, subElements, context);
    }

    public State(String name, int population, List<City> cities) {
        super("state", buildAttributeMap(name, population), cities);
    }

    public State(String tagName, List<Node<?>> childNodes, Map<String, ?> attributeMap) {
        super(tagName, childNodes, attributeMap);
    }

    private static Map<String, ?> buildAttributeMap(String name, int population) {
        Map<String, Object> map = new HashMap<>();
        map.put("name", name);
        map.put("population", population);
        return map;
    }

    @Nullable
    @Override
    public String getId() {
        return getAttribute("name").getValue();
    }

}
