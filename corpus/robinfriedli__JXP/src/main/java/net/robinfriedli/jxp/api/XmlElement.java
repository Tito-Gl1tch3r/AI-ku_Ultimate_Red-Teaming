package net.robinfriedli.jxp.api;

import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.collections.NodeList;
import net.robinfriedli.jxp.events.ElementChangingEvent;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.queries.Conditions;
import net.robinfriedli.jxp.queries.QueryResult;
import net.robinfriedli.jxp.queries.ResultStream;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Text;

/**
 * Interface for the JXP representation of DOM {@link Element} instances, does not include text nodes.
 */
public interface XmlElement extends Node<Element> {

    /**
     * Persists a new XmlElement in {@link State#CONCEPTION} to the XML file. This method calls {@link #persist(Context, XmlElement)}
     * with the document element as newParent.
     *
     * @param context the context for the document to save the element to
     */
    void persist(Context context);

    /**
     * Persist this element as the child of the provided parent. This method is used by {@link #addSubElement(Node)}.
     * Since you may not create new root elements the only way newParent may be null is when this method is called recursively
     * internally to persist all children this element may already have in which case the parent is already set the children
     * have already been adopted.
     * <p>
     * Generally library users should use {@link #persist(Context)} or {@link #addSubElement(Node)} instead of using
     * this method directly.
     *
     * @param context   the context for the document to save the element to
     * @param newParent the parent element
     */
    void persist(Context context, XmlElement newParent);

    /**
     * Creates a new XmlElement with the attributes and text content of this one. This does not require a transaction as
     * it does not persist the copy. This overrides {@link Node#copy(boolean, boolean)} to specialise the return type.
     *
     * @param copySubElements             also copies all subelements of this element
     * @param instantiateContributedClass tries to instantiate one of your classes contributed to the {@link JxpBackend}
     *                                    if none found or false returns a {@link BaseXmlElement}. Mind that your class has to have a constructor matching
     *                                    {@link BaseXmlElement} to be instantiated by this method.
     * @return the newly created XmlElement
     */
    XmlElement copy(boolean copySubElements, boolean instantiateContributedClass);

    /**
     * @return the actual {@link Element} in the XML document represented by this XmlElement. Null if in State CONCEPTION
     * or PHANTOM. Changes made to this Element are not reflected by JXP.
     */
    @Nullable
    Element getElement();

    /**
     * Like {@link #getElement()} but throws Exception if null
     */
    Element requireElement() throws IllegalStateException;

    /**
     * @return true if this XmlElement has a parent element that is not the Document's root element.
     */
    boolean isSubElement();

    /**
     * @return true if the XmlElement has an {@link Element}, meaning it has been persisted to the XML file
     */
    boolean isPersisted();

    /**
     * @return {@link Context} of this XmlElement, may be null if detached, i.e. the XmlElement has been instantiated but
     * not yet persisted to a Context (state {@link State#CONCEPTION}).
     */
    @Nullable
    Context getContext();

    /**
     * @return Tag name for this xml element
     */
    String getTagName();

    /**
     * @return a new immutable list instance containing all {@link XmlAttribute} instances currently on this XmlElement
     */
    List<XmlAttribute> getAttributes();

    /**
     * @param attributeName name of attribute
     * @return XmlAttribute instance with specified name or a new {@link XmlAttribute.Provisional}
     */
    XmlAttribute getAttribute(String attributeName);


    /**
     * Deletes the given attribute from this XmlElement. This action requires a Transaction for an XmlElement in a
     * physical state.
     *
     * @param attributeName the name of the attribute to remove
     */
    void removeAttribute(String attributeName);

    /**
     * Set existing attribute to a different value or create a new one.
     *
     * @param attribute XML attribute name to change
     * @param value     new value
     */
    void setAttribute(String attribute, Object value);

    /**
     * @param attributeName name of attribute to check
     * @return true if this XmlElement has an attribute with the specified name
     */
    boolean hasAttribute(String attributeName);

    /**
     * Add a new child node to this XmlElement.
     *
     * @param element the non-persistent node to add
     */
    void addSubElement(Node<?> element);

