package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.business.Order;
import ch.hearc.ig.orderresto.business.Product;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.CustomerPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.OrderPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.service.exceptions.CustomerServiceException;
import ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException;

import java.sql.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * 🧾 OrderMapper - Handles database operations for {@link Order} entities.
 * <p>
 * Provides CRUD operations for orders and manages associations with customers, restaurants, and products.
 */
public class OrderMapper extends BaseMapper<Order> {
    private final CustomerMapper customerMapper = new CustomerMapper();
    private final ProductMapper productMapper = new ProductMapper();
    private final RestaurantMapper restaurantMapper = new RestaurantMapper();

    /**
     * 🔍 Reads an order by its ID from the database.
     *
     * @param id   The ID of the order to retrieve.
     * @param conn The database connection used for the operation.
     * @return The {@link Order} entity if found, otherwise null.
     * @throws OrderPersistenceException if an SQL error or data retrieval error occurs.
     */
    public Order read(Long id, Connection conn) throws SQLException, OrderPersistenceException {
        Optional<Order> cachedOrder = findInCache(id);
        if (cachedOrder.isPresent()) {
            return cachedOrder.get();
        }

        Order order = null;
        String sql = "SELECT numero, fk_client, fk_resto, a_emporter, quand FROM Commande WHERE numero = ?";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, id);
            ResultSet rs = statement.executeQuery();

