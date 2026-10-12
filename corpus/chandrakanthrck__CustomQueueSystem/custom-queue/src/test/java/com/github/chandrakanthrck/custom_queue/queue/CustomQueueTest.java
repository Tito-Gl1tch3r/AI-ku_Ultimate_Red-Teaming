package com.github.chandrakanthrck.custom_queue.queue;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.NoSuchElementException;

public class CustomQueueTest {

    @Test
    public void testEnqueueDequeue() {
        CustomQueue<String> queue = new CustomQueue<>();
        queue.enqueue("first");
        queue.enqueue("second");
        assertEquals("first", queue.dequeue());
        assertEquals("second", queue.dequeue());
        assertTrue(queue.isEmpty());
    }

    @Test
    public void testPeek() {
        CustomQueue<String> queue = new CustomQueue<>();
        queue.enqueue("peeked");
        assertEquals("peeked", queue.peek());
        queue.dequeue();
        assertThrows(NoSuchElementException.class, queue::peek);
    }

    @Test
    public void testSize() {
        CustomQueue<String> queue = new CustomQueue<>();
        queue.enqueue("first");
        queue.enqueue("second");
        assertEquals(2, queue.size());
        queue.dequeue();
        assertEquals(1, queue.size());
    }

    @Test
    public void testIsEmpty() {
        CustomQueue<String> queue = new CustomQueue<>();
        assertTrue(queue.isEmpty());
        queue.enqueue("item");
        assertFalse(queue.isEmpty());
        queue.dequeue();
        assertTrue(queue.isEmpty());
    }
}