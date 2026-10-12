package com.github.chandrakanthrck.custom_queue.persistence.nosql;

import com.github.chandrakanthrck.custom_queue.model.Message;
import com.github.chandrakanthrck.custom_queue.persistence.QueuePersistence;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Profile;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;

@Profile("nosql")
@Repository
public class NoSqlQueuePersistence implements QueuePersistence {

    @Autowired
    private MongoTemplate mongoTemplate;

    @Override
    public void enqueue(Message message) {
        mongoTemplate.save(message);
    }

    @Override
    public Message dequeue() {
        List<Message> messages = mongoTemplate.findAll(Message.class);
        if (!messages.isEmpty()) {
            Message message = messages.get(0);
            mongoTemplate.remove(message);
            return message;
        }
        return null;
    }

    @Override
    public Message peek() {
        return mongoTemplate.findAll(Message.class).stream().findFirst().orElse(null);
    }

    @Override
    public boolean isEmpty() {
        return mongoTemplate.findAll(Message.class).isEmpty();
    }

    @Override
    public int size() {
        return mongoTemplate.findAll(Message.class).size();
    }
}