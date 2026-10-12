package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.business.Order;
import ch.hearc.ig.orderresto.persistence.mappers.OrderMapper;
import ch.hearc.ig.orderresto.service.exceptions.OrderServiceException;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;

import java.util.List;

public class OrderService {
    private final OrderMapper orderMapper;
    private final TransactionHandler transactionHandler;

    public OrderService() {
        this.orderMapper = new OrderMapper();
        this.transactionHandler = new TransactionHandler();
    }

    public OrderService(OrderMapper orderMapper, TransactionHandler transactionHandler) {
        this.orderMapper = orderMapper;
        this.transactionHandler = transactionHandler;
    }

    public boolean createOrder(Order order) throws OrderServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                orderMapper.insert(order, conn);
                return null;
            });
            return true;
        } catch (Exception e) {
            throw new OrderServiceException("Failed to create order", e);
        }
    }

    public List<Order> findOrdersByCustomer(Customer customer) throws OrderServiceException {
        try {
            return transactionHandler.executeInTransaction(conn -> orderMapper.findOrdersByCustomer(customer, conn));
        } catch (Exception e) {
            throw new OrderServiceException("Failed to find orders by customer", e);
        }
    }

    public Order getOrderById(Long id) throws OrderServiceException {
        try {
            return transactionHandler.executeInTransaction(conn -> orderMapper.read(id, conn));
        } catch (Exception e) {
            throw new OrderServiceException("Failed to get order by id", e);
        }
    }

    @Deprecated
    public List<Order> getAllOrders() {
        try {
            return transactionHandler.executeInTransaction(orderMapper::findAll);
        } catch (Exception e) {
            System.err.println("Error while finding orders: " + e.getMessage());
            return null;
        }
    }

    public boolean updateOrder(Order order) throws OrderServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                orderMapper.update(order, conn);
                return null; // Void equivalent
            });
            System.out.println("Order updated successfully!");
            return true;
        } catch (Exception e) {
            throw new OrderServiceException("Failed to update order", e);
        }
    }

    public boolean deleteOrder(Order order) throws OrderServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                orderMapper.delete(order.getId(), conn);
                return null; // Void equivalent
            });
            System.out.println("Order deleted successfully!");
            return true;
        } catch (Exception e) {
            throw new OrderServiceException("Failed to delete order", e);
        }
    }
}