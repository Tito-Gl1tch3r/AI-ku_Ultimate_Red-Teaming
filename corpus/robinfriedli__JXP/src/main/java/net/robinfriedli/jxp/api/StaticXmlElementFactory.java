package net.robinfriedli.jxp.api;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

import javax.annotation.Nullable;

import com.google.common.collect.Lists;
import net.robinfriedli.jxp.collections.NodeList;
import net.robinfriedli.jxp.collections.UninitializedNodeList;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.ElementUtils;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.Text;

public class StaticXmlElementFactory {

    public static final Map<String, Class<? extends XmlElement>> INSTANTIATION_CONTRIBUTIONS = new HashMap<>();

    public static void mapClass(String tagName, Class<? extends XmlElement> type) {
        INSTANTIATION_CONTRIBUTIONS.put(tagName, type);
    }

    public static XmlElement instantiate(String tagName, List<net.robinfriedli.jxp.api.Node<?>> childNodes, Map<String, ?> attributeMap) {
        Class<? extends XmlElement> classToInstantiate = INSTANTIATION_CONTRIBUTIONS.get(tagName);

        if (classToInstantiate != null) {
            try {
                Constructor<? extends XmlElement> constructor =
                    classToInstantiate.getConstructor(String.class, List.class, Map.class);
                return constructor.newInstance(tagName, childNodes, attributeMap);
            } catch (NoSuchMethodException e) {
                // do nothing, just return a BaseXmlElement instead
            } catch (InstantiationException | IllegalAccessException | InvocationTargetException e) {
                throw new PersistException("Could not instantiate " + classToInstantiate + ". Failed invoking constructor.", e);
            }
        }

        return new BaseXmlElement(tagName, childNodes, attributeMap);
    }

    public static XmlElement instantiateDocumentElement(Context context) {
        return instantiatePersistentXmlElement(context.getDocument().getDocumentElement(), context, true, null);
    }

    public static XmlElement instantiateDocumentElement(Context context, @Nullable Set<? extends net.robinfriedli.jxp.api.Node<?>> preInstantiated) {
        return instantiatePersistentXmlElement(context.getDocument().getDocumentElement(), context, true, preInstantiated);
    }

    public static XmlElement instantiateDocumentElement(Context context, boolean initializeSubElements) {
        return instantiatePersistentXmlElement(context.getDocument().getDocumentElement(), context, initializeSubElements, null);
    }

    public static XmlElement instantiateDocumentElement(Context context, boolean initializeSubElements, @Nullable Set<? extends net.robinfriedli.jxp.api.Node<?>> preInstantiated) {
        return instantiatePersistentXmlElement(context.getDocument().getDocumentElement(), context, initializeSubElements, preInstantiated);
    }

    public static NodeList instantiateChildrenOf(Element element, Context context) {
        return instantiateChildrenOf(element, context, true);
    }

    public static NodeList instantiateChildrenOf(Element element, Context context, boolean initializeSubElements) {
        return instantiateChildrenOf(element, context, initializeSubElements, null);
    }

    public static NodeList instantiateChildrenOf(Element element, Context context, boolean initializeSubElements, @Nullable Set<? extends net.robinfriedli.jxp.api.Node<?>> preInstantiated) {
        List<Node> childNodes = ElementUtils.getChildNodes(element);
        List<net.robinfriedli.jxp.api.Node<?>> instantiatedChildNodes = Lists.newArrayList();

        net.robinfriedli.jxp.api.Node<?> prev = null;
        for (Node node : childNodes) {
            net.robinfriedli.jxp.api.Node<?> subElement;
            if (node instanceof Element) {
                subElement = instantiatePersistentXmlElement((Element) node, context, initializeSubElements, preInstantiated);
            } else if (node instanceof Text) {
                Optional<TextNode> preInit;
                if (preInstantiated != null) {
                    preInit = preInstantiated.stream()
                        .filter(e -> e instanceof TextNode)
                        .filter(e -> Objects.equals(node, e.getElement()))
                        .map(TextNode.class::cast)
                        .findFirst();
                } else {
                    preInit = Optional.empty();
                }

                subElement = preInit.orElseGet(() -> new TextNode(context, (Text) node));
            } else {
                subElement = null;
            }

            if (subElement != null) {
                subElement.internal().setPreviousSibling(prev);
                if (prev != null) {
                    prev.internal().setNextSibling(subElement);
                }
                prev = subElement;
                instantiatedChildNodes.add(subElement);
            }
        }

        return NodeList.ofLinked(instantiatedChildNodes);
    }

    public static XmlElement instantiatePersistentXmlElement(Element element, Context context) {
        return instantiatePersistentXmlElement(element, context, null);
    }

    public static XmlElement instantiatePersistentXmlElement(Element element, Context context, boolean initializeSubElements) {
        return instantiatePersistentXmlElement(element, context, initializeSubElements, null);
    }

    public static XmlElement instantiatePersistentXmlElement(Element element, Context context, @Nullable Set<? extends net.robinfriedli.jxp.api.Node<?>> preInstantiated) {
        return instantiatePersistentXmlElement(element, context, true, preInstantiated);
    }

    private static XmlElement instantiatePersistentXmlElement(Element element, Context context, boolean initializeSubElements, @Nullable Set<? extends net.robinfriedli.jxp.api.Node<?>> preInstantiated) {
        if (preInstantiated != null && preInstantiated.size() > 0) {
            Optional<XmlElement> preInit = preInstantiated.stream()
                .filter(e -> e instanceof XmlElement)
                .filter(e -> element.equals(e.getElement()))
                .map(XmlElement.class::cast)
                .findFirst();
            if (preInit.isPresent()) {
                return preInit.get();
            }
        }

        NodeList childNodeList;
        if (initializeSubElements) {
            childNodeList = instantiateChildrenOf(element, context, true, preInstantiated);
        } else {
            childNodeList = new UninitializedNodeList(context, element);
        }

        Class<? extends XmlElement> xmlClass = INSTANTIATION_CONTRIBUTIONS.get(element.getTagName());
        if (xmlClass != null) {
            try {
                Constructor<? extends XmlElement> constructor = xmlClass.getConstructor(Element.class, NodeList.class, Context.class);
                return constructor.newInstance(element, childNodeList, context);
            } catch (NoSuchMethodException e) {
                throw new PersistException("Your class " + xmlClass + " does not have the appropriate Constructor", e);
            } catch (IllegalAccessException e) {
                throw new PersistException("Cannot access constructor of class " + xmlClass, e);
            } catch (InstantiationException e) {
                throw new PersistException("Cannot instantiate class " + xmlClass, e);
            } catch (InvocationTargetException e) {
                throw new PersistException("Exception while invoking constructor of " + xmlClass, e);
            }
        } else {
            return new BaseXmlElement(element, childNodeList, context);
        }
    }

}
