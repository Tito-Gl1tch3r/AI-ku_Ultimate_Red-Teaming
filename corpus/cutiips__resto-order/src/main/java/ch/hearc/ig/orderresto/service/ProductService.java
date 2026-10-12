package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.Product;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.mappers.ProductMapper;
import ch.hearc.ig.orderresto.service.exceptions.ProductServiceException;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;

public class ProductService {

    private final ProductMapper productMapper;
    private final TransactionHandler transactionHandler;

    public ProductService() {
        this.productMapper = new ProductMapper();
        this.transactionHandler = new TransactionHandler();
    }

    public ProductService(ProductMapper productMapper, TransactionHandler transactionHandler) {
        this.productMapper = productMapper;
        this.transactionHandler = transactionHandler;
    }

    public Product getProductById(Long id) throws ProductServiceException {
        try {
            return transactionHandler.executeInTransaction(conn -> productMapper.read(id, conn));
        } catch (Exception e) {
            throw new ProductServiceException("Error while getting product by id", e);
        }
    }

    public boolean addProduct(Product product) throws ProductServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                productMapper.insert(product, conn);
                return null; // Void equivalent
            });
            System.out.println("Product added successfully!");
            return true;
        } catch (Exception e) {
            throw new ProductServiceException("Failed to add product", e);
        }
    }

    public List<Product> getProductsByRestaurantId(Long restaurantId) throws ProductServiceException {
        try {
            return transactionHandler.executeInTransaction(conn -> productMapper.getProductsByRestaurantId(restaurantId, conn));
        } catch (Exception e) {
            throw new ProductServiceException("Failed to get products by restaurant id", e);
        }
    }

    public boolean updateProduct(Product product) throws ProductServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                productMapper.update(product, conn);
                return null; // Void equivalent
            });
            System.out.println("Product updated successfully!");
            return true;
        } catch (Exception e) {
            throw new ProductServiceException("Failed to update product", e);
        }
    }

    public boolean deleteProduct(Long id) throws ProductServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                productMapper.delete(id, conn);
                return null; // Void equivalent
            });
            System.out.println("Product deleted successfully!");
            return true;
        } catch (Exception e) {
            throw new ProductServiceException("Failed to delete product", e);
        }
    }

    public List<Product> getAllProducts() throws ProductServiceException {
        try {
            return transactionHandler.executeInTransaction(productMapper::findAll);
        } catch (Exception e) {
            throw new ProductServiceException("Failed to get all products", e);
        }
    }
}