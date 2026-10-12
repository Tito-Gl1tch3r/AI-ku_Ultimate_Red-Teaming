package net.robinfriedli.jxp.api;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Predicate;
import java.util.stream.Collectors;

import javax.annotation.Nullable;

import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import net.robinfriedli.jxp.collections.NodeList;
import net.robinfriedli.jxp.collections.UninitializedNodeList;
import net.robinfriedli.jxp.events.AttributeChangingEvent;
import net.robinfriedli.jxp.events.AttributeCreatedEvent;
import net.robinfriedli.jxp.events.AttributeDeletedEvent;
import net.robinfriedli.jxp.events.ElementChangingEvent;
import net.robinfriedli.jxp.events.ElementCreatedEvent;
import net.robinfriedli.jxp.events.ElementDeletingEvent;
import net.robinfriedli.jxp.events.Event;
import net.robinfriedli.jxp.events.TextNodeChangingEvent;
import net.robinfriedli.jxp.events.TextNodeCreatedEvent;
import net.robinfriedli.jxp.events.TextNodeDeletingEvent;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.ElementUtils;
import net.robinfriedli.jxp.persist.Transaction;
import net.robinfriedli.jxp.queries.Query;
import net.robinfriedli.jxp.queries.ResultStream;
import org.w3c.dom.Element;
import org.w3c.dom.Text;

/**
 * Abstract class to extend for classes you wish to able to persist to an XML file.
 * Classes that extend this class can be persisted via the {@link net.robinfriedli.jxp.persist.Context#invoke(Runnable)}
 * method using {@link #persist(Context)}
 */
public abstract class AbstractXmlElement implements XmlElement {

    private final InternalControl internalControl = new InternalControl();

    private final String tagName;
    private final Map<String, XmlAttribute> attributes;
    private final NodeList childNodes;
    private final List<ElementChangingEvent> changes = Lists.newArrayList();

    private Context context;
    private Element element;
    private State state;

    private XmlElement parent;
    private Node<?> previousSibling;
    private Node<?> nextSibling;

    private boolean locked = false;

    // creating new element

    public AbstractXmlElement(String tagName) {
        this(tagName, null, null, "");
    }

    public AbstractXmlElement(String tagName, Map<String, ?> attributeMap) {
        this(tagName, attributeMap, null, "");
    }

    public AbstractXmlElement(String tagName, List<? extends XmlElement> subElements) {
        this(tagName, null, subElements, "");
    }

    public AbstractXmlElement(String tagName, String textContent) {
        this(tagName, null, null, textContent);
    }

    public AbstractXmlElement(String tagName, Map<String, ?> attributeMap, List<? extends XmlElement> subElements) {
        this(tagName, attributeMap, subElements, "");
    }

    public AbstractXmlElement(String tagName, Map<String, ?> attributeMap, String textContent) {
        this(tagName, attributeMap, null, textContent);
    }

    public AbstractXmlElement(String tagName, List<? extends XmlElement> subElements, String textContent) {
        this(tagName, null, subElements, textContent);
    }

    /**
     * Full constructor used for creating new XmlElement instances in state {@link State#CONCEPTION}.
     *
     * @param tagName      the XML tag name for this element type
     * @param attributeMap the map containing attribute names + their current value.
     * @param subElements  list containing all sub elements
     * @param textContent  text context string; will create single {@link TextNode} that will be inserted as first child
     *                     of this element
     */
    public AbstractXmlElement(String tagName,
                              Map<String, ?> attributeMap,
                              List<? extends XmlElement> subElements,
                              String textContent) {
        this.tagName = tagName;
        this.state = State.CONCEPTION;

        Map<String, XmlAttribute> attributes = new HashMap<>();
        if (attributeMap != null) {
            for (String attributeName : attributeMap.keySet()) {
                attributes.put(attributeName, new XmlAttribute(this, attributeName, attributeMap.get(attributeName)));
            }
        }
        this.attributes = attributes;

        List<Node<?>> childNodes = Lists.newArrayList();
        TextNode textNode = null;
        if (!Strings.isNullOrEmpty(textContent)) {
            textNode = new TextNode(textContent);
            Node.Internals<Text> internal = textNode.internal();
            internal.setParent(this);
            childNodes.add(textNode);
        }
        if (subElements != null && !subElements.isEmpty()) {
            initParentAndSiblingLinkages(textNode, subElements);
            childNodes.addAll(subElements);
        }
        this.childNodes = NodeList.ofLinked(childNodes);
    }

