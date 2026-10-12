package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.business.Address;
import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.business.OrganizationCustomer;
import ch.hearc.ig.orderresto.business.PrivateCustomer;
import ch.hearc.ig.orderresto.persistence.exceptions.CustomerPersistenceException;
import ch.hearc.ig.orderresto.service.utils.ConnectionManager;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

public class CustomerMapperTests {

    private static Connection conn;
    private CustomerMapper customerMapper;

    @BeforeAll
    public static void setUpClass() throws SQLException {
        conn = ConnectionManager.getConnection();
    }

    @BeforeEach
    public void setUp() {
        customerMapper = new CustomerMapper();
    }

    @AfterEach
    public void tearDown() throws Exception {
        if (conn != null) {
            if (conn.getAutoCommit()) {
                conn.setAutoCommit(false);
            }
            conn.rollback(); // Revenir en arrière après chaque test
        }
    }

    @AfterAll
    public static void tearDownClass() {
        try {
            if (conn != null && !conn.isClosed()) {
                conn.close();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    @Test
    public void testInsertPrivateCustomer() {
        Address address = new Address("CH", "2000", "Neuchâtel", "Street", "2");
        PrivateCustomer customer = new PrivateCustomer(null, "123456789", "test@test.com", address, "O", "Jonathan", "Curty");

        assertDoesNotThrow(() -> customerMapper.insert(customer, conn));
        assertNotNull(customer.getId(), "Customer ID should be generated and set");
    }

    @Test
    public void testInsertOrganizationCustomer() {
        Address address = new Address("CH", "3000", "Berne", "Avenue", "2");
        OrganizationCustomer customer = new OrganizationCustomer(null, "987654321", "org@test.com", address, "Test SA", "SA");

        assertDoesNotThrow(() -> customerMapper.insert(customer, conn));
        assertNotNull(customer.getId(), "Customer ID should be generated and set");
    }

    @Test
    public void testInvalidPostalCode() {
        Address address = new Address("CH", "20000", "Genève", "Rue", "2"); // Code postal invalide (5 caractères)
        PrivateCustomer customer = new PrivateCustomer(null, "543216789", "invalid@test.com", address, "N", "Invalid", "Postal");

        CustomerPersistenceException exception = assertThrows(CustomerPersistenceException.class, () -> customerMapper.insert(customer, conn));
        assertTrue(exception.getCause() instanceof SQLException, "Expected a SQLException as the cause");
        String expectedMessage = "ORA-12899";
        String actualMessage = exception.getCause().getMessage();

        assertTrue(actualMessage.contains(expectedMessage), "Expected ORA-12899 error due to invalid postal code length");
    }


    @Test
    public void testReadPrivateCustomer() throws CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Route", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "1122334455", "readprivate@test.com", address, "O", "Read", "Private");
        customerMapper.insert(customer, conn);

        // Act
        Customer readCustomer = customerMapper.findByEmail("readprivate@test.com", conn);

        // Assert
        assertNotNull(readCustomer, "Customer should be retrievable by email");
        assertTrue(readCustomer instanceof PrivateCustomer, "Customer should be of type PrivateCustomer");
        assertEquals(customer.getEmail(), readCustomer.getEmail(), "Email should match");
    }


    @Test
    public void testReadOrganizationCustomer() throws CustomerPersistenceException {
        Address address = new Address("CH", "1000", "Lausanne", "Route", "1");
        OrganizationCustomer customer = new OrganizationCustomer(null, "5566778899", "org@gmail.com", address, "Test SA", "SA");
        customerMapper.insert(customer, conn);

        Customer readCustomer = customerMapper.findByEmail("org@gmail.com", conn);
        assertNotNull(readCustomer, "Customer should be retrievable by email");
        assertEquals(customer.getEmail(), readCustomer.getEmail(), "Email should match");
    }

    @Test
    public void testDeleteCustomer() throws CustomerPersistenceException {
        Address address = new Address("CH", "1000", "Lausanne", "Route", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "5566778899", "delete@test.com", address, "N", "Delete", "Me");
        customerMapper.insert(customer, conn);

        assertDoesNotThrow(() -> customerMapper.delete(customer.getId(), conn));
        Customer deletedCustomer = customerMapper.findByEmail("delete@test.com", conn);
        assertNull(deletedCustomer, "Customer should no longer be retrievable after deletion");
    }

    @Test
    public void testUpdateCustomer() throws CustomerPersistenceException {
        Address address = new Address("CH", "1000", "Lausanne", "Route", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "5566778899", "test-update@test.gmail", address, "N", "Update", "Me");
        customerMapper.insert(customer, conn);

        Customer updatedCustomer = customerMapper.findByEmail("test-update@test.gmail", conn);


        updatedCustomer.setPhoneNumber("123456789");
        updatedCustomer.getAddress().setStreet("Avenue");
        updatedCustomer.getAddress().setStreetNumber("2");

        assertDoesNotThrow(() -> customerMapper.update(updatedCustomer, conn));
        Customer fetchedCustomer = customerMapper.findByEmail("test-update@test.gmail", conn);
        assertEquals("123456789", fetchedCustomer.getPhone(), "Phone number should be updated");
        assertEquals("Avenue", fetchedCustomer.getAddress().getStreet(), "Street should be updated");
        assertEquals("2", fetchedCustomer.getAddress().getStreetNumber(), "Street number should be updated");
    }

    @Test
    public void testCacheAfterInsert() throws CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "4000", "Lausanne", "Route", "5");
        PrivateCustomer customer = new PrivateCustomer(null, "1122334455", "cache@test.com", address, "O", "Cache", "Customer");
        customerMapper.insert(customer, conn);

        // Act
        Customer readCustomer = customerMapper.read(customer.getId(), conn);

        // Assert
        assertNotNull(readCustomer, "Customer should be retrievable by ID");
        assertEquals(customer.getId(), readCustomer.getId(), "Customer ID should match");
        assertSame(customer, readCustomer, "The same instance should be returned from the cache");
    }

