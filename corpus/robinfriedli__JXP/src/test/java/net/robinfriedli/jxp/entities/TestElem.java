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

public class TestElem extends AbstractXmlElement {

    public TestElem(String atr1, String atr2) {
        super("test", buildAttributeMap(atr1, atr2));
    }

    public TestElem(Element element, NodeList subElements, Context context) {
        super(element, subElements, context);
    }

    public TestElem(String tagName, List<Node<?>> childNodes, Map<String, ?> attributeMap) {
        super(tagName, childNodes, attributeMap);
    }

    private static Map<String, String> buildAttributeMap(String testAtr1, String testAtr2) {
        Map<String, String> attributeMap = new HashMap<>();
        attributeMap.put("testAtr1", testAtr1);
        attributeMap.put("testAtr2", testAtr2);
        return attributeMap;
    }

    @Nullable
    @Override
    public String getId() {
        return getAttribute("testAtr1").getValue();
    }
}