    /**
     * Full constructor used for creating new XmlElement instances in state {@link State#CONCEPTION}. This constructor
     * is required for copying (see {@link XmlElement#copy(boolean, boolean)}).
     *
     * @param tagName      the XML tag name for this element type
     * @param childNodes   the child nodes, including sub elements and text nodes
     * @param attributeMap the map containing attribute names + their current value.
     */
    public AbstractXmlElement(String tagName,
                              List<Node<?>> childNodes,
                              Map<String, ?> attributeMap) {
        this.tagName = tagName;
        this.state = State.CONCEPTION;

        Map<String, XmlAttribute> attributes = new HashMap<>();
        if (attributeMap != null) {
            for (String attributeName : attributeMap.keySet()) {
                attributes.put(attributeName, new XmlAttribute(this, attributeName, attributeMap.get(attributeName)));
            }
        }
        this.attributes = attributes;

        initParentAndSiblingLinkages(null, childNodes);
        this.childNodes = NodeList.ofLinked(childNodes);
    }


    /**
     * Constructor used for initializing persistent XmlElements in state {@link State#CLEAN}. This constructor is required
     * for registered Classes when initializing a Context.
     *
     * @param element    the persistent {@link Element} in the Document
     * @param childNodes linked NodeList containing all child nodes, including sub elements and text nodes
     * @param context    the initializing Context managing the current Document
     */
    public AbstractXmlElement(Element element, NodeList childNodes, Context context) {
        this.element = element;
        this.tagName = element.getTagName();
        this.childNodes = childNodes;
        this.context = context;
        this.state = State.CLEAN;

        Map<String, XmlAttribute> attributes = new HashMap<>();
        Map<String, String> attributeMap = ElementUtils.getAttributes(element);
        for (String attributeName : attributeMap.keySet()) {
            attributes.put(attributeName, new XmlAttribute(this, attributeName, attributeMap.get(attributeName)));
        }
        this.attributes = attributes;

        if (childNodes instanceof UninitializedNodeList) {
            ((UninitializedNodeList) childNodes).setParent(this);
        } else {
            childNodes.forEach(node -> node.internal().setParent(this));
        }
    }

    @Override
    @Nullable
    public abstract String getId();

    @Override
    public void persist(Context context) {
        persist(context, context.getDocumentElement());
    }

    @Override
    public void persist(Context context, XmlElement newParent) {
        persist(context, newParent, null, true);
    }

    @Override
    public void persist(Context context, XmlElement newParent, @Nullable Node<?> refNode, boolean insertAfter) {
        this.context = context;
        List<Node<?>> childrenToPersist = getChildNodes();

        Transaction transaction = context.getActiveTransaction();
        // in case of an InstantApplyTx this might result in further subElements being added by listeners, so pre existing
        // subElements need to be collected before this happens or #persist would be called twice for added subElements,
        // resulting in failure
        transaction.internal().addChange(new ElementCreatedEvent(context, this, newParent, refNode, insertAfter));
        for (Node<?> child : childrenToPersist) {
            // parent has already been set
            child.persist(context, null);
        }
    }

    @Override
    public boolean isDetached() {
        return context == null;
    }

    @Override
    public XmlElement copy(boolean copySubElements, boolean instantiateContributedClass) {
        List<Node<?>> childNodes = Lists.newArrayList();
        Map<String, String> attributeMap = new HashMap<>();

        if (copySubElements && hasSubElements()) {
            ReentrantReadWriteLock.ReadLock readLock = this.childNodes.getLock().readLock();
            readLock.lock();
            try {
                for (Node<?> childNode : this.childNodes) {
                    childNodes.add(childNode.copy(true, instantiateContributedClass));
                }
            } finally {
                readLock.unlock();
            }
        }

        for (XmlAttribute attribute : getAttributes()) {
            attributeMap.put(attribute.getAttributeName(), attribute.getValue());
        }

        if (instantiateContributedClass) {
            return StaticXmlElementFactory.instantiate(tagName, childNodes, attributeMap);
        }

        return new BaseXmlElement(tagName, childNodes, attributeMap);
    }

