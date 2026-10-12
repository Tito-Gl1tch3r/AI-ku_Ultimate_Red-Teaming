package com.github.chandrakanthrck.custom_queue.queue;

import java.util.NoSuchElementException;

public class FixedSizeQueue<T> implements Queue<T> {
    private Object[] elements;
    private int front, rear, size, capacity;

    public FixedSizeQueue(int capacity) {
        this.capacity = capacity;
        this.elements = new Object[capacity];
        this.front = 0;
        this.rear = 0;
        this.size = 0;
    }

    @Override
    public void enqueue(T data) {
        if (size == capacity) {
            throw new IllegalStateException("Queue is full. Cannot enqueue.");
        }
        elements[rear] = data;
        rear = (rear + 1) % capacity;
        size++;
        System.out.println(data + " enqueued to the fixed-size queue.");
    }

    @Override
    public T dequeue() {
        if (isEmpty()) {
            throw new NoSuchElementException("Queue is empty. Cannot dequeue.");
        }
        T data = (T) elements[front];
        front = (front + 1) % capacity;
        size--;
        System.out.println(data + " dequeued from the fixed-size queue.");
        return data;
    }

    @Override
    public T peek() {
        if (isEmpty()) {
            throw new NoSuchElementException("Queue is empty. Cannot peek.");
        }
        return (T) elements[front];
    }

    @Override
    public boolean isEmpty() {
        return size == 0;
    }

    @Override
    public int size() {
        return size;
    }
}