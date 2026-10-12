package com.github.chandrakanthrck.custom_queue.queue;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.NoSuchElementException;

public class FixedSizeQueueTest {

    @Test
    public void testEnqueueDequeue() {
        FixedSizeQueue<String> queue = new FixedSizeQueue<>(2);
        queue.enqueue("first");
        queue.enqueue("second");
        assertEquals("first", queue.dequeue());
        assertEquals("second", queue.dequeue());
        assertTrue(queue.isEmpty());
    }

    @Test
    public void testEnqueueFullQueue() {
        FixedSizeQueue<String> queue = new FixedSizeQueue<>(2);
        queue.enqueue("first");
        queue.enqueue("second");
        assertThrows(IllegalStateException.class, () -> queue.enqueue("third"));
    }

    @Test
    public void testPeek() {
        FixedSizeQueue<String> queue = new FixedSizeQueue<>(2);
        queue.enqueue("peeked");
        assertEquals("peeked", queue.peek());
        queue.dequeue();
        assertThrows(NoSuchElementException.class, queue::peek);
    }

    @Test
    public void testSize() {
        FixedSizeQueue<String> queue = new FixedSizeQueue<>(2);
        queue.enqueue("first");
        queue.enqueue("second");
        assertEquals(2, queue.size());
        queue.dequeue();
        assertEquals(1, queue.size());
    }

    @Test
    public void testIsEmpty() {
        FixedSizeQueue<String> queue = new FixedSizeQueue<>(2);
        assertTrue(queue.isEmpty());
        queue.enqueue("item");
        assertFalse(queue.isEmpty());
        queue.dequeue();
        assertTrue(queue.isEmpty());
    }
}
