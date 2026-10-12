package com.github.chandrakanthrck.custom_queue.consumer;

import com.github.chandrakanthrck.custom_queue.model.Message;
import com.github.chandrakanthrck.custom_queue.persistence.QueuePersistence;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class Consumer {

    private final QueuePersistence queuePersistence;

    public Consumer(QueuePersistence queuePersistence) {
        this.queuePersistence = queuePersistence;
    }

    // Consumes a message every 7 seconds
    @Scheduled(fixedRate = 7000)
    public void consume() throws InterruptedException {
        if (!queuePersistence.isEmpty()) {
            Message message = queuePersistence.dequeue();
            System.out.println("Consumed: " + message.getContent());
        } else {
            System.out.println("Queue is empty, no message to consume.");
        }
    }
}
