package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.business.*;
import ch.hearc.ig.orderresto.business.Order;
import ch.hearc.ig.orderresto.persistence.exceptions.CustomerPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.OrderPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.service.utils.ConnectionManager;
import org.junit.jupiter.api.*;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

public class OrderMapperTests {

    private static Connection conn;
    private OrderMapper orderMapper;
    private CustomerMapper customerMapper;
    private RestaurantMapper restaurantMapper;
    private ProductMapper productMapper;

    @BeforeAll
    public static void setUpClass() throws SQLException {
        conn = ConnectionManager.getConnection();
        conn.setAutoCommit(false);
    }

    @BeforeEach
    public void setUp() {
        orderMapper = new OrderMapper();
        customerMapper = new CustomerMapper();
        restaurantMapper = new RestaurantMapper();
        productMapper = new ProductMapper();
    }

    @AfterEach
    public void tearDown() {
        try {
            conn.rollback();
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }

    @AfterAll
    public static void tearDownClass() {
        try {
            conn.close();
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }

    @Test
    public void testInsertOrder() throws SQLException, OrderPersistenceException, ProductPersistenceException, RestaurantPersistenceException, CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "123456789", "order@test.com", address, "O", "John", "Doe");
        customerMapper.insert(customer, conn);

        Restaurant restaurant = new Restaurant(null, "Test Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product = new Product(null, "Pizza", new BigDecimal("18.00"), "Delicious pizza", restaurant);
        productMapper.insert(product, conn);

        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());
        order.addProduct(product);

        // Act & Assert
        assertDoesNotThrow(() -> orderMapper.insert(order, conn));
        assertNotNull(order.getId(), "Order ID should be generated and set");
    }

