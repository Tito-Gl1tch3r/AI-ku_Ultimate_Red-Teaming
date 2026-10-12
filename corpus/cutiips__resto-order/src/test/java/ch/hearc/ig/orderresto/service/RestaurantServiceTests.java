package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.persistence.mappers.RestaurantMapper;
import ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;
import org.junit.jupiter.api.*;
import org.mockito.Mockito;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class RestaurantServiceTests {

    private RestaurantService restaurantService;
    private RestaurantMapper restaurantMapperMock;
    private TransactionHandler transactionHandlerMock;

    @BeforeEach
    public void setUp() {
        restaurantMapperMock = Mockito.mock(RestaurantMapper.class);
        transactionHandlerMock = Mockito.mock(TransactionHandler.class);
        restaurantService = new RestaurantService(restaurantMapperMock, transactionHandlerMock);
    }

    @Test
    public void testCreateRestaurant() throws Exception {
        Restaurant restaurant = new Restaurant(null, "Test Restaurant", null);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = restaurantService.addRestaurant(restaurant);
            assertTrue(result, "Restaurant should be created successfully");
        });
    }

    @Test
    public void testCreateRestaurantWithSQLException() throws Exception {
        Restaurant restaurant = new Restaurant(null, "Test Restaurant", null);

        // Simuler une exception lors de l'insertion
        doThrow(new RestaurantPersistenceException("Simulated persistence exception", new SQLException("Simulated SQL cause")))
                .when(restaurantMapperMock).insert(any(Restaurant.class), any(Connection.class));

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        // Vérifier qu'une exception est lancée
        assertThrows(RestaurantServiceException.class, () -> restaurantService.addRestaurant(restaurant));
    }

    @Test
    public void testGetRestaurantById() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        when(restaurantMapperMock.read(anyLong(), any(Connection.class))).thenReturn(restaurant);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            return action.execute(Mockito.mock(Connection.class));
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        Restaurant retrievedRestaurant = restaurantService.getRestaurantById(1L);
        assertNotNull(retrievedRestaurant, "Restaurant should be retrieved successfully");
        assertEquals(1L, retrievedRestaurant.getId(), "Restaurant ID should match");
    }

    @Test
    public void testUpdateRestaurant() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Updated Restaurant", null);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = restaurantService.updateRestaurant(restaurant);
            assertTrue(result, "Restaurant should be updated successfully");
        });
    }

    @Test
    public void testDeleteRestaurant() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = restaurantService.deleteRestaurant(restaurant.getId());
            assertTrue(result, "Restaurant should be deleted successfully");
        });
    }

    @Test
    public void testFindAllRestaurants() throws Exception {
        List<Restaurant> restaurants = List.of(new Restaurant(1L, "Test Restaurant", null));
        when(restaurantMapperMock.findAll(any(Connection.class))).thenReturn(restaurants);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            return action.execute(Mockito.mock(Connection.class));
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        List<Restaurant> retrievedRestaurants = restaurantService.getAllRestaurants();
        assertNotNull(retrievedRestaurants, "Restaurants should be retrieved successfully");
        assertFalse(retrievedRestaurants.isEmpty(), "There should be at least one restaurant retrieved");
    }
}