    @Test
    public void testCacheAfterDelete() throws CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "4000", "Lausanne", "Route", "5");
        PrivateCustomer customer = new PrivateCustomer(null, "1122334455", "deletecache@test.com", address, "O", "Delete", "Cache");
        customerMapper.insert(customer, conn);

        // Act - Supprimer le client
        customerMapper.delete(customer.getId(), conn);

        // Assert - Le client ne devrait plus être dans le cache
        Optional<Customer> cachedCustomer = customerMapper.findInCache(customer.getId());
        assertFalse(cachedCustomer.isPresent(), "Customer should no longer be present in the cache after deletion");
    }

    @Test
    public void testUpdatePrivateCustomerInCache() throws CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "6000", "Zurich", "Rue de la Paix", "15");
        PrivateCustomer customer = new PrivateCustomer(null, "3344556677", "privatecache@test.com", address, "M", "Mark", "Smith");
        customerMapper.insert(customer, conn);

        // Modifier des détails du PrivateCustomer
        customer.setFirstName("UpdatedMark");
        customer.setLastName("UpdatedSmith");
        customer.setPhoneNumber("9988776655");

        // Act - Mise à jour
        customerMapper.update(customer, conn);

        // Assert - Récupérer le client et vérifier les modifications
        Customer updatedCustomer = customerMapper.read(customer.getId(), conn);
        assertNotNull(updatedCustomer, "Customer should be retrievable by ID");
        assertTrue(updatedCustomer instanceof PrivateCustomer, "Customer should be of type PrivateCustomer");

        PrivateCustomer updatedPrivateCustomer = (PrivateCustomer) updatedCustomer;
        assertEquals("UpdatedMark", updatedPrivateCustomer.getFirstName(), "First name should be updated");
        assertEquals("UpdatedSmith", updatedPrivateCustomer.getLastName(), "Last name should be updated");
        assertEquals("9988776655", updatedPrivateCustomer.getPhoneNumber(), "Phone number should be updated");
        assertSame(customer, updatedPrivateCustomer, "The same instance should be returned from the cache after update");
    }

    @Test
    public void testUpdateOrganizationCustomerInCache() throws CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "8000", "Zurich", "Rue du Commerce", "10");
        OrganizationCustomer customer = new OrganizationCustomer(null, "4433221100", "orgcache@test.com", address, "Original Corp", "SA");
        customerMapper.insert(customer, conn);

        // Modifier des détails de l'OrganizationCustomer
        customer.setName("Updated Corp");
        customer.setLegalForm("SA");
        customer.setPhoneNumber("1122334455");

        // Act - Mise à jour
        customerMapper.update(customer, conn);

        // Assert - Récupérer le client et vérifier les modifications
        Customer updatedCustomer = customerMapper.read(customer.getId(), conn);
        assertNotNull(updatedCustomer, "Customer should be retrievable by ID");
        assertTrue(updatedCustomer instanceof OrganizationCustomer, "Customer should be of type OrganizationCustomer");

        OrganizationCustomer updatedOrgCustomer = (OrganizationCustomer) updatedCustomer;
        assertEquals("Updated Corp", updatedOrgCustomer.getName(), "Name should be updated");
        assertEquals("SA", updatedOrgCustomer.getLegalForm(), "Legal form should be updated");
        assertEquals("1122334455", updatedOrgCustomer.getPhoneNumber(), "Phone number should be updated");
        assertSame(customer, updatedOrgCustomer, "The same instance should be returned from the cache after update");
    }

    @Test
    public void testCacheAfterMultipleReads() throws CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "7000", "Fribourg", "Boulevard", "20");
        PrivateCustomer customer = new PrivateCustomer(null, "5566778899", "multiread@test.com", address, "N", "Cache", "Multiple");
        customerMapper.insert(customer, conn);

        // Act - Première lecture depuis la base de données
        Customer firstRead = customerMapper.read(customer.getId(), conn);
        assertNotNull(firstRead, "Customer should be retrievable by ID");

        // Act - Deuxième lecture qui devrait provenir du cache
        Customer secondRead = customerMapper.read(customer.getId(), conn);

        // Assert - Vérification que l'objet récupéré est identique (même instance)
        assertSame(firstRead, secondRead, "The second read should return the same instance from the cache");
    }

    @Test
    public void testCacheDoesNotMixCustomerTypes() throws CustomerPersistenceException {
        // Arrange
        Address address = new Address("CH", "6000", "Zurich", "Rue de la Paix", "15");
        PrivateCustomer privateCustomer = new PrivateCustomer(null, "3344556677", "privatecustomer@test.com", address, "M", "Mark", "Smith");
        OrganizationCustomer orgCustomer = new OrganizationCustomer(null, "9988776655", "orgcustomer@test.com", address, "Test Corp", "SA");

        // Insert both customers
        customerMapper.insert(privateCustomer, conn);
        customerMapper.insert(orgCustomer, conn);

        // Act - Retrieve each customer from the cache
        Customer cachedPrivateCustomer = customerMapper.read(privateCustomer.getId(), conn);
        Customer cachedOrgCustomer = customerMapper.read(orgCustomer.getId(), conn);

        // Assert - Ensure that the types are not mixed
        assertTrue(cachedPrivateCustomer instanceof PrivateCustomer, "Cached customer should be of type PrivateCustomer");
        assertTrue(cachedOrgCustomer instanceof OrganizationCustomer, "Cached customer should be of type OrganizationCustomer");
        assertNotSame(cachedPrivateCustomer, cachedOrgCustomer, "Different customer types should not refer to the same instance");
    }

}
