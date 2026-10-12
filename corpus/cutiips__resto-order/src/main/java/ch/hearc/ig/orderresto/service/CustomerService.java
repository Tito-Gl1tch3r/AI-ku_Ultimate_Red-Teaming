package ch.hearc.ig.orderresto.service;

import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.persistence.exceptions.CustomerPersistenceException;
import ch.hearc.ig.orderresto.persistence.mappers.CustomerMapper;
import ch.hearc.ig.orderresto.service.exceptions.CustomerServiceException;
import ch.hearc.ig.orderresto.service.utils.TransactionHandler;

import java.sql.Connection;
import java.sql.SQLException;

public class CustomerService {

    private final CustomerMapper customerMapper;
    private final TransactionHandler transactionHandler;

    public CustomerService() {
        this.customerMapper = new CustomerMapper();
        this.transactionHandler = new TransactionHandler();
    }

    public CustomerService(CustomerMapper customerMapper, TransactionHandler transactionHandler) {
        this.customerMapper = customerMapper;
        this.transactionHandler = transactionHandler;
    }

    public void addCustomer(Customer customer) throws CustomerServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                customerMapper.insert(customer, conn);
                return null; // Void equivalent
            });
        } catch (Exception e) {
            throw new CustomerServiceException("Failed to add customer", e);
        }
    }

    public Customer getExistingCustomer(String email) throws CustomerServiceException {
        try {
            return transactionHandler.executeInTransaction(conn -> customerMapper.findByEmail(email, conn));
        } catch (Exception e) {
            throw new CustomerServiceException("Failed to get customer by email", e);
        }
    }

    public Customer getCustomerById(Long id) throws CustomerServiceException {
        try {
            return transactionHandler.executeInTransaction(conn -> customerMapper.read(id, conn));
        } catch (Exception e) {
            throw new CustomerServiceException("Failed to get customer by id", e);
        }
    }

    public void updateCustomer(Customer customer) throws CustomerServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                customerMapper.update(customer, conn);
                return null; // Void equivalent
            });
            System.out.println("Client updated successfully!");
        } catch (Exception e) {
            throw new CustomerServiceException("Failed to update customer", e);
        }
    }

    public void deleteCustomer(Customer customer) throws CustomerServiceException {
        try {
            transactionHandler.executeInTransaction(conn -> {
                customerMapper.delete(customer.getId(), conn);
                return null; // Void equivalent
            });
            System.out.println("Client deleted successfully!");
        } catch (Exception e) {
            throw new CustomerServiceException("Failed to delete customer", e);
        }
    }
}