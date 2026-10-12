package net.robinfriedli.jxp.api;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Element;

/**
 * The interface for any JXP representation of org.w3c {@link org.w3c.dom.Node} instances.
 *
 * @param <T> the represented {@link org.w3c.dom.Node} type
 */
public interface Node<T extends org.w3c.dom.Node> {


    /**
     * Persist this node to the xml document with the root document element (see {@link Context#getDocumentElement()})
     * as parent where the new node will be added as last child node.
     *
     * @param context the context for the document to save the element to
     */
    void persist(Context context);

    /**
     * Persist this element as the child of the provided parent where the new node will be added as last child node.
     *
     * @param context   the context for the document to save the element to
     * @param newParent the parent element
     */
    void persist(Context context, XmlElement newParent);

    /**
     * Persist this node to the XML document as the child of the provided newParent where the new node will be inserted
     * at the relative position as specified by the refNode and insertAfter parameter.
     *
     * @param context     the context for the document to save the element to
     * @param newParent   the parent element
     * @param refNode     the node after / before which to insert the new element
     * @param insertAfter whether to insert the new node after the provided refNode (default) or before, if refNode is
     *                    <code>null</code> this determines whether the new node will be added at the end of its parent's
     *                    child node list, if insertAfter is <code>true</code>, or at the top of the child node list.
     */
    void persist(Context context, XmlElement newParent, @Nullable Node<?> refNode, boolean insertAfter);

    /**
     * Delete a persistent Node from the XML document.
     */
    void delete();

    /**
     * @return true if this Node was persisted to the XML document, i.e. if {@link #getElement()} does not return null.
     */
    boolean isPersisted();

    /**
     * @return true if this Node is not in any Context. This is the case when a Node has just been
     * instantiated before persisting it to a Context.
     */
    boolean isDetached();

    /**
     * @return {@link Context} of this Node, may be null if detached, i.e. the Node has been instantiated but
     * not yet persisted to a Context.
     */
    @Nullable
    Context getContext();

    /**
     * Creates a new Node instance based on this one. This does not require a transaction as
     * it does not persist the copy.
     *
     * @param deep                        also copies all children of this node
     * @param instantiateContributedClass tries to instantiate one of your classes contributed to the {@link JxpBackend}
     *                                    if none found or false returns a {@link BaseXmlElement}. Mind that your class has to have a constructor matching
     *                                    {@link BaseXmlElement} to be instantiated by this method.
     * @return the newly created XmlElement
     */
    Node<T> copy(boolean deep, boolean instantiateContributedClass);

    /**
     * @return the represented DOM Node of type {@link T} if this Node is persistent, else null.
     */
    @Nullable
    T getElement();

    /**
     * Like {@link #getElement()} but throws an {@link IllegalStateException} if null.
     */
    default T requireElement() throws IllegalStateException {
        T element = getElement();

        if (element == null) {
            throw new IllegalStateException(toString() + "is not persistent.");
        }

        return element;
    }

    /**
     * @return the parent Element of this Node. Might return null if this Node represents the root document
     * element or if this is a new Node that hasn't been persisted yet (i.e. the creation event hasn't been applied yet).
     */
    @Nullable
    XmlElement getParent();

    /**
     * @return the previous node on the same level as and adjacent to this node
     */
    @Nullable
    Node<?> getPreviousSibling();

    /**
     * @return the next node on the same level as and adjacent to this node
     */
    @Nullable
    Node<?> getNextSibling();

    /**
     * @return access to internal API methods.
     */
    Internals<T> internal();

    /**
     * Interface for internal API methods to separate them from the regular API
     *
     * @param <T> the represented {@link org.w3c.dom.Node} type
     */
    interface Internals<T extends org.w3c.dom.Node> {

        /**
         * Sets the created {@link T} for this XmlElement. Used after a new XmlElement has been persisted.
         */
        void setElement(T element);

        /**
         * Set the parent of this node to null on destruction.
         */
        void removeElement();

        /**
         * Set the parent of this node to null on removal.
         */
        void removeParent();

        /**
         * Set the JXP element representation for the parent DOM {@link Element}. This is not permitted if the element
         * already has a parent, the element first has to be removed from the old parent.
         *
         * @param parent the parent element
         * @throws IllegalStateException if this Node already has an initialized parent
         */
        void setParent(XmlElement parent);