    /**
     * Add several new child nodes to this XmlElement in the order they appear in the provided list.
     *
     * @param elements the non-persistent nodes to add
     */
    void addSubElements(List<Node<?>> elements);

    /**
     * Add several new child nodes to this XmlElement in the order they appear in the provided array.
     *
     * @param elements the non-persistent nodes to add
     */
    void addSubElements(Node<?>... elements);

    /**
     * Add a new child element to this XmlElement and position it after the provided existing child node.
     *
     * @param refNode    the existing node after which to insert the new node
     * @param childToAdd the new non-persistent element to add
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    void insertSubElementAfter(Node<?> refNode, Node<?> childToAdd);

    /**
     * Add new child nodes to this XmlElement and position them all after the provided existing child node in the
     * order in which they appear in the provided list.
     *
     * @param refNode       the existing node after which to insert the new node
     * @param childrenToAdd the new non-persistent nodes to add
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    void insertSubElementsAfter(Node<?> refNode, List<Node<?>> childrenToAdd);

    /**
     * Add new child nodes to this XmlElement and position them all after the provided existing child node in the
     * order in which they appear in the provided list.
     *
     * @param refNode       the existing node after which to insert the new node
     * @param childrenToAdd the new non-persistent nodes to add
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    void insertSubElementsAfter(Node<?> refNode, Node<?>... childrenToAdd);

    /**
     * Add a new child element to this XmlElement and position it before the provided existing child node.
     *
     * @param refNode    the existing node before which to insert the new node
     * @param childToAdd the new non-persistent element to add
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    void insertSubElementBefore(Node<?> refNode, Node<?> childToAdd);

    /**
     * Add new child nodes to this XmlElement and position them all before the provided existing child node in the
     * order in which they appear in the provided list.
     *
     * @param refNode       the existing node before which to insert the new node
     * @param childrenToAdd the new non-persistent nodes to add
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    void insertSubElementsBefore(Node<?> refNode, List<Node<?>> childrenToAdd);

    /**
     * Add new child nodes to this XmlElement and position them all before the provided existing child node in the
     * order in which they appear in the provided list.
     *
     * @param refNode       the existing node before which to insert the new node
     * @param childrenToAdd the new non-persistent nodes to add
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    void insertSubElementsBefore(Node<?> refNode, Node<?>... childrenToAdd);

    /**
     * Remove an existing child node from this XmlElement.
     *
     * @param element the existing child node to delete
     * @throws IllegalArgumentException if any of the provided sub elements is not actually a sub element of this element
     */
    void removeSubElement(Node<?> element);

    /**
     * Remove existing child nodes from this XmlElement.
     *
     * @param elements the existing child nodes to delete
     * @throws IllegalArgumentException if any of the provided sub elements is not actually a sub element of this element
     */
    void removeSubElements(List<Node<?>> elements);

    /**
     * Remove existing child nodes from this XmlElement.
     *
     * @param elements the existing child nodes to delete
     * @throws IllegalArgumentException if any of the provided sub elements is not actually a sub element of this element
     */
    void removeSubElements(Node<?>... elements);

    /**
     * @return all child nodes of this XmlElement, including all sub elements and text nodes.
     */
    List<Node<?>> getChildNodes();

    /**
     * @return an unmodifiable collection of all SubElements.
     */
    List<XmlElement> getSubElements();

    /**
     * @return all subElements and their subElements
     */
    List<XmlElement> getSubElementsRecursive();

    /**
     * Get all subElements of this XmlElement of type {@link E}. Use this to method to treat subElements as instances of
     * their original class rather than XmlElements. As of v1.1 an alias for method {@link #getInstancesOf(Class)}
     *
     * @param type Subclass of XmlElement you want to filter and cast the subElements to
     * @param <E>  target Type. Subclass of XmlElement
     * @return all filtered SubElements as instances of class E
     */
    <E extends XmlElement> List<E> getSubElementsWithType(Class<E> type);

    /**
     * Get one of the subElements via their unique {@link #getId()}
     *
     * @param id unique id to find the subElement with
     * @return found subElement
     */
    @Nullable
    XmlElement getSubElement(String id);

