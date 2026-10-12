package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.business.Address;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.persistence.utils.AddressUtils;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

public class RestaurantMapper extends BaseMapper<Restaurant> {

    public void insert(Restaurant restaurant, Connection conn) throws RestaurantPersistenceException {
        String query = "INSERT INTO RESTAURANT (nom, code_postal, localite, rue, num_rue, pays) VALUES (?, ?, ?, ?, ?, ?)";

        try (PreparedStatement stmt = conn.prepareStatement(query, new String[]{"NUMERO"})) {

            stmt.setString(1, restaurant.getName());
            AddressUtils.setPreparedStatementAddress(stmt, restaurant.getAddress(), 2);

            stmt.executeUpdate();

            try (ResultSet generatedKeys = stmt.getGeneratedKeys()) {
                if (generatedKeys.next()) {
                    restaurant.setId(generatedKeys.getLong(1));
                    addToCache(restaurant.getId(), restaurant); // Ajouter au cache après insertion
                }
            }

        } catch (SQLException e) {
            throw new RestaurantPersistenceException("Erreur lors de l'insertion du restaurant : ", e);
        }
    }

    public Restaurant read(Long id, Connection conn) throws RestaurantPersistenceException {
        // Vérifie si le restaurant est déjà dans le cache
        return findInCache(id).orElseGet(() -> {
            String query = "SELECT nom, code_postal, localite, rue, num_rue, pays FROM RESTAURANT WHERE numero = ?";
            try (PreparedStatement stmt = conn.prepareStatement(query)) {

                stmt.setLong(1, id);
                ResultSet rs = stmt.executeQuery();

                if (rs.next()) {
                    Address address = AddressUtils.createAddressFromResultSet(rs);
                    Restaurant restaurant = new Restaurant(id, rs.getString("nom"), address);
                    addToCache(id, restaurant); // Ajouter au cache
                    return restaurant;
                }
            } catch (SQLException e) {
                throw new RuntimeException("Erreur lors de la récupération du restaurant", e);
            }
            return null;  // 404
        });
    }

    public void update(Restaurant restaurant, Connection conn) throws RestaurantPersistenceException {
        String query = "UPDATE RESTAURANT SET nom = ?, code_postal = ?, localite = ?, rue = ?, num_rue = ?, pays = ? WHERE numero = ?";

        try (PreparedStatement stmt = conn.prepareStatement(query)) {

            stmt.setString(1, restaurant.getName());
            AddressUtils.setPreparedStatementAddress(stmt, restaurant.getAddress(), 2);
            stmt.setLong(7, restaurant.getId());

            stmt.executeUpdate();
            updateInCache(restaurant.getId(), restaurant); // Mettre à jour dans le cache

        } catch (SQLException e) {
            throw new RestaurantPersistenceException("Erreur lors de la mise à jour du restaurant : ", e);
        }
    }

    public void delete(Long id, Connection conn) throws RestaurantPersistenceException {
        String query = "DELETE FROM RESTAURANT WHERE numero = ?";

        try (PreparedStatement stmt = conn.prepareStatement(query)) {

            stmt.setLong(1, id);
            stmt.executeUpdate();
            removeFromCache(id); // Supprimer du cache

        } catch (SQLException e) {
            throw new RestaurantPersistenceException("Erreur lors de la suppression du restaurant : ", e);
        }
    }

    public List<Restaurant> findAll(Connection conn) throws RestaurantPersistenceException {
        List<Restaurant> restaurants = new ArrayList<>();
        String query = "SELECT numero, nom, code_postal, localite, rue, num_rue, pays FROM RESTAURANT";

        try (PreparedStatement stmt = conn.prepareStatement(query);
             ResultSet rs = stmt.executeQuery()) {

            while (rs.next()) {
                Long id = rs.getLong("numero");

                // Vérifier si le restaurant est déjà dans le cache
                Restaurant restaurant = findInCache(id).orElse(null);
                if (restaurant == null) {
                    try {
                        Address address = AddressUtils.createAddressFromResultSet(rs);
                        restaurant = new Restaurant(id, rs.getString("nom"), address);
                        addToCache(id, restaurant);
                    } catch (SQLException e) {
                        throw new RestaurantPersistenceException("Erreur lors de la récupération des données de l'adresse ou du nom", e);
                    }
                }

                restaurants.add(restaurant);
            }

        } catch (SQLException e) {
            throw new RestaurantPersistenceException("Erreur lors de la récupération des restaurants : ", e);
        }
        return restaurants;
    }


}
