package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.persistence.exceptions.CustomerPersistenceException;
import ch.hearc.ig.orderresto.persistence.utils.CustomerUtils;

import java.sql.*;
import java.util.Optional;

/**
 * 🧭 CustomerMapper - Manages database operations for {@link Customer} entities.
 * <p>
 * Provides CRUD operations and utilizes an in-memory cache to optimize performance by reducing redundant database calls.
 */
public class CustomerMapper extends BaseMapper<Customer> {

    /**
     * ➕ Inserts a new customer into the database.
     *
     * @param customer The {@link Customer} entity to insert.
     * @param conn     The database connection used for the operation.
     * @throws CustomerPersistenceException if an SQL error occurs or no ID is generated.
     */
    public void insert(Customer customer, Connection conn) throws CustomerPersistenceException {
        String query = "INSERT INTO CLIENT (telephone, email, nom, code_postal, localite, rue, num_rue, pays, est_une_femme, prenom, forme_sociale, type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement stmt = conn.prepareStatement(query, new String[]{"NUMERO"})) {
            CustomerUtils.setPreparedStatementForCustomer(stmt, customer, CustomerUtils.QueryType.INSERT);
            stmt.executeUpdate();

            try (ResultSet generatedKeys = stmt.getGeneratedKeys()) {
                if (generatedKeys.next()) {
                    Long generatedId = generatedKeys.getLong(1);
                    customer.setId(generatedId);
                } else {
                    throw new CustomerPersistenceException("Échec de l'insertion du client, aucun ID généré.");
                }
            }

                addToCache(customer.getId(), customer);
        } catch (SQLException e) {
            throw new CustomerPersistenceException("Erreur lors de l'insertion du client", e);
        }


    }

    /**
     * 📧 Finds a customer by their email.
     *
     * @param email The email of the customer to find.
     * @param conn  The database connection used for the operation.
     * @return The {@link Customer} entity if found, otherwise null.
     * @throws CustomerPersistenceException if an SQL error occurs.
     */
    public Customer findByEmail(String email, Connection conn) throws CustomerPersistenceException {
        String query = "SELECT * FROM CLIENT WHERE email = ?";
        Customer customer = null;

        try (PreparedStatement stmt = conn.prepareStatement(query)) {

            stmt.setString(1, email);
            ResultSet rs = stmt.executeQuery();

            if (rs.next()) {
                customer = CustomerUtils.mapCustomerFromResultSet(rs);
                if (customer != null) {
                    addToCache(customer.getId(), customer);
                }            }
        } catch (SQLException e) {
            throw new CustomerPersistenceException("Erreur lors de la lecture du client", e);
        }

        return customer;
    }

    /**
     * 🔍 Reads a customer from the database by their ID.
     *
     * @param id   The ID of the customer to read.
     * @param conn The database connection used for the operation.
     * @return The {@link Customer} entity if found, otherwise null.
     * @throws CustomerPersistenceException if an SQL error occurs.
     */
    public Customer read(Long id, Connection conn) throws CustomerPersistenceException {
        Optional<Customer> cachedCustomer = findInCache(id);
        if (cachedCustomer.isPresent()) {
            return cachedCustomer.get();
        }

        String query = "SELECT * FROM CLIENT WHERE numero = ?";
        Customer customer = null;

        try (PreparedStatement stmt = conn.prepareStatement(query)) {

            stmt.setLong(1, id);
            ResultSet rs = stmt.executeQuery();

            if (rs.next()) {
                customer = CustomerUtils.mapCustomerFromResultSet(rs);
                if (customer != null && customer.getId() != null) {
                    addToCache(customer.getId(), customer);
                }
            }
        } catch (SQLException e) {
            throw new CustomerPersistenceException("Erreur lors de la recherche du client par ID", e);
        }
        return customer;
    }

    /**
     * ✏️ Updates an existing customer in the database.
     *
     * @param customer The {@link Customer} entity with updated information.
     * @param conn     The database connection used for the operation.
     * @throws CustomerPersistenceException if an SQL error occurs.
     */
    public void update(Customer customer, Connection conn) throws CustomerPersistenceException {
        String query = "UPDATE CLIENT SET telephone = ?, nom = ?, code_postal = ?, localite = ?, rue = ?, num_rue = ?, pays = ?, est_une_femme = ?, prenom = ?, forme_sociale = ? WHERE email = ?";

        try (PreparedStatement stmt = conn.prepareStatement(query)) {
            CustomerUtils.setPreparedStatementForCustomer(stmt, customer, CustomerUtils.QueryType.UPDATE);
            stmt.executeUpdate();
            updateInCache(customer.getId(), customer);
        } catch (SQLException e) {
            throw new CustomerPersistenceException("Erreur lors de la mise à jour du client", e);
        }
    }

    /**
     * 🗑️ Deletes a customer from the database by their ID.
     *
     * @param id   The ID of the customer to delete.
     * @param conn The database connection used for the operation.
     * @throws CustomerPersistenceException if an SQL error occurs.
     */
    public void delete(Long id, Connection conn) throws CustomerPersistenceException {
        String query = "DELETE FROM CLIENT WHERE numero = ?";

        try (PreparedStatement stmt = conn.prepareStatement(query)) {

            stmt.setLong(1, id);
            stmt.executeUpdate();
            if (findInCache(id).isPresent()) {
                removeFromCache(id);
            }
        } catch (SQLException e) {
            throw new CustomerPersistenceException("Erreur lors de la suppression du client", e);
        }
    }
}