    @Override
    @Nullable
    public Element getElement() {
        return element;
    }

    @Override
    public Element requireElement() throws IllegalStateException {
        if (element == null) {
            throw new IllegalStateException(toString() + " has no Element");
        }

        return element;
    }

    @Nullable
    @Override
    public XmlElement getParent() {
        return parent;
    }

    @Nullable
    @Override
    public Node<?> getPreviousSibling() {
        return previousSibling;
    }

    @Nullable
    @Override
    public Node<?> getNextSibling() {
        return nextSibling;
    }

    @Override
    public Context getContext() {
        return context;
    }

    @Override
    public boolean isSubElement() {
        return parent != null && (isDetached() || !Objects.equals(context.getDocumentElement().getElement(), parent.getElement()));
    }

    @Override
    public boolean isPersisted() {
        return element != null;
    }

    @Deprecated
    @Override
    public boolean checkDuplicates(XmlElement element) {
        if (!this.getTagName().equals(element.getTagName())) return false;
        if (this.getId() == null || element.getId() == null) return false;
        return this.getId().equals(element.getId());
    }

    @Override
    public String getTagName() {
        return tagName;
    }

    @Override
    public List<XmlAttribute> getAttributes() {
        return ImmutableList.copyOf(attributes.values());
    }

    @Override
    public XmlAttribute getAttribute(String attributeName) {
        List<XmlAttribute> foundAttributes = getAttributes().stream()
            .filter(a -> a.getAttributeName().equals(attributeName))
            .collect(Collectors.toList());

        if (foundAttributes.size() == 1) {
            return foundAttributes.get(0);
        } else if (foundAttributes.size() > 1) {
            throw new IllegalStateException("Duplicate attribute: " + attributeName + " on element " + toString());
        } else {
            return new XmlAttribute.Provisional(this, attributeName);
        }
    }

    @Override
    public void removeAttribute(String attributeName) {
        getAttribute(attributeName).remove();
    }

    @Override
    public void setAttribute(String attribute, Object value) {
        XmlAttribute attributeToChange = getAttribute(attribute);
        attributeToChange.setValue(value);
    }

    @Override
    public boolean hasAttribute(String attributeName) {
        return getAttributes().stream().anyMatch(attribute -> attribute.getAttributeName().equals(attributeName));
    }

    @Override
    public void addSubElement(Node<?> element) {
        addSubElements(Collections.singletonList(element));
    }

    @Override
    public void addSubElements(List<Node<?>> elements) {
        if (isDetached()) {
            elements.forEach(elem -> elem.internal().setParent(this));
            childNodes.addAll(elements);
        } else {
            if (state.isPhysical()) {
                elements.forEach(elem -> elem.persist(context, this));
            } else {
                Event.virtualiseEvents(() -> elements.forEach(elem -> elem.persist(context, this)), context);
            }
        }
    }

    @Override
    public void addSubElements(Node<?>... elements) {
        addSubElements(Arrays.asList(elements));
    }

    @Override
    public void insertSubElementAfter(Node<?> refNode, Node<?> childToAdd) {
        insertSubElementsAfter(refNode, Collections.singletonList(childToAdd));
    }

    @Override
    public void insertSubElementsAfter(Node<?> refNode, List<Node<?>> childrenToAdd) {
        insertRelative(refNode, true, childrenToAdd);
    }

    @Override
    public void insertSubElementsAfter(Node<?> refNode, Node<?>... childrenToAdd) {
        insertSubElementsAfter(refNode, Arrays.asList(childrenToAdd));
    }

    @Override
    public void insertSubElementBefore(Node<?> refNode, Node<?> childToAdd) {
        insertSubElementsBefore(refNode, Collections.singletonList(childToAdd));
    }

    @Override
    public void insertSubElementsBefore(Node<?> refNode, List<Node<?>> childrenToAdd) {
        insertRelative(refNode, false, childrenToAdd);
    }

    @Override
    public void insertSubElementsBefore(Node<?> refNode, Node<?>... childrenToAdd) {
        insertSubElementsBefore(refNode, Arrays.asList(childrenToAdd));
    }

