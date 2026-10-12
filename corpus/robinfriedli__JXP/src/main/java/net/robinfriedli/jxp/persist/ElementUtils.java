package net.robinfriedli.jxp.persist;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.common.collect.Lists;
import net.robinfriedli.jxp.exceptions.PersistException;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.w3c.dom.Text;

public class ElementUtils {

    public static boolean hasTextContent(Element element) {
        Node childNode = element.getChildNodes().item(0);
        return childNode != null && childNode.getNodeType() == Node.TEXT_NODE && !childNode.getTextContent().trim().equals("");
    }

    public static String getTextContent(Element element) {
        if (hasTextContent(element)) {
            Node childNode = element.getChildNodes().item(0);
            return childNode.getTextContent();
        } else {
            return "";
        }
    }

    public static Map<String, String> getAttributes(Element element) {
        NamedNodeMap attributes = element.getAttributes();
        Map<String, String> attributeMap = new HashMap<>();
        for (int i = 0; i < attributes.getLength(); i++) {
            Node attribute = attributes.item(i);
            attributeMap.put(attribute.getNodeName(), attribute.getNodeValue());
        }

        return attributeMap;
    }

    // gets called for the old Element when an XmlElement gets bound to a new Element (typically subelements)
    public static void destroy(Node element) {
        // might be called when a child element gets added to a different parent, thus setting a new Element on an existing
        // XmlElement instance (via XmlElement#setElement), in this case the element may have already been
        // detached from its old parent if XmlElement#removeSubElement was called before adding it to the new parent
        Node parentNode = element.getParentNode();
        if (parentNode != null) {
            parentNode.removeChild(element);
        } else {
            throw new PersistException("Cannot destroy node that does not have a parent. Either the node is the document root or it isn't part of the tree.");
        }
    }

    public static List<Element> nodeListToElementList(NodeList nodeList) {
        List<Element> elements = Lists.newArrayList();
        for (int i = 0; i < nodeList.getLength(); i++) {
            elements.add((Element) nodeList.item(i));
        }

        return elements;
    }

    public static List<Element> getChildren(Element parent) {
        NodeList childNodes = parent.getChildNodes();
        List<Element> elements = Lists.newArrayList();

        for (int i = 0; i < childNodes.getLength(); i++) {
            Node node = childNodes.item(i);
            if (node instanceof Element) {
                elements.add((Element) node);
            }
        }

        return elements;
    }

    public static List<Node> getChildNodes(Element parent) {
        NodeList childNodes = parent.getChildNodes();
        List<Node> elements = Lists.newArrayList();

        for (int i = 0; i < childNodes.getLength(); i++) {
            Node node = childNodes.item(i);
            if (node instanceof Element || node instanceof Text) {
                elements.add(node);
            }
        }

        return elements;
    }

}
