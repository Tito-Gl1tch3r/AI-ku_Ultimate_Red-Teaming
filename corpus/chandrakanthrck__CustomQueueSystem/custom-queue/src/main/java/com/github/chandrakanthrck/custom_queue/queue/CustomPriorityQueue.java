package com.github.chandrakanthrck.custom_queue.queue;

import java.util.PriorityQueue;

public class CustomPriorityQueue<T> implements Queue<T> {
    private PriorityQueue<T> priorityQueue;

    public CustomPriorityQueue() {
        this.priorityQueue = new PriorityQueue<>();
    }

    @Override
    public void enqueue(T data) {
        priorityQueue.offer(data);
        System.out.println(data + " added to the priority queue.");
    }

    @Override
    public T dequeue() {
        T data = priorityQueue.poll();
        if (data != null) {
            System.out.println(data + " removed from the priority queue.");
        } else {
            System.out.println("Priority queue is empty.");
        }
        return data;
    }

    @Override
    public T peek() {
        return priorityQueue.peek();
    }

    @Override
    public boolean isEmpty() {
        return priorityQueue.isEmpty();
    }

    @Override
    public int size() {
        return priorityQueue.size();
    }
}