        /**
         * Set the JXP Node representation for the previous sibling's DOM {@link org.w3c.dom.Node} (see {@link org.w3c.dom.Node#getPreviousSibling()}).
         * This is not allowed if this node already has a previous sibling, even if the provided node is <code>null</code>,
         * which is where {@link #removePreviousSibling()} is used.
         *
         * @param node the node to set as previous sibling
         * @throws IllegalStateException if this Node already has an initialized previous sibling
         */
        void setPreviousSibling(Node<?> node);

        /**
         * Set the previous sibling of this node to <code>null</code>.
         */
        void removePreviousSibling();

        /**
         * Set the JXP Node representation for the next sibling's DOM {@link org.w3c.dom.Node} (see {@link org.w3c.dom.Node#getNextSibling()}).
         * This is not allowed if this node already has a next sibling, even if the provided node is <code>null</code>,
         * which is where {@link #removeNextSibling()} is used.
         *
         * @param node the node to set as next sibling
         * @throws IllegalStateException if this Node already has an initialized next sibling
         */
        void setNextSibling(Node<?> node);

        /**
         * Set the next sibling of this node to <code>null</code>.
         */
        void removeNextSibling();

        /**
         * Add the Element of type {@link T} represented by this node to the DOM document upon persisting. The element was
         * already created while applying the creation event.
         *
         * @param elem        the {@link org.w3c.dom.Node} of type {@link T} represented by this JXP node to add to the DOM.
         *                    This is specified explicitly as it might have changed between the time the creation event was
         *                    applied, which is when the node of type T is created, and the time is actually committed
         *                    (e.g. if the same element is created, deleted and then created again in the same transaction, the
         *                    element of type T represented by this JXP node will be a different one by the time the first creation
         *                    is committed) to make sure the exact same {@link org.w3c.dom.Node} of type {@link T} is inserted
         *                    to the dom that was created by the current creation event.
         * @param parent      the parent for which to insert the new element, must be persistent. This is specified explicitly
         *                    as the parent element may have changed between the time the creation event is applied and it is
         *                    committed
         * @param refNode     the referenced persistent node used for relative positioning
         * @param insertAfter if true the new node will be inserted after the referenced sibling, else the new node will
         *                    be inserted before the referenced sibling (which is default behaviour, see
         *                    {@link org.w3c.dom.Node#insertBefore(org.w3c.dom.Node, org.w3c.dom.Node)}).
         */
        default void addToDOM(T elem, org.w3c.dom.Node parent, @Nullable org.w3c.dom.Node refNode, boolean insertAfter) {
            if (parent == null) {
                throw new PersistException("Cannot persist new root document element, element needs to have a defined parent before persisting.");
            }

            if (refNode != null) {
                if (insertAfter) {
                    org.w3c.dom.Node nextSibling = refNode.getNextSibling();
                    parent.insertBefore(elem, nextSibling);
                } else {
                    parent.insertBefore(elem, refNode);
                }
            } else {
                parent.appendChild(elem);
            }
        }

        /**
         * Convenience overload that accepts a nullable JXP Node and calls {@link #addToDOM(org.w3c.dom.Node, org.w3c.dom.Node, org.w3c.dom.Node, boolean)}
         * accordingly.
         *
         * @param parent      the parent for which to insert the new element, must be persistent. This is specified explicitly
         *                    as the parent element may have changed between the time the creation event is applied and it is
         *                    committed
         * @param refNode     the referenced JXP Node used for relative positioning
         * @param insertAfter if true the new node will be inserted after the referenced sibling, else before.
         * @throws PersistException if the provided refNode is not persistent
         */
        default void addToDOM(T elem, org.w3c.dom.Node parent, @Nullable Node<?> refNode, boolean insertAfter) {
            if (refNode != null) {
                org.w3c.dom.Node persistentRefNode = refNode.getElement();
                if (persistentRefNode != null) {
                    addToDOM(elem, parent, persistentRefNode, insertAfter);
                } else {
                    throw new PersistException("Reference node used for relative position needs to get persisted first. Make sure you persist the referenced node first when inserting a new node before or after it.");
                }
            } else {
                addToDOM(elem, parent, (org.w3c.dom.Node) null, false);
            }
        }

    }

}