    /**
     * Same as {@link #getSubElement(String)} but also checks whether the sub element matches the given type and casts
     * it to it
     */
    @Nullable
    <E extends XmlElement> E getSubElement(String id, Class<E> type);

    /**
     * Like {@link #getSubElement(String)} but throws {@link IllegalStateException} if none is found
     *
     * @param id unique id to find the subElement with
     * @return found subElement
     * @throws IllegalStateException if no subElement is found
     */
    XmlElement requireSubElement(String id) throws IllegalStateException;

    /**
     * Same as {@link #requireSubElement(String)} but also checks whether the sub element matches the given type and casts
     * it to it
     */
    <E extends XmlElement> E requireSubElement(String id, Class<E> type) throws IllegalStateException;

    /**
     * @return true if this XmlElement has any SubElements
     */
    boolean hasSubElements();

    /**
     * Checks if this XmlElement has a subElement where {@link #getId()} matches the provided id
     *
     * @param id of subElement
     * @return true if element has subElement with specified id
     */
    boolean hasSubElement(String id);

    /**
     * @return all children that are TextNodes, meaning they represent a {@link Text} node.
     */
    List<TextNode> getTextNodes();

    /**
     * Get the text content of the XML element.
     * <p>
     * E.g. <element>textContent</element>
     * <p>
     * In case of mixed content or several text nodes this joins all text nodes on {@link System#lineSeparator()}.
     *
     * @return text content of XML element
     */
    String getTextContent();

    /**
     * Set the text content of the XML element.
     * <p>
     * E.g. <element>textContent</element>
     * <p>
     * If there already is exactly one {@link TextNode} this will update the existing text node. Else this will delete
     * all existing text nodes and add a new text node as last child of this XmlElement.
     *
     * @param textContent to set
     */
    void setTextContent(String textContent);

    /**
     * @return true if this XmlElement has any child text nodes.
     */
    boolean hasTextContent();

    /**
     * Create a new {@link TextNode} and add it as last child to this XmlElement.
     *
     * @param textContent the text content of the new text node.
     */
    default void addTextNode(String textContent) {
        TextNode textNode = new TextNode(textContent);
        addSubElement(textNode);
    }

    /**
     * Create a new {@link TextNode} and insert it after the specified existing child node.
     *
     * @param refNode     the existing child node after which to insert the text node
     * @param textContent the text content of the new text node
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    default void insertTextNodeAfter(Node<?> refNode, String textContent) {
        TextNode textNode = new TextNode(textContent);
        insertSubElementAfter(refNode, textNode);
    }

    /**
     * Create a new {@link TextNode} and insert it before the specified existing child node.
     *
     * @param refNode     the existing child node before which to insert the text node
     * @param textContent the text content of the new text node
     * @throws IllegalArgumentException if the provided refNode is not a child of this XmlElement
     */
    default void insertTextNodeBefore(Node<?> refNode, String textContent) {
        TextNode textNode = new TextNode(textContent);
        insertSubElementsBefore(refNode, textNode);
    }

    /**
     * Define some way to identify this XmlElement instance, ideally through either one of its attributes or text content.
     * If there is no way to uniquely identify this XmlElement, just return null.
     *
     * @return unique id for this XmlElement instance
     */
    @Nullable
    String getId();

    /**
     * Check if an XmlElement already exists in the same {@link Context} and thus would result in a duplicate.
     * Ideally you should compare attributes that represent an id of some kind.
     * If you do not want to check your XmlElement for duplicates just return false.
     * <p>
     * The default implementation in {@link AbstractXmlElement} checks if there is another XmlElement with the same
     * same tag and id returned by {@link #getId()}
     *
     * @param elementToCheck XmlElement to compare
     * @return true if the specified XmlElement would duplicate an already existing Element
     */
    @Deprecated
    boolean checkDuplicates(XmlElement elementToCheck);

    /**
     * Checks if the provided XmlElement has the same structure, meaning the same tag name and attributes
     *
     * @param elementToCompare element to compare
     * @return true if tag name and attribute names match
     */
    boolean matchesStructure(XmlElement elementToCompare);

