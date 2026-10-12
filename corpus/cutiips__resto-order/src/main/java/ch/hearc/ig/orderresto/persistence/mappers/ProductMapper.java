package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.business.Product;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;

import java.math.BigDecimal;
import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * 🛒 ProductMapper - Manages database operations for {@link Product} entities.
 * <p>
 * Provides CRUD operations for products and manages associations with restaurants.
 */
public class ProductMapper extends BaseMapper<Product> {
    private final RestaurantMapper restaurantMapper = new RestaurantMapper();

    /**
     * 🧩 Extracts a {@link Product} from a {@link ResultSet}.
     *
     * @param rs   The {@link ResultSet} containing product data.
     * @param conn The database connection used for the operation.
     * @return The {@link Product} entity extracted from the result set.
     * @throws ProductPersistenceException if an error occurs while extracting the product.
     */
    private Product extractProductFromResultSet(ResultSet rs, Connection conn) throws ProductPersistenceException {
        try {
            Long productId = rs.getLong("numero");
            String name = rs.getString("nom");
            BigDecimal price = rs.getBigDecimal("prix_unitaire");
            String description = rs.getString("description");
            Long restaurantId = rs.getLong("fk_resto");
            Restaurant restaurant = getRestaurantById(restaurantId, conn);

            return new Product(productId, name, price, description, restaurant);

        } catch (SQLException | RestaurantPersistenceException e) {
            throw new ProductPersistenceException("Erreur lors de l'extraction du produit du ResultSet", e);
        }
    }

    /**
     * 🔍 Reads a product by its ID from the database, with cache support.
     *
     * @param id   The ID of the product to retrieve.
     * @param conn The database connection used for the operation.
     * @return The {@link Product} entity if found, otherwise null.
     * @throws ProductPersistenceException if an SQL error or data retrieval error occurs.
     */
    public Product read(Long id, Connection conn) throws ProductPersistenceException {
        Optional<Product> cachedProduct = findInCache(id);
        if (cachedProduct.isPresent()) {
            return cachedProduct.get();
        }

        String sql = "SELECT numero, nom, prix_unitaire, description, fk_resto FROM Produit WHERE numero = ?";
        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, id);
            ResultSet rs = statement.executeQuery();



            if (rs.next()) {
                Product product = extractProductFromResultSet(rs, conn);
                addToCache(id, product);
                return product;
            }
        } catch (SQLException e) {
            throw new ProductPersistenceException("Erreur lors de la récupération du produit avec ID: " + id, e);
        }
        return null;
    }

    /**
     * ➕ Inserts a new product into the database and adds it to the cache.
     *
     * @param product The {@link Product} entity to insert.
     * @param conn    The database connection used for the operation.
     * @throws ProductPersistenceException if an SQL error or ID generation error occurs.
     */
    public void insert(Product product, Connection conn) throws ProductPersistenceException {
        String sql = "INSERT INTO Produit (nom, prix_unitaire, description, fk_resto) VALUES (?, ?, ?, ?)";

        try (PreparedStatement statement = conn.prepareStatement(sql, new String[]{"NUMERO"})) {
            statement.setString(1, product.getName());
            statement.setBigDecimal(2, product.getUnitPrice());
            statement.setString(3, product.getDescription());
            statement.setLong(4, product.getRestaurant().getId());

            statement.executeUpdate();
            ResultSet generatedKeys = statement.getGeneratedKeys();
            if (generatedKeys.next()) {
                product.setId(generatedKeys.getLong(1));
                addToCache(product.getId(), product);
            }
        } catch (SQLException e) {
            throw new ProductPersistenceException("Erreur lors de l'insertion du produit: " + product, e);
        }
    }

    /**
     * 🔄 Updates an existing product in the database and updates the cache.
     *
     * @param product The {@link Product} entity with updated information.
     * @param conn    The database connection used for the operation.
     * @throws ProductPersistenceException if an SQL error occurs.
     */
    public void update(Product product, Connection conn) throws ProductPersistenceException {
        String sql = "UPDATE Produit SET nom = ?, prix_unitaire = ?, description = ?, fk_resto = ? WHERE numero = ?";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setString(1, product.getName());
            statement.setBigDecimal(2, product.getUnitPrice());
            statement.setString(3, product.getDescription());
            statement.setLong(4, product.getRestaurant().getId());
            statement.setLong(5, product.getId());

            statement.executeUpdate();
            updateInCache(product.getId(), product);
        } catch (SQLException e) {
            throw new ProductPersistenceException("Erreur lors de la mise à jour du produit: " + product, e);
        }
    }

    /**
     * 🗑️ Deletes a product by its ID from the database and removes it from the cache.
     *
     * @param id   The ID of the product to delete.
     * @param conn The database connection used for the operation.
     * @throws ProductPersistenceException if an SQL error occurs.
     */
    public void delete(Long id, Connection conn) throws ProductPersistenceException {
        String sql = "DELETE FROM Produit WHERE numero = ?";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, id);
            statement.executeUpdate();
            removeFromCache(id);
        } catch (SQLException e) {
            throw new ProductPersistenceException("Erreur lors de la suppression du produit avec ID: " + id, e);
        }
    }

    /**
     * 🏠 Retrieves a {@link Restaurant} entity by its ID.
     *
     * @param restaurantId The ID of the restaurant to retrieve.
     * @param conn         The database connection used for the operation.
     * @return The {@link Restaurant} associated with the given ID.
     * @throws RestaurantPersistenceException if an SQL error occurs.
     */
    private Restaurant getRestaurantById(Long restaurantId, Connection conn) throws RestaurantPersistenceException {
        return restaurantMapper.read(restaurantId, conn);
    }

    /**
     * 🍽️ Retrieves all products associated with a specific restaurant ID.
     *
     * @param restaurantId The ID of the restaurant.
     * @param conn         The database connection used for the operation.
     * @return A list of {@link Product} entities associated with the restaurant.
     * @throws ProductPersistenceException if an SQL error occurs.
     */
    public List<Product> getProductsByRestaurantId(Long restaurantId, Connection conn) throws ProductPersistenceException {
        List<Product> products = new ArrayList<>();
        String sql = "SELECT numero, nom, prix_unitaire, description, fk_resto FROM Produit WHERE fk_resto = ?";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            statement.setLong(1, restaurantId);
            ResultSet rs = statement.executeQuery();

            while (rs.next()) {
                Product product = extractProductFromResultSet(rs, conn);
                products.add(product);
                addToCache(product.getId(), product);
            }
        } catch (SQLException e) {
            throw new ProductPersistenceException("Erreur lors de la récupération des produits pour le restaurant avec ID: " + restaurantId, e);
        }
        return products;
    }

    /**
     * 📜 Retrieves all products from the database and adds them to the cache.
     *
     * @param conn The database connection used for the operation.
     * @return A list of all {@link Product} entities.
     * @throws ProductPersistenceException if an SQL error occurs.
     */
    public List<Product> findAll(Connection conn) throws ProductPersistenceException {
        List<Product> products = new ArrayList<>();
        String sql = "SELECT numero, nom, prix_unitaire, description, fk_resto FROM Produit";

        try (PreparedStatement statement = conn.prepareStatement(sql)) {
            ResultSet rs = statement.executeQuery();

            while (rs.next()) {
                Product product = extractProductFromResultSet(rs, conn);
                products.add(product);
                addToCache(product.getId(), product);
            }
        } catch (SQLException e) {
            throw new ProductPersistenceException("Erreur lors de la récupération de tous les produits", e);
        }
        return products;
    }
}
