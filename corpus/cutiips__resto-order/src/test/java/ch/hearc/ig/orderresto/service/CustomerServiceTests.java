
package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.Address;
import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.business.OrganizationCustomer;
import ch.hearc.ig.orderresto.business.PrivateCustomer;
import ch.hearc.ig.orderresto.persistence.mappers.CustomerMapper;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;
import org.junit.jupiter.api.*;
import org.mockito.Mockito;

import java.sql.Connection;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class CustomerServiceTests {

    private CustomerService customerService;
    private TransactionHandler transactionHandlerMock;
    private CustomerMapper customerMapperMock;

    @BeforeEach
    public void setUp() {
        customerMapperMock = Mockito.mock(CustomerMapper.class);
        transactionHandlerMock = Mockito.mock(TransactionHandler.class);
        customerService = new CustomerService(customerMapperMock, transactionHandlerMock);
    }

    @Test
    public void testInsertPrivateCustomer() throws Exception {
        // Arrange
        Address address = new Address("CH", "2000", "Neuchâtel", "Rue", "1");
        PrivateCustomer customer = new PrivateCustomer(null, "123456789", "private@test.com", address, "O", "John", "Doe");

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        // Act & Assert
        assertDoesNotThrow(() -> customerService.addCustomer(customer));
        verify(customerMapperMock, times(1)).insert(eq(customer), any(Connection.class));
    }

    @Test
    public void testInsertOrganizationCustomer() throws Exception {
        // Arrange
        Address address = new Address("CH", "3000", "Berne", "Avenue", "10");
        OrganizationCustomer customer = new OrganizationCustomer(null, "987654321", "org@test.com", address, "Test SA", "SA");

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        // Act & Assert
        assertDoesNotThrow(() -> customerService.addCustomer(customer));
        verify(customerMapperMock, times(1)).insert(eq(customer), any(Connection.class));
    }

    @Test
    public void testGetCustomerById() throws Exception {
        // Arrange
        Address address = new Address("CH", "1000", "Lausanne", "Route", "5");
        PrivateCustomer customer = new PrivateCustomer(1L, "1122334455", "getcustomer@test.com", address, "N", "Alice", "Smith");
        when(customerMapperMock.read(anyLong(), any(Connection.class))).thenReturn(customer);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            return action.execute(Mockito.mock(Connection.class));
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        // Act
        Customer fetchedCustomer = customerService.getCustomerById(customer.getId());

        // Assert
        assertNotNull(fetchedCustomer, "Customer should be retrievable by ID");
        assertEquals(customer.getEmail(), fetchedCustomer.getEmail(), "Emails should match");
    }

    @Test
    public void testUpdateCustomer() throws Exception {
        // Arrange
        Address address = new Address("CH", "4000", "Bâle", "Rue Centrale", "3");
        PrivateCustomer customer = new PrivateCustomer(1L, "9988776655", "update2@test.com", address, "O", "Bob", "Marley");

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        // Act & Assert
        assertDoesNotThrow(() -> customerService.updateCustomer(customer));
        verify(customerMapperMock, times(1)).update(eq(customer), any(Connection.class));
    }

    @Test
    public void testDeleteCustomer() throws Exception {
        // Arrange
        Address address = new Address("CH", "5000", "Aarau", "Place", "7");
        PrivateCustomer customer = new PrivateCustomer(1L, "5544332211", "delete@test.com", address, "N", "Charlie", "Chaplin");

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        // Act & Assert
        assertDoesNotThrow(() -> customerService.deleteCustomer(customer));
        verify(customerMapperMock, times(1)).delete(eq(customer.getId()), any(Connection.class));
    }
}
