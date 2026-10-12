package com.github.chandrakanthrck.custom_queue.queue;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class CustomPriorityQueueTest {

    @Test
    public void testEnqueueDequeue() {
        CustomPriorityQueue<String> queue = new CustomPriorityQueue<>();
        queue.enqueue("second");
        queue.enqueue("first");
        assertEquals("first", queue.dequeue()); // PriorityQueue should order based on natural ordering
        assertEquals("second", queue.dequeue());
        assertTrue(queue.isEmpty());
    }

    @Test
    public void testPeek() {
        CustomPriorityQueue<String> queue = new CustomPriorityQueue<>();
        queue.enqueue("peeked");
        assertEquals("peeked", queue.peek());
        queue.dequeue();
        assertNull(queue.peek());
    }

    @Test
    public void testSize() {
        CustomPriorityQueue<String> queue = new CustomPriorityQueue<>();
        queue.enqueue("first");
        queue.enqueue("second");
        assertEquals(2, queue.size());
        queue.dequeue();
        assertEquals(1, queue.size());
    }

    @Test
    public void testIsEmpty() {
        CustomPriorityQueue<String> queue = new CustomPriorityQueue<>();
        assertTrue(queue.isEmpty());
        queue.enqueue("item");
        assertFalse(queue.isEmpty());
        queue.dequeue();
        assertTrue(queue.isEmpty());
    }
}