            if (rs.next()) {
                order = mapRowToOrder(rs, conn);
                if (order.getId() != null) {
                    addToCache(order.getId(), order);
                }
            }
        } catch (RestaurantPersistenceException | CustomerPersistenceException | ProductPersistenceException |
                 CustomerServiceException | RestaurantServiceException e) {
            throw new OrderPersistenceException("Erreur lors de la recherche de la commande par ID", e);
        }
        return order;
    }

    /**
     * 📜 Retrieves all orders from the database.
     *
     * @param conn The database connection used for the operation.
     * @return A list of all {@link Order} entities.
     * @throws OrderPersistenceException if an SQL error occurs.
     */
    public List<Order> findAll(Connection conn) throws SQLException, OrderPersistenceException {
        List<Order> orders = new ArrayList<>();
        String sql = "SELECT numero, fk_client, fk_resto, a_emporter, quand FROM Commande";

        try (PreparedStatement statement = conn.prepareStatement(sql);
             ResultSet rs = statement.executeQuery()) {

            while (rs.next()) {
                Order order = mapRowToOrder(rs, conn);
                if (order.getId() != null) {
                    addToCache(order.getId(), order);
                }
                orders.add(order);
            }
        } catch (RestaurantPersistenceException | CustomerPersistenceException | ProductPersistenceException |
                 CustomerServiceException | RestaurantServiceException | SQLException e) {
            throw new OrderPersistenceException("Erreur lors de la récupération de toutes les commandes", e);
        }
        return orders;
    }

    /**
     * ➕ Inserts a new order into the database.
     *
     * @param order The {@link Order} entity to insert.
     * @param conn  The database connection used for the operation.
     * @throws OrderPersistenceException if an SQL error or ID generation error occurs.
     */
    public void insert(Order order, Connection conn) throws SQLException, OrderPersistenceException {
        String sql = "INSERT INTO Commande (numero, fk_client, fk_resto, a_emporter, quand) VALUES (SEQ_COMMANDE.NEXTVAL, ?, ?, ?, ?)";

        try (PreparedStatement statement = conn.prepareStatement(sql, new String[]{"numero"})) {
            statement.setLong(1, order.getCustomer().getId());
            statement.setLong(2, order.getRestaurant().getId());
            statement.setString(3, order.getTakeAway() ? "O" : "N");
            statement.setTimestamp(4, Timestamp.valueOf(order.getWhen()));
            statement.executeUpdate();

            try (ResultSet generatedKeys = statement.getGeneratedKeys()) {
                if (generatedKeys.next()) {
                    order.setId(generatedKeys.getLong(1));
                }
            } catch (SQLException e) {
                throw new OrderPersistenceException("Échec de l'insertion de la commande, aucun ID généré.", e);
            }

            try {
                insertOrderProducts(order, conn);
            } catch (SQLException e) {
                throw new OrderPersistenceException("Erreur lors de l'insertion des produits de la commande", e);
            }

            if (order.getId() != null) {
                addToCache(order.getId(), order);
            }
        }
    }

    /**
     * 🔄 Updates an existing order in the database.
     *
     * @param order The {@link Order} entity with updated information.
     * @param conn  The database connection used for the operation.
     * @throws OrderPersistenceException if an SQL error occurs.
     */
    public void update(Order order, Connection conn) throws SQLException, OrderPersistenceException {
        String sql = "UPDATE Commande SET fk_client = ?, fk_resto = ?, a_emporter = ?, quand = ? WHERE numero = ?";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, order.getCustomer().getId());
            statement.setLong(2, order.getRestaurant().getId());
            statement.setString(3, order.getTakeAway() ? "O" : "N");
            statement.setTimestamp(4, Timestamp.valueOf(order.getWhen()));
            statement.setLong(5, order.getId());
            statement.executeUpdate();

            deleteOrderProducts(order.getId(), conn);
            insertOrderProducts(order, conn);

            if (findInCache(order.getId()).isPresent()) {
                updateInCache(order.getId(), order);
            } else {
                addToCache(order.getId(), order);
            }
        }
    }

    /**
     * 🗑️ Deletes an order by its ID from the database.
     *
     * @param id   The ID of the order to delete.
     * @param conn The database connection used for the operation.
     * @throws OrderPersistenceException if an SQL error occurs.
     */
    public void delete(Long id, Connection conn) throws SQLException, OrderPersistenceException {
        deleteOrderProducts(id, conn);

        String sql = "DELETE FROM Commande WHERE numero = ?";
        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, id);
            statement.executeUpdate();

            findInCache(id).ifPresent(order -> removeFromCache(id));
        }
    }

    /**
     * 📦 Inserts products associated with an order into the database.
     *
     * @param order The {@link Order} entity whose products to associate.
     * @param conn  The database connection used for the operation.
     * @throws SQLException if an SQL error occurs.
     */
    private void insertOrderProducts(Order order, Connection conn) throws SQLException {
        String sql = "INSERT INTO PRODUIT_COMMANDE (fk_produit, fk_commande) VALUES (?, ?)";
        Set<Long> insertedProducts = new HashSet<>();

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            for (Product product : order.getProducts()) {
                if (!insertedProducts.contains(product.getId())) {
                    statement.setLong(1, product.getId());
                    statement.setLong(2, order.getId());
                    statement.executeUpdate();
                    insertedProducts.add(product.getId());
                }
            }
        }

    }

    /**
     * 🎨 Maps a row from a {@link ResultSet} to an {@link Order} object.
     *
     * @param rs   The {@link ResultSet} containing the order data.
     * @param conn The database connection used for the operation.
     * @return The mapped {@link Order} entity.
     * @throws SQLException               if an SQL error occurs.
     * @throws RestaurantPersistenceException if related restaurant data retrieval fails.
     * @throws CustomerPersistenceException if related customer data retrieval fails.
     * @throws ProductPersistenceException if related product data retrieval fails.
     */
    private Order mapRowToOrder(ResultSet rs, Connection conn) throws SQLException, RestaurantPersistenceException, CustomerPersistenceException, ProductPersistenceException, CustomerServiceException, RestaurantServiceException {
        Long orderId = rs.getLong("numero");

        Long customerId = rs.getLong("fk_client");
        Customer customer = customerMapper.read(customerId, conn);

        Long restaurantId = rs.getLong("fk_resto");
        Restaurant restaurant = restaurantMapper.read(restaurantId, conn);

        Boolean takeAway = "O".equalsIgnoreCase(rs.getString("a_emporter"));
        LocalDateTime when = rs.getTimestamp("quand").toLocalDateTime();

        Order order = new Order(orderId, customer, restaurant, takeAway, when);

        Set<Product> products = findProductsByOrderId(orderId, conn);
        for (Product product : products) {
            order.addProduct(product);
        }
        return order;
    }

    /**
     * 🗑️ Deletes products associated with a specific order.
     *
     * @param orderId The ID of the order whose products to delete.
     * @param conn    The database connection used for the operation.
     * @throws SQLException if an SQL error occurs.
     */
    private void deleteOrderProducts(Long orderId, Connection conn) throws SQLException {
        String sql = "DELETE FROM Produit_Commande WHERE fk_commande = ?";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, orderId);
            statement.executeUpdate();
        }
    }

    /**
     * 🔗 Retrieves products associated with a given order ID.
     *
     * @param orderId The ID of the order.
     * @param conn    The database connection used for the operation.
     * @return A set of {@link Product} entities associated with the order.
     * @throws ProductPersistenceException if an SQL error occurs or products cannot be retrieved.
     */
    private Set<Product> findProductsByOrderId(Long orderId, Connection conn) throws ProductPersistenceException {
        Set<Product> products = new HashSet<>();
        String sql = "SELECT fk_produit FROM Produit_Commande WHERE fk_commande = ?";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, orderId);
            ResultSet rs = statement.executeQuery();

            while (rs.next()) {
                Long productId = rs.getLong("fk_produit");
                Product product = productMapper.read(productId, conn);
                products.add(product);
            }
        } catch (ProductPersistenceException | SQLException e) {
            throw new ProductPersistenceException("Erreur lors de la récupération des produits par ID de commande", e);
        }
        return products;
    }

    /**
     * 👥 Retrieves all orders associated with a specific customer.
     *
     * @param customer The {@link Customer} whose orders to retrieve.
     * @param conn     The database connection used for the operation.
     * @return A list of {@link Order} entities associated with the customer.
     * @throws OrderPersistenceException if an SQL error occurs or orders cannot be retrieved.
     */
    public List<Order> findOrdersByCustomer(Customer customer, Connection conn) throws SQLException, OrderPersistenceException {
        List<Order> orders = new ArrayList<>();
        String sql = "SELECT numero, fk_client, fk_resto, a_emporter, quand FROM Commande WHERE fk_client = ?";
        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, customer.getId());
            ResultSet rs = statement.executeQuery();
            while (rs.next()) {
                Order order = mapRowToOrder(rs, conn);
                if (order.getId() != null) {
                    addToCache(order.getId(), order);
                }
                orders.add(order);
            }
        } catch (RestaurantPersistenceException | CustomerPersistenceException | ProductPersistenceException |
                 CustomerServiceException | RestaurantServiceException | SQLException e) {
            throw new OrderPersistenceException("Erreur lors de la récupération des commandes par client", e);
        }
        return orders;
    }
}
