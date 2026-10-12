
package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.PrivateCustomer;
import ch.hearc.ig.orderresto.business.Order;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.mappers.OrderMapper;
import ch.hearc.ig.orderresto.service.exceptions.OrderServiceException;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;
import org.junit.jupiter.api.*;
import org.mockito.Mockito;

import java.sql.Connection;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class OrderServiceTests {

    private OrderService orderService;
    private OrderMapper orderMapperMock;
    private TransactionHandler transactionHandlerMock;

    @BeforeEach
    public void setUp() {
        orderMapperMock = Mockito.mock(OrderMapper.class);
        transactionHandlerMock = Mockito.mock(TransactionHandler.class);
        orderService = new OrderService(orderMapperMock, transactionHandlerMock);
    }

    @Test
    public void testCreateOrder() throws Exception {
        PrivateCustomer customer = new PrivateCustomer(1L, "123456789", "test@example.com", null, "N", "John", "Doe");
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = orderService.createOrder(order);
            assertTrue(result, "Order should be created successfully");
        });
    }

    @Test
    public void testCreateOrderWithSQLException() throws Exception {
        PrivateCustomer customer = new PrivateCustomer(1L, "123456789", "test@example.com", null, "N", "John", "Doe");
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());

        doThrow(new SQLException("Simulated SQL exception")).when(orderMapperMock).insert(any(Order.class), any(Connection.class));

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        OrderServiceException exception = assertThrows(OrderServiceException.class, () -> {
            orderService.createOrder(order);
        });

        assertEquals("Failed to create order", exception.getMessage());
    }

    @Test
    public void testGetOrderById() throws Exception {
        Order order = new Order(1L, null, null, false, LocalDateTime.now());
        when(orderMapperMock.read(anyLong(), any(Connection.class))).thenReturn(order);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            return action.execute(Mockito.mock(Connection.class));
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        Order retrievedOrder = orderService.getOrderById(1L);
        assertNotNull(retrievedOrder, "Order should be retrieved successfully");
        assertEquals(1L, retrievedOrder.getId(), "Order ID should match");
    }

    @Test
    public void testUpdateOrder() throws Exception {
        PrivateCustomer customer = new PrivateCustomer(1L, "123456789", "test@example.com", null, "N", "Jane", "Doe");
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Order order = new Order(1L, customer, restaurant, false, LocalDateTime.now()); // Initialiser tous les champs

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = orderService.updateOrder(order);
            assertTrue(result, "Order should be updated successfully");
        });
    }

    @Test
    public void testDeleteOrder() throws Exception {
        Order order = new Order(1L, null, null, false, LocalDateTime.now());

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = orderService.deleteOrder(order);
            assertTrue(result, "Order should be deleted successfully");
        });
    }

    @Test
    public void testFindOrdersByCustomer() throws Exception {
        PrivateCustomer customer = new PrivateCustomer(1L, "123456789", "test@example.com", null, "N", "John", "Doe");
        List<Order> orders = List.of(new Order(1L, customer, null, false, LocalDateTime.now()));
        when(orderMapperMock.findOrdersByCustomer(any(PrivateCustomer.class), any(Connection.class))).thenReturn(orders);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            return action.execute(Mockito.mock(Connection.class));
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        List<Order> retrievedOrders = orderService.findOrdersByCustomer(customer);
        assertNotNull(retrievedOrders, "Orders should be retrieved successfully");
        assertEquals(1, retrievedOrders.size(), "There should be one order retrieved");
    }
}