    /**
     * Delete this XmlElement. Creates an {@link net.robinfriedli.jxp.events.ElementDeletingEvent} which, when applied,
     * will remove the element from its Context and set this XmlElement to {@link State#PHANTOM}. Only when committing
     * the XmlElement will be fully removed from the DOM document and its XML file.
     */
    void delete();

    /**
     * @return true if this XmlElement has uncommitted {@link ElementChangingEvent}s
     */
    boolean hasChanges();

    /**
     * Check if attribute with specified name has any uncommitted changes
     *
     * @param attributeName name of attribute
     * @return true if attribute has changes
     */
    boolean attributeChanged(String attributeName);

    /**
     * @return true if this XmlElement's text content has uncommitted changes
     */
    boolean textContentChanged();

    /**
     * Prevents this XmlElement instance from being changed or deleted.
     */
    void lock();

    void unlock();

    /**
     * @return true if this XmlElement is locked. See {@link #lock()}
     */
    boolean isLocked();

    /**
     * @return {@link State} of this XmlElement
     */
    State getState();

    /**
     * Get all subElements that are instance of {@link E}
     *
     * @param c   Class to check
     * @param <E> Type of Class to check
     * @return All Elements that are an instance of specified Class
     */
    <E extends XmlElement> List<E> getInstancesOf(Class<E> c);

    /**
     * Get all subElements that are instance of {@link E}, ignoring elements that are instance of
     * any of the ignored subClasses. Used to exclude subclasses.
     *
     * @param c                 Class to check
     * @param ignoredSubClasses subclasses to exclude
     * @param <E>               Type to return
     * @return All Elements that are an instance of specified Class but not specified subclasses
     */
    <E extends XmlElement> List<E> getInstancesOf(Class<E> c, Class<?>... ignoredSubClasses);

    /**
     * Checks all subElements for provided {@link Predicate}s and returns {@link QueryResult} with matching elements.
     * See {@link Conditions} for useful predicates.
     *
     * @param condition
     * @return
     */
    ResultStream<XmlElement> query(Predicate<XmlElement> condition);

    /**
     * Like {@link #query(Predicate)} but casts the found elements to the given class
     */
    <E extends XmlElement> ResultStream<E> query(Predicate<XmlElement> condition, Class<E> type);

    /**
     * @return an interface that provides access to library internals
     */
    Internals internal();

    /**
     * The state of the in memory representation of the XML element
     */
    enum State {

        /**
         * XmlElement instance has just been created but not yet persisted to the XML document.
         * All changes made to this element are applied immediately as there is no need to update its XML element representation,
         * this also means changes do not necessarily require a transaction but without a transaction write-access is
         * not synchronised across threads.
         */
        CONCEPTION(false, false),

        /**
         * {@link XmlElement#persist(Context)} has already been called on this element in the current transaction but
         * the transaction hasn't been committed yet. Those elements are treated as physical elements already even though
         * their physical {@link Element} representation has not been created and added to the {@link Document} yet as changes
         * made to those elements will get committed after the {@link Element} is created and thus those changes required
         * to be committed as well (changes such as adding or removing a child element).
         */
        PERSISTING(true, true),

        /**
         * Element exists and has no uncommitted changes
         */
        CLEAN(true, false),

        /**
         * Element exists in XML file but has uncommitted changes
         */
        TOUCHED(true, false),

        /**
         * Unlike PHANTOM the Element has not actually been deleted yet and still exists in the XML document. This is
         * state of elements after the delete() method has been called but before the change has been committed.
         * <p>
         * Physical is already false even though that is technically incorrect since this state is only temporary during
         * Transactions and we want to treat those element like phantoms. Even IF the element would get persisted again
         * in the same transaction, it would get persisted with all changes applied. Thus eliminating the need to commit
         * changes as with normal physical elements.
         */
        DELETION(false, true),

        /**
         * The XmlElement has been removed from the XML document. This instance may be re-persisted by calling {@link XmlElement#persist(Context)}.
         * All changes made to this element are applied immediately as there is no need to update its XML element representation,
         * this also means changes do not necessarily require a transaction but without a transaction write-access is
         * not synchronised across threads.
         */
        PHANTOM(false, false);

