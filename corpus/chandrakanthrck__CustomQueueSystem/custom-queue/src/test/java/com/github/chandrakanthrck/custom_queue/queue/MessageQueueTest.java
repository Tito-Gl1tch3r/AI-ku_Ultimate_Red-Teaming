package com.github.chandrakanthrck.custom_queue.queue;

import com.github.chandrakanthrck.custom_queue.model.Message;
import org.junit.jupiter.api.Test;

import java.util.NoSuchElementException;

import static org.junit.jupiter.api.Assertions.*;

public class MessageQueueTest {

    @Test
    public void testEnqueueDequeue() {
        MessageQueue<String> messageQueue = new MessageQueue<>();
        messageQueue.enqueue("first");
        messageQueue.enqueue("second");

        Message<String> message = messageQueue.dequeue();
        assertEquals("first", message.getContent());
        assertNotNull(message.getTimestamp());

        message = messageQueue.dequeue();
        assertEquals("second", message.getContent());
    }

    @Test
    public void testPeek() {
        MessageQueue<String> messageQueue = new MessageQueue<>();
        messageQueue.enqueue("peeked");
        Message<String> message = messageQueue.peek();
        assertEquals("peeked", message.getContent());
        assertNotNull(message.getTimestamp());

        messageQueue.dequeue();
        assertThrows(NoSuchElementException.class, messageQueue::peek);
    }

    @Test
    public void testSize() {
        MessageQueue<String> messageQueue = new MessageQueue<>();
        messageQueue.enqueue("first");
        messageQueue.enqueue("second");
        assertEquals(2, messageQueue.size());
        messageQueue.dequeue();
        assertEquals(1, messageQueue.size());
    }

    @Test
    public void testIsEmpty() {
        MessageQueue<String> messageQueue = new MessageQueue<>();
        assertTrue(messageQueue.isEmpty());
        messageQueue.enqueue("item");
        assertFalse(messageQueue.isEmpty());
        messageQueue.dequeue();
        assertTrue(messageQueue.isEmpty());
    }
}