    private void insertRelative(Node<?> refNode, boolean insertAfter, List<Node<?>> toAdd) {
        if (!childNodes.contains(refNode)) {
            throw new IllegalArgumentException("The provided refNode is not a child element of " + toString());
        }

        if (isDetached()) {
            toAdd.forEach(elem -> elem.internal().setParent(this));
            ReentrantReadWriteLock.WriteLock writeLock = childNodes.getLock().writeLock();
            writeLock.lock();

            Node<?> lastRef = refNode;
            boolean isFirst = true;
            for (Node<?> node : toAdd) {
                if (node == null) {
                    throw new NullPointerException();
                }

                if (isFirst && !insertAfter) {
                    childNodes.linkBefore(node, lastRef);
                    isFirst = false;
                } else {
                    childNodes.linkAfter(node, lastRef);
                }
                lastRef = node;
            }
            writeLock.unlock();
        } else {
            if (state.isPhysical()) {
                doInsertAll(refNode, insertAfter, toAdd);
            } else {
                Event.virtualiseEvents(() -> doInsertAll(refNode, insertAfter, toAdd), context);
            }
        }
    }

    private void doInsertAll(Node<?> refNode, boolean insertAfter, List<Node<?>> toAdd) {
        boolean isFirst = true;
        for (Node<?> node : toAdd) {
            if (isFirst && !insertAfter) {
                node.persist(context, this, refNode, false);
                isFirst = false;
            } else {
                node.persist(context, this, refNode, true);
            }
            refNode = node;
        }
    }

    @Override
    public void removeSubElement(Node<?> element) {
        removeSubElements(Collections.singletonList(element));
    }

    @Override
    public void removeSubElements(List<Node<?>> elements) {
        if (!childNodes.containsAll(elements)) {
            throw new IllegalArgumentException("Not all provided elements are subElements of " + toString());
        }

        if (isDetached()) {
            elements.forEach(xmlElement -> xmlElement.internal().removeParent());
            childNodes.removeAll(elements);
        } else {
            if (state.isPhysical()) {
                elements.forEach(Node::delete);
            } else {
                Event.virtualiseEvents(() -> elements.forEach(Node::delete), context);
            }
        }
    }

    @Override
    public void removeSubElements(Node<?>... elements) {
        removeSubElements(Arrays.asList(elements));
    }

    @Override
    public List<Node<?>> getChildNodes() {
        return ImmutableList.copyOf(childNodes);
    }

    @Override
    public List<XmlElement> getSubElements() {
        ReentrantReadWriteLock.ReadLock readLock = childNodes.getLock().readLock();
        readLock.lock();
        try {
            return Collections.unmodifiableList(
                childNodes.stream()
                    .filter(node -> node instanceof XmlElement)
                    .map(node -> (XmlElement) node)
                    .collect(Collectors.toList())
            );
        } finally {
            readLock.unlock();
        }
    }

    @Override
    public List<XmlElement> getSubElementsRecursive() {
        List<XmlElement> elements = Lists.newArrayList();
        for (XmlElement element : getSubElements()) {
            recursiveAdd(elements, element);
        }
        return elements;
    }

    private void recursiveAdd(List<XmlElement> elements, XmlElement element) {
        elements.add(element);
        if (element.hasSubElements()) {
            for (XmlElement subElement : element.getSubElements()) {
                recursiveAdd(elements, subElement);
            }
        }
    }

    @Override
    public <E extends XmlElement> List<E> getSubElementsWithType(Class<E> type) {
        return getInstancesOf(type);
    }

    @Override
    public XmlElement getSubElement(String id) {
        return getSubElement(id, XmlElement.class);
    }

    @Override
    public <E extends XmlElement> E getSubElement(String id, Class<E> type) {
        List<E> foundSubElements = getSubElements().stream()
            .filter(subElem -> type.isInstance(subElem) && subElem.getId() != null && subElem.getId().equals(id))
            .map(type::cast)
            .collect(Collectors.toList());

        if (foundSubElements.size() == 1) {
            return foundSubElements.get(0);
        } else if (foundSubElements.size() > 1) {
            throw new IllegalStateException("Multiple SubElements found for id " + id + ". Id's must be unique");
        } else {
            return null;
        }
    }

