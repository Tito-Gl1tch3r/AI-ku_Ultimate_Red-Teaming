package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.business.Address;
import ch.hearc.ig.orderresto.business.Product;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.service.utils.ConnectionManager;
import org.junit.jupiter.api.*;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

public class RestaurantMapperTests {

    private static Connection conn;
    private RestaurantMapper restaurantMapper;
    private ProductMapper productMapper;

    @BeforeAll
    public static void setUpClass() throws SQLException {
        conn = ConnectionManager.getConnection();
        conn.setAutoCommit(false);
    }

    @BeforeEach
    public void setUp() {
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
    public void testInsertRestaurant() throws SQLException, RestaurantPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Test Resto", address);

        // Act & Assert
        assertDoesNotThrow(() -> restaurantMapper.insert(restaurant, conn));
        assertNotNull(restaurant.getId(), "Restaurant ID should be generated and set");
    }

    @Test
    public void testReadRestaurant() throws SQLException, RestaurantPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Read Resto", address);
        restaurantMapper.insert(restaurant, conn);

        // Act
        Restaurant readRestaurant = restaurantMapper.read(restaurant.getId(), conn);

        // Assert
        assertNotNull(readRestaurant, "Restaurant should be retrievable by ID");
        assertEquals(restaurant.getId(), readRestaurant.getId(), "Restaurant ID should match");
        assertEquals(restaurant.getName(), readRestaurant.getName(), "Restaurant name should match");
    }

    @Test
    public void testDeleteRestaurant() throws SQLException, RestaurantPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Delete Resto", address);
        restaurantMapper.insert(restaurant, conn);

        // Act & Assert
        assertDoesNotThrow(() -> restaurantMapper.delete(restaurant.getId(), conn));
        Restaurant deletedRestaurant = restaurantMapper.read(restaurant.getId(), conn);
        assertNull(deletedRestaurant, "Restaurant should no longer be retrievable after deletion");
    }

    @Test
    public void testAddProductToRestaurant() throws SQLException, RestaurantPersistenceException, ProductPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Product Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product = new Product(null, "Burger", new BigDecimal("12.00"), "Tasty burger", restaurant);

        // Act & Assert
        assertDoesNotThrow(() -> productMapper.insert(product, conn));
        assertNotNull(product.getId(), "Product ID should be generated and set");
        assertEquals(restaurant.getId(), product.getRestaurant().getId(), "Product should be linked to the correct restaurant");
    }

    @Test
    public void testGetProductsByRestaurant() throws SQLException, RestaurantPersistenceException, ProductPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Get Products Resto", address);
        restaurantMapper.insert(restaurant, conn);

        Product product1 = new Product(null, "Pizza", new BigDecimal("15.00"), "Delicious pizza", restaurant);
        productMapper.insert(product1, conn);

        Product product2 = new Product(null, "Pasta", new BigDecimal("10.00"), "Tasty pasta", restaurant);
        productMapper.insert(product2, conn);

        // Act
        List<Product> products = productMapper.getProductsByRestaurantId(restaurant.getId(), conn);

        // Assert
        assertEquals(2, products.size(), "Restaurant should have 2 products");
    }

    @Test
    public void testCacheAfterInsert() throws SQLException, RestaurantPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Cache Resto", address);

        // Act
        restaurantMapper.insert(restaurant, conn);
        Restaurant cachedRestaurant = restaurantMapper.findInCache(restaurant.getId()).orElse(null);

        // Assert
        assertNotNull(cachedRestaurant, "Restaurant should be in cache after insert");
    }

    @Test
    public void testCacheAfterUpdate() throws SQLException, RestaurantPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Cache Resto", address);
        restaurantMapper.insert(restaurant, conn);

        // Act
        restaurant.setName("Updated Cache Resto");
        restaurantMapper.update(restaurant, conn);
        Restaurant cachedRestaurant = restaurantMapper.findInCache(restaurant.getId()).orElse(null);

        // Assert
        assertNotNull(cachedRestaurant, "Restaurant should be in cache after update");
        assertEquals("Updated Cache Resto", cachedRestaurant.getName(), "Restaurant name should be updated in cache");
    }

    @Test
    public void testCacheAfterDelete() throws SQLException, RestaurantPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Cache Resto", address);
        restaurantMapper.insert(restaurant, conn);

        // Act
        restaurantMapper.delete(restaurant.getId(), conn);
        Restaurant cachedRestaurant = restaurantMapper.findInCache(restaurant.getId()).orElse(null);

        // Assert
        assertNull(cachedRestaurant, "Restaurant should not be in cache after delete");
    }

    @Test
    public void testCacheAfterRead() throws SQLException, RestaurantPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Rue", "1");
        Restaurant restaurant = new Restaurant(null, "Cache Resto", address);
        restaurantMapper.insert(restaurant, conn);

        // Act
        Restaurant readRestaurant = restaurantMapper.read(restaurant.getId(), conn);
        Restaurant cachedRestaurant = restaurantMapper.findInCache(restaurant.getId()).orElse(null);

        // Assert
        assertNotNull(cachedRestaurant, "Restaurant should be in cache after read");
        assertEquals(readRestaurant, cachedRestaurant, "Cached restaurant should match read restaurant");
    }
}
