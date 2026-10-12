package com.github.chandrakanthrck.custom_queue.persistence.sql;

import com.github.chandrakanthrck.custom_queue.model.Message;
import com.github.chandrakanthrck.custom_queue.persistence.QueuePersistence;
import jakarta.persistence.EntityManager;
import jakarta.transaction.Transactional;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Repository;

import java.util.List;

@Profile("sql")
@Repository
@Transactional
public class SqlQueuePersistence implements QueuePersistence {

    @Autowired
    private EntityManager entityManager;

    @Override
    public void enqueue(Message message) {
        entityManager.persist(message);
    }

    @Override
    public Message dequeue() {
        List<Message> messages = entityManager.createQuery("SELECT m FROM Message m ORDER BY m.timestamp", Message.class)
                .setMaxResults(1).getResultList();
        if (!messages.isEmpty()) {
            Message message = messages.get(0);
            entityManager.remove(message);
            return message;
        }
        return null;
    }

    @Override
    public Message peek() {
        return entityManager.createQuery("SELECT m FROM Message m ORDER BY m.timestamp", Message.class)
                .setMaxResults(1).getSingleResult();
    }

    @Override
    public boolean isEmpty() {
        return entityManager.createQuery("SELECT COUNT(m) FROM Message m", Long.class).getSingleResult() == 0;
    }

    @Override
    public int size() {
        return entityManager.createQuery("SELECT COUNT(m) FROM Message m", Long.class).getSingleResult().intValue();
    }
}