    @Override
    public XmlElement requireSubElement(String id) throws IllegalStateException {
        return requireSubElement(id, XmlElement.class);
    }

    @Override
    public <E extends XmlElement> E requireSubElement(String id, Class<E> type) throws IllegalStateException {
        E subElement = getSubElement(id, type);

        if (subElement != null) {
            return subElement;
        } else {
            throw new IllegalStateException("No SubElement found for id " + id);
        }
    }

    @Override
    public boolean hasSubElements() {
        ReentrantReadWriteLock.ReadLock readLock = childNodes.getLock().readLock();
        readLock.lock();
        try {
            return childNodes.stream().anyMatch(node -> node instanceof XmlElement);
        } finally {
            readLock.unlock();
        }
    }

    @Override
    public boolean hasSubElement(String id) {
        return getSubElements().stream().anyMatch(subElem -> subElem.getId() != null && subElem.getId().equals(id));
    }

    @Override
    public List<TextNode> getTextNodes() {
        ReentrantReadWriteLock.ReadLock readLock = childNodes.getLock().readLock();
        readLock.lock();
        try {
            return childNodes.stream()
                .filter(node -> node instanceof TextNode)
                .map(node -> (TextNode) node)
                .collect(Collectors.toList());
        } finally {
            readLock.unlock();
        }
    }

    @Override
    public String getTextContent() {
        return getTextNodes().stream().map(TextNode::getTextContent).collect(Collectors.joining(System.lineSeparator()));
    }

    @Override
    public void setTextContent(String textContent) {
        String oldValue = getTextContent();
        List<TextNode> textNodes = getTextNodes();
        if (textNodes.size() == 1) {
            internal().addChange(new TextNodeChangingEvent(context, this, textNodes.get(0), oldValue, textContent));
        } else if (textNodes.isEmpty()) {
            addTextNode(textContent);
        } else {
            textNodes.forEach(TextNode::delete);
            addTextNode(textContent);
        }
    }

    @Override
    public boolean hasTextContent() {
        ReentrantReadWriteLock.ReadLock readLock = childNodes.getLock().readLock();
        readLock.lock();
        try {
            return childNodes.stream().anyMatch(node -> TextNode.class.isAssignableFrom(node.getClass()));
        } finally {
            readLock.unlock();
        }
    }

    @Override
    public boolean matchesStructure(XmlElement elementToCompare) {
        if (!elementToCompare.getTagName().equals(getTagName())) return false;
        return elementToCompare.getAttributes().stream().allMatch(attribute -> this.hasAttribute(attribute.getAttributeName()))
            && getAttributes().stream().allMatch(attribute -> elementToCompare.hasAttribute(attribute.getAttributeName()));
    }

    @Override
    public void delete() {
        if (!isLocked()) {
            if (isDetached()) {
                throw new PersistException("Cannot delete detached XmlElement. This XmlElement has never been persisted in the first place.");
            }

            Transaction transaction = context.getActiveTransaction();

            State oldState = state;
            ElementDeletingEvent deletingEvent = new ElementDeletingEvent(context, this, oldState);
            transaction.internal().addChange(deletingEvent);
            if (!childNodes.isEmpty()) {
                // cannot use read lock as the following action acquires a write lock if instantApply is true
                // also no sense in acquiring a write lock and then to a normal foreach iteration as a copy is required
                // due to concurrent modification anyway
                List<Node<?>> nodes = Lists.newArrayList(childNodes);
                nodes.forEach(Node::delete);
            }
        } else {
            throw new PersistException("Unable to delete. " + toString() + " is locked");
        }
    }

    @Override
    public boolean hasChanges() {
        return !changes.isEmpty();
    }

    @Override
    public boolean attributeChanged(String attributeName) {
        return Lists.newArrayList(changes).stream().anyMatch(change -> change.attributeChanged(attributeName));
    }

    @Override
    public boolean textContentChanged() {
        return Lists.newArrayList(changes).stream().anyMatch(change -> change.getChangedTextContent() != null);
    }

    @Override
    public void lock() {
        locked = true;
    }

    @Override
    public void unlock() {
        locked = false;
    }

    @Override
    public boolean isLocked() {
        return locked;
    }

    @Override
    public State getState() {
        return state;
    }

