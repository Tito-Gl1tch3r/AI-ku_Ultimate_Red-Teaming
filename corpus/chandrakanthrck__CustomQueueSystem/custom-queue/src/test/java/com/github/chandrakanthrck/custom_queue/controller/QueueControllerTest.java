package com.github.chandrakanthrck.custom_queue.controller;

import com.github.chandrakanthrck.custom_queue.model.Message;
import com.github.chandrakanthrck.custom_queue.persistence.QueuePersistence;
import com.github.chandrakanthrck.custom_queue.consumer.Consumer;
import com.github.chandrakanthrck.custom_queue.producer.Producer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockitoAnnotations;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.NoSuchElementException;

import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(QueueController.class)
public class QueueControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private QueuePersistence queuePersistence;

    @MockBean
    private Producer producer;

    @MockBean
    private Consumer consumer;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this); // Initialize mocks
    }

    @Test
    public void testEnqueueAndCheckSizeDynamically() throws Exception {
        // Before enqueue, the queue size is 0
        when(queuePersistence.size()).thenReturn(0);
        mockMvc.perform(get("/queue/size")
                        .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(content().string("Current queue size: 0"));

        // After enqueuing an item, mock the size to increase dynamically
        doAnswer(invocation -> {
            when(queuePersistence.size()).thenReturn(1);  // Enqueue an item
            return null;
        }).when(queuePersistence).enqueue(any(Message.class));

        mockMvc.perform(post("/queue/enqueue/{item}", "testItem")
                        .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(content().string("testItem has been added to the queue."));

        // Verify that the queue size has increased after enqueueing
        mockMvc.perform(get("/queue/size")
                        .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(content().string("Current queue size: 1"));
    }

    @Test
    public void testDequeueAndCheckEmptyStateDynamically() throws Exception {
        // Initially, the queue has 1 item
        when(queuePersistence.size()).thenReturn(1);
        when(queuePersistence.isEmpty()).thenReturn(false);

        // Mock dequeue behavior to remove the last item and make the queue empty
        doAnswer(invocation -> {
            when(queuePersistence.size()).thenReturn(0);  // After dequeue, the queue size is 0
            when(queuePersistence.isEmpty()).thenReturn(true);  // Queue becomes empty
            return new Message("testItem");
        }).when(queuePersistence).dequeue();

        // Perform dequeue operation
        mockMvc.perform(delete("/queue/dequeue")
                        .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(content().string("testItem has been removed from the queue."));

        // Check if the queue is empty after dequeueing the item
        mockMvc.perform(get("/queue/isEmpty")
                        .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(content().string("Is the queue empty? true"));
    }

    @Test
    public void testPeekQueueDynamically() throws Exception {
        when(queuePersistence.peek()).thenThrow(new NoSuchElementException("Queue is empty"));

        mockMvc.perform(get("/queue/peek")
                        .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())  // Expect 200 status instead of 404
                .andExpect(content().string("Queue is empty."));  // Expect "Queue is empty." message
    }
}