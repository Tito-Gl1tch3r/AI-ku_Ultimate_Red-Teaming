package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.mappers.RestaurantMapper;
import ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;

import java.util.List;

public class RestaurantService {

    private final RestaurantMapper restaurantMapper;
    private final TransactionHandler transactionHandler;

    public RestaurantService() {
        this.restaurantMapper = new RestaurantMapper();
        this.transactionHandler = new TransactionHandler();
    }

    public RestaurantService(RestaurantMapper restaurantMapper, TransactionHandler transactionHandler) {
        this.restaurantMapper = restaurantMapper;
        this.transactionHandler = transactionHandler;
    }

    public Restaurant getRestaurantById(Long id) throws RestaurantServiceException {
        try {
            return transactionHandler.executeInTransaction(conn -> restaurantMapper.read(id, conn));
        } catch (Exception e) {
            throw new RestaurantServiceException("Error while getting restaurant by id", e);
        }
    }

    public boolean addRestaurant(Restaurant restaurant) throws RestaurantServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                restaurantMapper.insert(restaurant, conn);
                return null; // Void equivalent
            });
            System.out.println("Restaurant ajouté avec succès !");
            return true;
        } catch (Exception e) {
            throw new RestaurantServiceException("Failed to add restaurant", e);
        }
    }

    public boolean updateRestaurant(Restaurant restaurant) throws RestaurantServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                restaurantMapper.update(restaurant, conn);
                return null; // Void equivalent
            });
            System.out.println("Restaurant updated successfully!");
            return true;
        } catch (Exception e) {
            throw new RestaurantServiceException("Failed to update restaurant", e);
        }
    }

    public boolean deleteRestaurant(Long id) throws RestaurantServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                restaurantMapper.delete(id, conn);
                return null; // Void equivalent
            });
            System.out.println("Restaurant deleted successfully!");
            return true;
        } catch (Exception e) {
            throw new RestaurantServiceException("Failed to delete restaurant", e);
        }
    }

    public List<Restaurant> getAllRestaurants() throws RestaurantServiceException {
        try {
            return transactionHandler.executeInTransaction(restaurantMapper::findAll);
        } catch (Exception e) {
            throw new RestaurantServiceException("Failed to get all restaurants", e);
        }
    }
}