    @Override
    public <E extends XmlElement> List<E> getInstancesOf(Class<E> c) {
        return getSubElements().stream()
            .filter(c::isInstance)
            .map(c::cast)
            .collect(Collectors.toList());
    }

    @Override
    public <E extends XmlElement> List<E> getInstancesOf(Class<E> c, Class<?>... ignoredSubClasses) {
        return getSubElements().stream()
            .filter(elem -> c.isInstance(elem) && Arrays.stream(ignoredSubClasses).noneMatch(clazz -> clazz.isInstance(elem)))
            .map(c::cast)
            .collect(Collectors.toList());
    }

    @Override
    public ResultStream<XmlElement> query(Predicate<XmlElement> condition) {
        return Query.evaluate(condition).execute(getSubElementsRecursive());
    }

    @Override
    public <E extends XmlElement> ResultStream<E> query(Predicate<XmlElement> condition, Class<E> type) {
        return Query.evaluate(condition).execute(getSubElementsRecursive(), type);
    }

    @Override
    public String toString() {
        return "XmlElement<" + getTagName() + ">:" + getId();
    }

    @Override
    public Internals internal() {
        return internalControl;
    }

    private void initParentAndSiblingLinkages(@Nullable Node<?> initPrev, List<? extends Node<?>> childNodes) {
        Node<?> prev = initPrev;
        for (Node<?> childNode : childNodes) {
            childNode.internal().setParent(this);
            childNode.internal().setPreviousSibling(prev);
            if (prev != null) {
                prev.internal().setNextSibling(childNode);
            }
            prev = childNode;
        }
    }

    private class InternalControl implements Internals {

        @Override
        public void setElement(Element element) {
            if (AbstractXmlElement.this.element != null && AbstractXmlElement.this.element != element) {
                throw new IllegalStateException(AbstractXmlElement.this.toString() + " is already persisted as an element. Destroy the old element first.");
            }

            AbstractXmlElement.this.element = element;
        }

        @Override
        public void removeElement() {
            element = null;
        }

        @Override
        public void removeParent() {
            parent = null;
        }

        @Override
        public void setParent(XmlElement parent) {
            XmlElement oldParent = AbstractXmlElement.this.parent;
            if (oldParent != null && parent != oldParent) {
                if (oldParent instanceof UninitializedParent) {
                    UninitializedParent uninitializedParent = (UninitializedParent) oldParent;
                    if (uninitializedParent.getChild() != AbstractXmlElement.this) {
                        throw new IllegalArgumentException("The provided UninitializedParent is a parent of a different element");
                    }
                } else {
                    throw new IllegalStateException(AbstractXmlElement.this.toString() + " already has a parent. Remove it from the old parent first.");
                }
            }

            AbstractXmlElement.this.parent = parent;
        }

        @Override
        public void adoptChild(Node<?> nodeToAdopt, @Nullable Node<?> refNode, boolean insertAfter) {
            if (refNode != null) {
                if (insertAfter) {
                    childNodes.linkAfter(nodeToAdopt, refNode);
                } else {
                    childNodes.linkBefore(nodeToAdopt, refNode);
                }
            } else {
                if (insertAfter) {
                    childNodes.linkLast(nodeToAdopt);
                } else {
                    childNodes.linkFirst(nodeToAdopt);
                }
            }
        }

        @Override
        public void removeChild(Node<?> node) {
            childNodes.remove(node);
        }

        @Override
        public void setPreviousSibling(Node<?> node) {
            if (previousSibling != null && previousSibling != node) {
                throw new IllegalStateException(AbstractXmlElement.this.toString() + " already has a previous sibling. Delete the element from its old location before inserting it to a different one.");
            }

            previousSibling = node;
        }

        @Override
        public void removePreviousSibling() {
            previousSibling = null;
        }

        @Override
        public void setNextSibling(Node<?> node) {
            if (nextSibling != null && nextSibling != node) {
                throw new IllegalStateException(AbstractXmlElement.this.toString() + " already has a next sibling. Delete the element from its old location before inserting it to a different one.");
            }

            nextSibling = node;
        }

        @Override
        public void removeNextSibling() {
            nextSibling = null;
        }

        @Override
        public Map<String, XmlAttribute> getInternalAttributeMap() {
            return attributes;
        }

