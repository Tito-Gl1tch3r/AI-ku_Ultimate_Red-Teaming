package com.fnr.controller;

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceException;

import com.fnr.connection.ConnectionFactory;
import com.fnr.dao.DAO;
import com.fnr.enums.Response;
import com.fnr.interfaces.IController;
import com.fnr.interfaces.IDAO;
import com.fnr.model.Customer;

public class CustomerController implements IController<Customer>{
	private IDAO<Customer> dao;

	public CustomerController() {
		this.dao = new DAO<Customer>();
	}

	private boolean verifyData(Customer cust) {
		if (cust.getName() != null && cust.getEmail() != null && cust.getPhone() != null && cust.getResidencial_Phone() != null)
			return true;
		return false;
	}

	@Override
	public Response post(ConnectionFactory conn, Customer cust) {
		if (verifyData(cust) && this.dao.post(conn, cust))
			return Response.POST_SUCCESS;
		return Response.POST_FAILED;
	}

	@Override
	public Response put(ConnectionFactory conn, Customer customer) {
		if (verifyData(customer) && this.dao.put(conn, customer)) 
			return Response.UPDATE_SUCCESS;
		return Response.UPDATE_FAILED;
	}

	@Override
	public Response delete(ConnectionFactory conn, Customer customer, Integer customerId) {
		if (customerId != null && this.dao.delete(conn, customer, customerId)) 
			return Response.DELETE_SUCCESS;
		return Response.DELETE_FAILED;
	}

	@Override
	public Customer getById(ConnectionFactory conn, Integer id) {
		if (id != null) {
			EntityManager em = conn.getConnection();
			try {
				return em.find(Customer.class, id);
			} catch (PersistenceException e) {
				System.out.println("Desfazendo transa��es... \nMotivo: " + e.getMessage());
				return null;
			} finally {
				em.close();
			}
		}
		return null;
	}

	@Override
	public List<Customer> getAll(ConnectionFactory conn, Customer custInstance) {
		return this.dao.getAll(conn, custInstance);
	}
}