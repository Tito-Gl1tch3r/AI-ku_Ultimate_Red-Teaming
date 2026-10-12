package com.github.chandrakanthrck.custom_queue.producer;

import com.github.chandrakanthrck.custom_queue.model.Message;
import com.github.chandrakanthrck.custom_queue.persistence.QueuePersistence;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class Producer {

    private final QueuePersistence queuePersistence;

    public Producer(QueuePersistence queuePersistence) {
        this.queuePersistence = queuePersistence;
    }

    // Produces a message every 5 seconds.
    @Scheduled(fixedRate = 5000)
    public void produce() throws InterruptedException {
        String messageContent = "Message-" + System.currentTimeMillis();
        Message message = new Message(messageContent);
        queuePersistence.enqueue(message);
        System.out.println("Produced: " + message.getContent());
    }
}