    @Test
    public void testReadOrder() throws SQLException, OrderPersistenceException, CustomerPersistenceException, RestaurantPersistenceException, ProductPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "987654321", "readorder@test.com", address, "N", "Jane", "Smith");
        customerMapper.insert(customer, conn);

        Restaurant restaurant = new Restaurant(null, "Read Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product = new Product(null, "Burger", new BigDecimal("12.00"), "Tasty burger", restaurant);
        productMapper.insert(product, conn);

        Order order = new Order(null, customer, restaurant, true, LocalDateTime.now());
        order.addProduct(product);
        orderMapper.insert(order, conn);

        // Act
        Order readOrder = orderMapper.read(order.getId(), conn);

        // Assert
        assertNotNull(readOrder, "Order should be retrievable by ID");
        assertEquals(order.getId(), readOrder.getId(), "Order ID should match");
        assertEquals(order.getCustomer().getId(), readOrder.getCustomer().getId(), "Customer ID should match");
    }

    @Test
    public void testDeleteOrder() throws SQLException, OrderPersistenceException, CustomerPersistenceException, RestaurantPersistenceException, ProductPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "123123123", "deleteorder@test.com", address, "O", "Alice", "Wonder");
        customerMapper.insert(customer, conn);

        Restaurant restaurant = new Restaurant(null, "Delete Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product = new Product(null, "Pasta", new BigDecimal("10.00"), "Delicious pasta", restaurant);
        productMapper.insert(product, conn);

        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());
        order.addProduct(product);
        orderMapper.insert(order, conn);

        // Act & Assert
        assertDoesNotThrow(() -> orderMapper.delete(order.getId(), conn));
        Order deletedOrder = orderMapper.read(order.getId(), conn);
        assertNull(deletedOrder, "Order should no longer be retrievable after deletion");
    }

    @Test
    public void testFindOrdersByCustomer() throws SQLException, OrderPersistenceException, CustomerPersistenceException, RestaurantPersistenceException, ProductPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "555555555", "findorders@test.com", address, "N", "Bob", "Builder");
        customerMapper.insert(customer, conn);
        System.out.println("Customer inserted: " + customer.getId());

        Restaurant restaurant = new Restaurant(null, "FindOrders Resto", address);
        restaurantMapper.insert(restaurant, conn);
        System.out.println("Restaurant inserted: " + restaurant.getId());

        Product product = new Product(null, "Salad", new BigDecimal("10.00"), "Fresh salad", restaurant);
        productMapper.insert(product, conn);
        System.out.println("Product inserted: " + product.getId());

        Order order1 = new Order(null, customer, restaurant, false, LocalDateTime.now());
        order1.addProduct(product);
        orderMapper.insert(order1, conn);
        System.out.println("Order 1 inserted: " + order1.getId());

        Order order2 = new Order(null, customer, restaurant, true, LocalDateTime.now());
        order2.addProduct(product);
        orderMapper.insert(order2, conn);
        System.out.println("Order 2 inserted: " + order2.getId());

        // Act
        List<Order> orders = orderMapper.findOrdersByCustomer(customer, conn);

        // Assert
        assertEquals(2, orders.size(), "Customer should have 2 orders");
    }

    @Test
    public void testCacheAfterInsertOrder() throws SQLException, OrderPersistenceException, ProductPersistenceException, RestaurantPersistenceException, CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "123456789", "order-cache@test.com", address, "O", "Cache", "Insert");
        customerMapper.insert(customer, conn);
        Restaurant restaurant = new Restaurant(null, "Cache Insert Resto", address);
        restaurantMapper.insert(restaurant, conn);
        Product product = new Product(null, "Pizza", new BigDecimal("18.00"), "Delicious pizza", restaurant);
        productMapper.insert(product, conn);
        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());
        order.addProduct(product);
        // Act
        orderMapper.insert(order, conn);

        // Assert
        Order cachedOrder = orderMapper.read(order.getId(), conn);
        assertNotNull(cachedOrder, "Order should be retrievable by ID");
        assertSame(order, cachedOrder, "The order should be cached after insertion");
    }

    @Test
    public void testCacheAfterUpdateOrder() throws SQLException, OrderPersistenceException, ProductPersistenceException, RestaurantPersistenceException, CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "987654321", "update-order@test.com", address, "N", "Jane", "Doe");
        customerMapper.insert(customer, conn);

        Restaurant restaurant = new Restaurant(null, "Update Order Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product = new Product(null, "Burger", new BigDecimal("12.00"), "Tasty burger", restaurant);
        productMapper.insert(product, conn);

        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());
        order.addProduct(product);
        orderMapper.insert(order, conn);

        // Update some order details
        order.setTakeAway(true);

        // Act
        orderMapper.update(order, conn);

        // Assert
        Order updatedOrder = orderMapper.read(order.getId(), conn);
        assertTrue(updatedOrder.getTakeAway(), "Order take away status should be updated");
        assertSame(order, updatedOrder, "The same instance should be returned from the cache after update");
    }

    @Test
    public void testCacheAfterDeleteOrder() throws SQLException, OrderPersistenceException, ProductPersistenceException, RestaurantPersistenceException, CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "555555555", "delete-order-cache@test.com", address, "N", "Delete", "Cache");
        customerMapper.insert(customer, conn);

        Restaurant restaurant = new Restaurant(null, "Delete Cache Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product = new Product(null, "Salad", new BigDecimal("10.00"), "Fresh salad", restaurant);
        productMapper.insert(product, conn);

        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());
        order.addProduct(product);
        orderMapper.insert(order, conn);

        // Act - Delete the order
        orderMapper.delete(order.getId(), conn);

        // Assert - The order should no longer be in the cache
        Optional<Order> cachedOrder = orderMapper.findInCache(order.getId());
        assertFalse(cachedOrder.isPresent(), "Order should no longer be present in the cache after deletion");
    }

    @Test
    public void testCacheAfterReadOrder() throws SQLException, OrderPersistenceException, ProductPersistenceException, RestaurantPersistenceException, CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "555555555", "test-read@test.test", address, "N", "Read", "Cache");
        customerMapper.insert(customer, conn);

        Restaurant restaurant = new Restaurant(null, "Read Cache Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product = new Product(null, "Salad", new BigDecimal("10.00"), "Fresh salad", restaurant);
        productMapper.insert(product, conn);

        Order order = new Order(null, customer, restaurant, false, LocalDateTime.now());
        order.addProduct(product);
        orderMapper.insert(order, conn);

        // Act - Read the order
        Order readOrder = orderMapper.read(order.getId(), conn);

        // Assert - The order should be in the cache
        Order cachedOrder = orderMapper.findInCache(order.getId()).orElse(null);
        assertNotNull(cachedOrder, "Order should be in cache after read");
        assertSame(readOrder, cachedOrder, "The same instance should be returned from the cache after read");
}
}
