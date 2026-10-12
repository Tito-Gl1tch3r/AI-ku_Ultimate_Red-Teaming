package net.robinfriedli.jxp.collections;

import java.util.AbstractSequentialList;
import java.util.Collection;
import java.util.Comparator;
import java.util.ConcurrentModificationException;
import java.util.ListIterator;
import java.util.NoSuchElementException;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Consumer;
import java.util.function.Predicate;
import java.util.function.UnaryOperator;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.Node;


public class NodeListImpl extends AbstractSequentialList<Node<?>> implements NodeList {

    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    private int size;
    private int modCount;

    private Node<?> head;
    private Node<?> tail;

    public NodeListImpl(int size, Node<?> head, Node<?> tail) {
        this.size = size;
        this.modCount = 0;
        this.head = head;
        this.tail = tail;
    }

    @Override
    public ReentrantReadWriteLock getLock() {
        return lock;
    }

    @Override
    public ListIterator<Node<?>> listIterator(int index) {
        return new ListIteratorImpl(index);
    }

    @Override
    public int size() {
        return size;
    }

    @Override
    public void add(int index, Node<?> element) {
        lock.writeLock().lock();
        try {
            super.add(index, element);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public boolean addAll(int index, Collection<? extends Node<?>> c) {
        lock.writeLock().lock();
        try {
            return super.addAll(index, c);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public boolean addAll(Collection<? extends Node<?>> c) {
        lock.writeLock().lock();
        try {
            return super.addAll(c);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public Node<?> set(int index, Node<?> element) {
        lock.writeLock().lock();
        try {
            return super.set(index, element);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public Node<?> remove(int index) {
        lock.writeLock().lock();
        try {
            return super.remove(index);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public boolean remove(Object o) {
        lock.writeLock().lock();
        try {
            return super.remove(o);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public Node<?> get(int index) {
        lock.readLock().lock();
        try {
            return super.get(index);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public <T> T[] toArray(T[] a) {
        lock.readLock().lock();
        try {
            return super.toArray(a);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public Object[] toArray() {
        lock.readLock().lock();
        try {
            return super.toArray();
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public int indexOf(Object o) {
        lock.readLock().lock();
        try {
            return super.indexOf(o);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public int lastIndexOf(Object o) {
        lock.readLock().lock();
        try {
            return super.lastIndexOf(o);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public void clear() {
        lock.writeLock().lock();
        try {
            super.clear();
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public boolean contains(Object o) {
        lock.readLock().lock();
        try {
            return super.contains(o);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public boolean containsAll(Collection<?> c) {
        lock.readLock().lock();
        try {
            return super.containsAll(c);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public boolean removeAll(Collection<?> c) {
        lock.writeLock().lock();
        try {
            return super.removeAll(c);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public boolean retainAll(Collection<?> c) {
        lock.writeLock().lock();
        try {
            return super.retainAll(c);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public void replaceAll(UnaryOperator<Node<?>> operator) {
        lock.writeLock().lock();
        try {
            super.replaceAll(operator);
        } finally {
            lock.writeLock().lock();
        }
    }

    @Override
    public void sort(Comparator<? super Node<?>> c) {
        lock.writeLock().lock();
        try {
            super.sort(c);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public boolean removeIf(Predicate<? super Node<?>> filter) {
        lock.writeLock().lock();
        try {
            return super.removeIf(filter);
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public void forEach(Consumer<? super Node<?>> action) {
        lock.readLock().lock();
        try {
            super.forEach(action);
        } finally {
            lock.readLock().unlock();
        }
    }

    @Override
    public void linkFirst(Node<?> node) {
        lock.writeLock().lock();
        try {
            Node<?> h = head;
            node.internal().setNextSibling(h);
            head = node;

            if (h == null) {
                tail = node;
            } else {
                h.internal().removePreviousSibling();
                h.internal().setPreviousSibling(node);
            }

            size++;
            modCount++;
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public void linkLast(Node<?> node) {
        lock.writeLock().lock();
        try {
            Node<?> t = tail;
            node.internal().setPreviousSibling(t);
            tail = node;

            if (t == null) {
                head = node;
            } else {
                t.internal().removeNextSibling();
                t.internal().setNextSibling(node);
            }

            size++;
            modCount++;
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public void linkBefore(Node<?> newNode, Node<?> successor) {
        lock.writeLock().lock();
        try {
            Node<?> previousSibling = successor.getPreviousSibling();
            newNode.internal().setPreviousSibling(previousSibling);
            newNode.internal().setNextSibling(successor);
            successor.internal().removePreviousSibling();
            successor.internal().setPreviousSibling(newNode);

            if (previousSibling == null) {
                head = newNode;
            } else {
                previousSibling.internal().removeNextSibling();
                previousSibling.internal().setNextSibling(newNode);
            }

            size++;
            modCount++;
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    public void linkAfter(Node<?> newNode, Node<?> predecessor) {
        lock.writeLock().lock();
        try {
            Node<?> nextSibling = predecessor.getNextSibling();
            newNode.internal().setNextSibling(nextSibling);
            newNode.internal().setPreviousSibling(predecessor);
            predecessor.internal().removeNextSibling();
            predecessor.internal().setNextSibling(newNode);

            if (nextSibling == null) {
                tail = newNode;
            } else {
                nextSibling.internal().removePreviousSibling();
                nextSibling.internal().setPreviousSibling(newNode);
            }

            size++;
            modCount++;
        } finally {
            lock.writeLock().unlock();
        }
    }

    @Override
    @Nullable
    public Node<?> getHead() {
        return head;
    }

    @Override
    @Nullable
    public Node<?> getTail() {
        return tail;
    }

    Node<?> nodeAt(int index) {
        if (index >= size) {
            throw new IndexOutOfBoundsException(String.format("Index %s out of bounds for size %s", index, this.size));
        }

        lock.readLock().lock();
        try {
            Node<?> current;
            if (index < (size >> 1)) {
                current = head;
                for (int i = 0; i < index; i++) {
                    //noinspection ConstantConditions
                    current = current.getNextSibling();
                }
            } else {
                current = tail;
                for (int i = size - 1; i > index; i--) {
                    current = tail.getPreviousSibling();
                }
            }
            return current;
        } finally {
            lock.readLock().unlock();
        }
    }

    void unlink(Node<?> toUnlink) {
        lock.writeLock().lock();
        try {
            Node<?> nextSibling = toUnlink.getNextSibling();
            Node<?> previousSibling = toUnlink.getPreviousSibling();

            if (previousSibling == null) {
                head = nextSibling;
            } else {
                previousSibling.internal().removeNextSibling();
                previousSibling.internal().setNextSibling(nextSibling);
                toUnlink.internal().removePreviousSibling();
            }

            if (nextSibling == null) {
                tail = previousSibling;
            } else {
                nextSibling.internal().removePreviousSibling();
                nextSibling.internal().setPreviousSibling(previousSibling);
                toUnlink.internal().removeNextSibling();
            }

            size--;
            modCount++;
        } finally {
            lock.writeLock().unlock();
        }
    }

    void swap(Node<?> toUnlink, Node<?> toLink) {
        lock.writeLock().lock();
        try {
            Node<?> nextSibling = toUnlink.getNextSibling();
            Node<?> previousSibling = toUnlink.getPreviousSibling();

            if (previousSibling == null) {
                head = toLink;
                // do not use removePreviousSibling as this call SHOULD fail if the insertion node already has a previous sibling defined
                toLink.internal().setPreviousSibling(null);
            } else {
                previousSibling.internal().removeNextSibling();
                previousSibling.internal().setNextSibling(toLink);
                toLink.internal().setPreviousSibling(previousSibling);
                toUnlink.internal().removePreviousSibling();
            }

            if (nextSibling == null) {
                tail = toLink;
                toLink.internal().setNextSibling(null);
            } else {
                nextSibling.internal().removePreviousSibling();
                nextSibling.internal().setPreviousSibling(toLink);
                toLink.internal().setNextSibling(nextSibling);
                toUnlink.internal().removeNextSibling();
            }

            modCount++;
        } finally {
            lock.writeLock().unlock();
        }
    }

    private class ListIteratorImpl implements ListIterator<Node<?>> {

        private int nextIndex;
        private Node<?> lastReturned;
        private Node<?> next;

        private int expectedModCount = modCount;

        ListIteratorImpl(int index) {
            nextIndex = index;
            next = index < size ? nodeAt(index) : null;
        }

        @Override
        public boolean hasNext() {
            return nextIndex < size;
        }

        @Override
        public Node<?> next() {
            checkConcurrentModification();

            if (!hasNext()) {
                throw new NoSuchElementException();
            }

            lastReturned = next;
            next = next.getNextSibling();
            nextIndex++;

            return lastReturned;
        }

        @Override
        public boolean hasPrevious() {
            return nextIndex > 0;
        }

        @Override
        public Node<?> previous() {
            checkConcurrentModification();

            if (!hasPrevious()) {
                throw new NoSuchElementException();
            }

            nextIndex--;
            return lastReturned = next = (next == null) ? tail : next.getPreviousSibling();
        }

        @Override
        public int nextIndex() {
            return nextIndex;
        }

        @Override
        public int previousIndex() {
            return nextIndex - 1;
        }

        @Override
        public void remove() {
            checkConcurrentModification();
            if (lastReturned == null) {
                throw new IllegalStateException();
            }

            Node<?> nextSibling = lastReturned.getNextSibling();
            unlink(lastReturned);

            if (next == lastReturned) {
                next = nextSibling;
            } else {
                nextIndex--;
            }

            lastReturned = null;
            expectedModCount++;
        }

        @Override
        public void set(Node<?> node) {
            if (lastReturned == null) {
                throw new IllegalStateException();
            }

            checkConcurrentModification();
            swap(lastReturned, node);
            lastReturned = node;
            expectedModCount++;
        }

        @Override
        public void add(Node<?> node) {
            checkConcurrentModification();
            lastReturned = null;

            if (next == null) {
                linkLast(node);
            } else {
                linkBefore(node, next);
            }

            nextIndex++;
            expectedModCount++;
        }

        @Override
        public void forEachRemaining(Consumer<? super Node<?>> action) {
            while (modCount == expectedModCount && nextIndex < size) {
                action.accept(next);
                lastReturned = next;
                next = next.getNextSibling();
                nextIndex++;
            }
            checkConcurrentModification();
        }

        private void checkConcurrentModification() {
            if (expectedModCount != modCount) {
                throw new ConcurrentModificationException();
            }
        }
    }

}