        private final boolean physical;
        private final boolean transitioning;

        State(boolean physical, boolean transitioning) {
            this.physical = physical;
            this.transitioning = transitioning;
        }

        /**
         * @return true if the element has a physical element in the XML file in this state. Defines whether or not
         * changes made to an element need to be committed.
         */
        public boolean isPhysical() {
            return physical;
        }

        /**
         * @return true if this element is currently transitioning from being physical to being virtual or vice versa in
         * the current transaction, i.e. if this element is currently being persisted or deleted
         */
        public boolean isTransitioning() {
            return transitioning;
        }
    }

    /**
     * Sub interface for methods intended for internal use to clearly separate them from the regular API while still allowing
     * access.
     */
    interface Internals extends Node.Internals<Element> {

        /**
         * Sets the created {@link Element} for this XmlElement. Used after a new XmlElement has been persisted.
         */
        void setElement(Element element);

        /**
         * Set the parent of this XmlElement to null. Used for subElements when {@link #removeSubElement(Node)} is called
         */
        void removeParent();

        /**
         * Defines the parent of a subElement. This is not permitted if the element already has a parent, the element first
         * has to be removed from the old parent using {@link #removeSubElement(Node)}.
         */
        void setParent(XmlElement parent);

        /**
         * Adopt a child node. This adds this node to the end of this node's child nodes and handles setting the parent
         * and next / previous sibling of the child node.
         *
         * @param node the node to adopt
         */
        default void adoptChild(Node<?> node) {
            adoptChild(node, null, true);
        }

        /**
         * Insert a child node at a position relative to the provided child node. If refNode is null the node will be inserted
         * at the bottom of the list if insertAfter is true, else at the top of the list.
         *
         * @param nodeToAdopt the node to add
         * @param refNode     the existing child node after or before which to add the new node
         * @param insertAfter if true the new node will be inserted after the provided refNode, else before
         */
        void adoptChild(Node<?> nodeToAdopt, @Nullable Node<?> refNode, boolean insertAfter);

        /**
         * Remove a child node from this node. This removes the provided node from this node's child nodes and handles
         * un-setting the node's parent and next / previous sibling.
         *
         * @param node the node to remove
         * @throws IllegalArgumentException if the provided node is not a child of this node
         */
        void removeChild(Node<?> node);

        /**
         * @return the actual map instance holding the {@link XmlAttribute} instances for this XmlElement
         */
        Map<String, XmlAttribute> getInternalAttributeMap();

        /**
         * @return the internal list instance that stores the subelements
         */
        NodeList getInternalChildNodeList();

        /**
         * Add an {@link ElementChangingEvent} to this XmlElement
         *
         * @param change to add
         */
        void addChange(ElementChangingEvent change);

        /**
         * Remove an {@link ElementChangingEvent} from this XmlElement
         *
         * @param change to remove
         */
        void removeChange(ElementChangingEvent change);

        /**
         * Applies an {@link ElementChangingEvent} to this XmlElement. The source of the event must be this XmlElement or else
         * an {@link UnsupportedOperationException} is thrown.
         *
         * @param change {@link ElementChangingEvent} to apply
         * @throws UnsupportedOperationException if source of event does not equal this XmlElement
         * @throws PersistException              if {@link Context} has no {@link net.robinfriedli.jxp.persist.Transaction}
         */
        void applyChange(ElementChangingEvent change) throws UnsupportedOperationException, PersistException;

        /**
         * Reverts a change made to this XmlElement. This occurs when an exception is thrown during commit.
         *
         * @param change {@link ElementChangingEvent} change to revert
         * @throws UnsupportedOperationException
         * @throws PersistException
         */
        void revertChange(ElementChangingEvent change) throws UnsupportedOperationException, PersistException;

        /**
         * @return all {@link ElementChangingEvent} on this XmlElement. This exposes the internal list directly.
         */
        List<ElementChangingEvent> getChanges();

        /**
         * Set the {@link State} of this XmlElement
         *
         * @param state to set
         */
        void setState(State state);

    }

}
