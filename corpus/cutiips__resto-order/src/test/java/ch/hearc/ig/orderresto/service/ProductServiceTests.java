
package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.Product;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.mappers.ProductMapper;
import ch.hearc.ig.orderresto.service.exceptions.ProductServiceException;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;
import org.junit.jupiter.api.*;
import org.mockito.Mockito;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class ProductServiceTests {

    private ProductService productService;
    private ProductMapper productMapperMock;
    private TransactionHandler transactionHandlerMock;

    @BeforeEach
    public void setUp() {
        productMapperMock = Mockito.mock(ProductMapper.class);
        transactionHandlerMock = Mockito.mock(TransactionHandler.class);
        productService = new ProductService(productMapperMock, transactionHandlerMock);
    }

    @Test
    public void testCreateProduct() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Product product = new Product(null, "Test Product", new BigDecimal("10.99"), "A product for testing", restaurant);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = productService.addProduct(product);
            assertTrue(result, "Product should be created successfully");
        });
    }

    @Test
    public void testCreateProductWithSQLException() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Product product = new Product(null, "Test Product", new BigDecimal("10.99"), "A product for testing", restaurant);

        // Simuler une exception lors de l'insertion
        doThrow(new ProductPersistenceException("Simulated persistence exception", new SQLException("Simulated SQL cause")))
                .when(productMapperMock).insert(any(Product.class), any(Connection.class));

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        // Vérifier qu'une exception est lancée
        assertThrows(ProductServiceException.class, () -> productService.addProduct(product));
    }

    @Test
    public void testGetProductById() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Product product = new Product(1L, "Test Product", new BigDecimal("10.99"), "A product for testing", restaurant);
        when(productMapperMock.read(anyLong(), any(Connection.class))).thenReturn(product);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            return action.execute(Mockito.mock(Connection.class));
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        Product retrievedProduct = productService.getProductById(1L);
        assertNotNull(retrievedProduct, "Product should be retrieved successfully");
        assertEquals(1L, retrievedProduct.getId(), "Product ID should match");
    }

    @Test
    public void testUpdateProduct() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Product product = new Product(1L, "Updated Product", new BigDecimal("15.99"), "An updated product for testing", restaurant);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = productService.updateProduct(product);
            assertTrue(result, "Product should be updated successfully");
        });
    }

    @Test
    public void testDeleteProduct() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        Product product = new Product(1L, "Test Product", new BigDecimal("10.99"), "A product for testing", restaurant);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            action.execute(Mockito.mock(Connection.class));
            return null;
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        assertDoesNotThrow(() -> {
            boolean result = productService.deleteProduct(product.getId());
            assertTrue(result, "Product should be deleted successfully");
        });
    }

    @Test
    public void testFindAllProducts() throws Exception {
        Restaurant restaurant = new Restaurant(1L, "Test Restaurant", null);
        List<Product> products = List.of(new Product(1L, "Test Product", new BigDecimal("10.99"), "A product for testing", restaurant));
        when(productMapperMock.findAll(any(Connection.class))).thenReturn(products);

        doAnswer(invocation -> {
            TransactionHandler.TransactionCallable<?> action = invocation.getArgument(0);
            return action.execute(Mockito.mock(Connection.class));
        }).when(transactionHandlerMock).executeInTransaction(any(TransactionHandler.TransactionCallable.class));

        List<Product> retrievedProducts = productService.getAllProducts();
        assertNotNull(retrievedProducts, "Products should be retrieved successfully");
        assertEquals(1, retrievedProducts.size(), "There should be one product retrieved");
    }
}
