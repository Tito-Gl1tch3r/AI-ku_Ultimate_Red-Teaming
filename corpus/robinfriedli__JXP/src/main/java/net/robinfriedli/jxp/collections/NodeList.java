package net.robinfriedli.jxp.collections;

import java.util.AbstractSequentialList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedList;
import java.util.List;
import java.util.ListIterator;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Consumer;
import java.util.function.Predicate;
import java.util.function.UnaryOperator;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.Node;

/**
 * A specialized {@link AbstractSequentialList} implementation that is largely based on a {@link LinkedList} where the
 * nodes are also the elements in the list. This list implementation is used to manage a collection of sibling XML nodes.
 * The implementation aims to provide thread safety by using a {@link ReentrantReadWriteLock} to apply a read or write
 * lock to most non-atomic operations. {@link #forEach(Consumer)} acquires a read lock and the list exposes the lock via
 * {@link #getLock()} to be used for regular iterations, but API methods generally return an immutable copy of this list
 * (copied via {@link #toArray()}, which also acquires a read lock).
 */
public interface NodeList extends List<Node<?>> {
    /**
     * @return a NodeList instance based on a (usually array-based) list of pre-linked Nodes (meaning the linkages of the
     * siblings already need to be set). The provided list may also be empty.
     */
    static NodeList ofLinked(List<Node<?>> nodes) {
        if (nodes.isEmpty()) {
            return new NodeListImpl(0, null, null);
        } else {
            return new NodeListImpl(nodes.size(), nodes.get(0), nodes.get(nodes.size() - 1));
        }
    }

    /**
     * @return the {@link ReentrantReadWriteLock} used by this NodeList.
     */
    ReentrantReadWriteLock getLock();

    @Override
    ListIterator<Node<?>> listIterator(int index);

    /**
     * Add the provided node as first element
     *
     * @param node the node to add
     */
    void linkFirst(Node<?> node);

    /**
     * Add the provided node as last element
     *
     * @param node the node to add
     */
    void linkLast(Node<?> node);

    /**
     * Insert the provided node ahead of the provided successor node
     *
     * @param newNode   the node to add
     * @param successor the existing node ahead of which to insert the new node
     */
    void linkBefore(Node<?> newNode, Node<?> successor);

    /**
     * Insert the provided node after the provided predecessor node
     *
     * @param newNode     the node to add
     * @param predecessor the existing node after which to insert the new node
     */
    void linkAfter(Node<?> newNode, Node<?> predecessor);

    /**
     * @return the first element of this list or null. If {@link #size()} == 1 the head element is also the tail element.
     */
    @Nullable
    Node<?> getHead();

    /**
     * @return the last element of this list or null. If {@link #size()} == 1 the head element is also the tail element.
     */
    @Nullable
    Node<?> getTail();

    // methods overridden to apply locks:

    @Override
    int size();

    @Override
    void add(int index, Node<?> element);

    @Override
    boolean addAll(int index, Collection<? extends Node<?>> c);

    @Override
    boolean addAll(Collection<? extends Node<?>> c);

    @Override
    Node<?> set(int index, Node<?> element);

    @Override
    Node<?> remove(int index);

    @Override
    boolean remove(Object o);

    @Override
    Node<?> get(int index);

    @Override
    <T> T[] toArray(T[] a);

    @Override
    Object[] toArray();

    @Override
    int indexOf(Object o);

    @Override
    int lastIndexOf(Object o);

    @Override
    void clear();

    @Override
    boolean contains(Object o);

    @Override
    boolean containsAll(Collection<?> c);

    @Override
    boolean removeAll(Collection<?> c);

    @Override
    boolean retainAll(Collection<?> c);

    @Override
    void replaceAll(UnaryOperator<Node<?>> operator);

    @Override
    void sort(Comparator<? super Node<?>> c);

    @Override
    boolean removeIf(Predicate<? super Node<?>> filter);

    /**
     * Applies an action to each element in the list and acquired a read lock before iterating and only unlocks once
     * the action has been applied to each element. IMPORTANT: because of this you may NOT perform any action that acquires
     * a write lock for this list using this method as that would cause a deadlock.
     *
     * @param action the action to perform with each element.
     */
    @Override
    void forEach(Consumer<? super Node<?>> action);
}