        @Override
        public NodeList getInternalChildNodeList() {
            return childNodes;
        }

        @Override
        public void addChange(ElementChangingEvent change) {
            if (!isLocked()) {
                if (isDetached()) {
                    applyChange(change);
                } else {
                    if (state.isPhysical() || (state.isTransitioning() && change.shouldTreatAsPhysicalIfTransitioning())) {
                        Transaction transaction = context.getActiveTransaction();

                        if (state == State.CLEAN) {
                            setState(State.TOUCHED);
                        }
                        changes.add(change);
                        transaction.internal().addChange(change);
                    } else {
                        Transaction transaction = context.getTransaction();
                        if (transaction != null) {
                            changes.add(change);
                            change.setVirtual(true);
                            transaction.internal().addChange(change);
                        } else {
                            applyChange(change);
                        }
                    }
                }
            } else {
                throw new PersistException("Unable to add Change. " + AbstractXmlElement.this.toString() + " is locked.");
            }
        }

        @Override
        public void removeChange(ElementChangingEvent change) {
            changes.remove(change);

            if (!hasChanges() && state.isPhysical()) {
                setState(State.CLEAN);
            }
        }

        @Override
        public void applyChange(ElementChangingEvent change) throws UnsupportedOperationException, PersistException {
            applyChange(change, false);
        }

        @Override
        public void revertChange(ElementChangingEvent change) throws UnsupportedOperationException, PersistException {
            applyChange(change, true);
        }

        @Override
        public List<ElementChangingEvent> getChanges() {
            return changes;
        }

        private void applyChange(ElementChangingEvent change, boolean isRollback) {
            if (change.getSource() != AbstractXmlElement.this) {
                throw new UnsupportedOperationException("Source of ElementChangingEvent is not this XmlElement. Change can't be applied.");
            }

            AttributeChangingEvent attributeChange = change.getAttributeChange();
            if (attributeChange != null) {
                XmlAttribute attributeToChange = attributeChange.getAttribute();
                if (isRollback) {
                    attributeToChange.revertChange(attributeChange);
                } else {
                    attributeToChange.applyChange(attributeChange);
                }
            }

            AttributeDeletedEvent attributeDeletion = change.getAttributeDeletion();
            if (attributeDeletion != null) {
                XmlAttribute attribute = attributeDeletion.getAttribute();
                if (isRollback) {
                    attributes.put(attribute.getAttributeName(), attribute);
                } else {
                    attributes.remove(attribute.getAttributeName());
                }
            }

            AttributeCreatedEvent addedAttribute = change.getAddedAttribute();
            if (addedAttribute != null) {
                XmlAttribute attribute = addedAttribute.getAttribute();
                if (isRollback) {
                    attributes.remove(attribute.getAttributeName());
                } else {
                    attributes.put(attribute.getAttributeName(), attribute);
                }
            }

            TextNodeChangingEvent changedTextContent = change.getChangedTextContent();
            if (changedTextContent != null) {
                changedTextContent.getTextNode().applyChange(changedTextContent, isRollback);
            }

            TextNodeCreatedEvent addedTextNode = change.getAddedTextNode();
            if (addedTextNode != null) {
                TextNode textNode = addedTextNode.getTextNode();
                if (isRollback) {
                    textNode.internal().removeParent();
                    removeChild(textNode);
                } else {
                    textNode.internal().setParent(AbstractXmlElement.this);
                    Node<?> refNode = addedTextNode.getRefNode();
                    boolean insertAfter = addedTextNode.isInsertAfter();
                    adoptChild(textNode, refNode, insertAfter);
                }
            }

            TextNodeDeletingEvent deletedTextNode = change.getDeletedTextNode();
            if (deletedTextNode != null) {
                TextNode textNode = deletedTextNode.getTextNode();
                if (isRollback) {
                    XmlElement oldParent = deletedTextNode.getOldParent();
                    textNode.internal().setParent(oldParent);
                    oldParent.internal().adoptChild(textNode, deletedTextNode.getOldPreviousSibling(), true);
                } else {
                    textNode.internal().removeParent();
                    removeChild(textNode);
                }
            }
        }

        @Override
        public void setState(State state) {
            AbstractXmlElement.this.state = state;
        }

    }

}
