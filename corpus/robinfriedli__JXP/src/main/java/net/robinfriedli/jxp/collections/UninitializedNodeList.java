package net.robinfriedli.jxp.collections;

import java.util.Collection;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.ListIterator;
import java.util.Set;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Consumer;
import java.util.function.Predicate;
import java.util.function.UnaryOperator;

import javax.annotation.Nullable;

import com.google.common.collect.Sets;
import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.api.StaticXmlElementFactory;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Element;

public class UninitializedNodeList implements NodeList {

    private final Context context;
    private final Element parentElement;

    private volatile NodeList initialized;
    private volatile XmlElement parent;

    public UninitializedNodeList(Context context, Element parentElement) {
        this.context = context;
        this.parentElement = parentElement;
    }

    public void setParent(XmlElement parent) {
        this.parent = parent;
    }

    public synchronized NodeList initialize(boolean initializeSubElements, Set<? extends Node<?>> preInitialized) {
        if (initialized != null) {
            // recheck if other thread initialized
            return initialized;
        }
        initialized = StaticXmlElementFactory.instantiateChildrenOf(parentElement, context, initializeSubElements, preInitialized);
        if (parent != null) {
            initialized.forEach(node -> {
                if (node instanceof XmlElement && preInitialized.contains(node)) {
                    return;
                }
                node.internal().setParent(parent);
            });
        }
        return initialized;
    }

    private NodeList initialize() {
        return initialize(false, Sets.newHashSet());
    }

    public boolean isInitialized() {
        return initialized != null;
    }

    private NodeList getInitialized() {
        if (initialized == null) {
            return initialize();
        }

        return initialized;
    }

    @Override
    public ReentrantReadWriteLock getLock() {
        return getInitialized().getLock();
    }

    @Override
    public ListIterator<Node<?>> listIterator(int index) {
        return getInitialized().listIterator(index);
    }

    @Override
    public List<Node<?>> subList(int fromIndex, int toIndex) {
        return getInitialized().subList(fromIndex, toIndex);
    }

    @Override
    public int size() {
        return getInitialized().size();
    }

    @Override
    public boolean isEmpty() {
        return getInitialized().isEmpty();
    }

    @Override
    public void add(int index, Node<?> element) {
        getInitialized().add(index, element);
    }

    @Override
    public boolean addAll(int index, Collection<? extends Node<?>> c) {
        return getInitialized().addAll(index, c);
    }

    @Override
    public boolean addAll(Collection<? extends Node<?>> c) {
        return getInitialized().addAll(c);
    }

    @Override
    public Node<?> set(int index, Node<?> element) {
        return getInitialized().set(index, element);
    }

    @Override
    public Node<?> remove(int index) {
        return getInitialized().remove(index);
    }

    @Override
    public boolean remove(Object o) {
        return getInitialized().remove(o);
    }

    @Override
    public Node<?> get(int index) {
        return getInitialized().get(index);
    }

    @Override
    public <T> T[] toArray(T[] a) {
        return getInitialized().toArray(a);
    }

    @Override
    public boolean add(Node<?> node) {
        return getInitialized().add(node);
    }

    @Override
    public Object[] toArray() {
        return getInitialized().toArray();
    }

    @Override
    public int indexOf(Object o) {
        return getInitialized().indexOf(o);
    }

    @Override
    public int lastIndexOf(Object o) {
        return getInitialized().lastIndexOf(o);
    }

    @Override
    public ListIterator<Node<?>> listIterator() {
        return getInitialized().listIterator();
    }

    @Override
    public void clear() {
        getInitialized().clear();
    }

    @Override
    public boolean contains(Object o) {
        return getInitialized().contains(o);
    }

    @Override
    public Iterator<Node<?>> iterator() {
        return getInitialized().iterator();
    }

    @Override
    public boolean containsAll(Collection<?> c) {
        return getInitialized().containsAll(c);
    }

    @Override
    public boolean removeAll(Collection<?> c) {
        return getInitialized().removeAll(c);
    }

    @Override
    public boolean retainAll(Collection<?> c) {
        return getInitialized().retainAll(c);
    }

    @Override
    public void replaceAll(UnaryOperator<Node<?>> operator) {
        getInitialized().replaceAll(operator);
    }

    @Override
    public void sort(Comparator<? super Node<?>> c) {
        getInitialized().sort(c);
    }

    @Override
    public boolean removeIf(Predicate<? super Node<?>> filter) {
        return getInitialized().removeIf(filter);
    }

    @Override
    public void forEach(Consumer<? super Node<?>> action) {
        getInitialized().forEach(action);
    }

    @Override
    public void linkFirst(Node<?> node) {
        getInitialized().linkFirst(node);
    }

    @Override
    public void linkLast(Node<?> node) {
        getInitialized().linkLast(node);
    }

    @Override
    public void linkBefore(Node<?> newNode, Node<?> successor) {
        getInitialized().linkBefore(newNode, successor);
    }

    @Override
    public void linkAfter(Node<?> newNode, Node<?> predecessor) {
        getInitialized().linkAfter(newNode, predecessor);
    }

    @Nullable
    @Override
    public Node<?> getHead() {
        return getInitialized().getHead();
    }

    @Nullable
    @Override
    public Node<?> getTail() {
        return getInitialized().getTail();
    }
}
