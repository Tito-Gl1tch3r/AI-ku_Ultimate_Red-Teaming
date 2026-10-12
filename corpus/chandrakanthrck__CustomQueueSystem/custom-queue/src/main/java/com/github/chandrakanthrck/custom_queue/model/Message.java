package com.github.chandrakanthrck.custom_queue.model;

import java.io.Serializable;
import java.util.UUID;

public class Message<T> implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String id;
    private final T content;
    private final long timestamp;

    public Message(T content) {
        this.id = UUID.randomUUID().toString(); // Unique ID for each message
        this.content = content;
        this.timestamp = System.currentTimeMillis();
    }

    public String getId() {
        return id;
    }

    public T getContent() {
        return content;
    }

    public long getTimestamp() {
        return timestamp;
    }

    @Override
    public String toString() {
        return "Message{" +
                "id='" + id + '\'' +
                ", content=" + content +
                ", timestamp=" + timestamp +
                '}';
    }
}