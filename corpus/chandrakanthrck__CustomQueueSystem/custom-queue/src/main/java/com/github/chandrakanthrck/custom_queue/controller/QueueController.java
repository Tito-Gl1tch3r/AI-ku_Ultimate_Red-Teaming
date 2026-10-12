package com.github.chandrakanthrck.custom_queue.controller;

import com.github.chandrakanthrck.custom_queue.consumer.Consumer;
import com.github.chandrakanthrck.custom_queue.model.Message;
import com.github.chandrakanthrck.custom_queue.persistence.QueuePersistence;
import com.github.chandrakanthrck.custom_queue.producer.Producer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.NoSuchElementException;

@RestController
@RequestMapping("/queue")
public class QueueController {

    private static final Logger logger = LoggerFactory.getLogger(QueueController.class);

    private final QueuePersistence queuePersistence;
    private final Producer producer;
    private final Consumer consumer;

    public QueueController(QueuePersistence queuePersistence, Producer producer, Consumer consumer) {
        this.queuePersistence = queuePersistence;
        this.producer = producer;
        this.consumer = consumer;
    }

    @PostMapping("/enqueue/{item}")
    public ResponseEntity<String> enqueue(@PathVariable String item) {
        if (item == null || item.trim().isEmpty()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body("Error: Item cannot be null or empty.");
        }
        Message message = new Message(item);
        queuePersistence.enqueue(message);
        logger.info("Enqueued item: {}", item);
        return ResponseEntity.ok(item + " has been added to the queue.");
    }

    @DeleteMapping("/dequeue")
    public ResponseEntity<String> dequeue() {
        try {
            Message message = queuePersistence.dequeue();
            logger.info("Dequeued item: {}", message.getContent());
            return ResponseEntity.ok(message.getContent() + " has been removed from the queue.");
        } catch (NoSuchElementException e) {
            logger.error("Error during dequeue: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body("Error: Queue is empty.");
        } catch (Exception e) {
            logger.error("Error during dequeue: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Error: " + e.getMessage());
        }
    }

    @GetMapping("/peek")
    public ResponseEntity<String> peek() {
        try {
            Message message = queuePersistence.peek();
            return ResponseEntity.ok("Front of the queue: " + message.getContent());
        } catch (NoSuchElementException e) {
            logger.error("Error during peek: Queue is empty.");
            return ResponseEntity.ok("Queue is empty.");  // Always return 200 OK with the message
        } catch (Exception e) {
            logger.error("Error during peek: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Error: " + e.getMessage());
        }
    }

    @GetMapping("/size")
    public ResponseEntity<String> getSize() {
        return ResponseEntity.ok("Current queue size: " + queuePersistence.size());
    }

    @GetMapping("/isEmpty")
    public ResponseEntity<String> isEmpty() {
        return ResponseEntity.ok("Is the queue empty? " + queuePersistence.isEmpty());
    }

    @PostMapping("/produce")
    public ResponseEntity<String> produce() throws InterruptedException {
        producer.produce();
        logger.info("Produced an item to the queue.");
        return ResponseEntity.ok("Produced an item to the queue.");
    }

    @DeleteMapping("/consume")
    public ResponseEntity<String> consume() throws InterruptedException {
        consumer.consume();
        logger.info("Consumer has consumed an item from the queue.");
        return ResponseEntity.ok("Consumer has consumed an item from the queue.");
    }
}