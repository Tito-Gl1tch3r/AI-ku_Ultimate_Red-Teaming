package com.fnr.controller;

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceException;

import com.fnr.connection.ConnectionFactory;
import com.fnr.dao.DAO;
import com.fnr.enums.Response;
import com.fnr.interfaces.IController;
import com.fnr.interfaces.IDAO;
import com.fnr.model.User;

public class UserController implements IController<User>{
	private IDAO<User> dao;

	public UserController() {
		this.dao = new DAO<User>();
	}

	private boolean verifyData(User user) {
		if (user.getIsAdmin() != null && user.getName() != null && user.getEmail() != null && user.getPassword() != null)
			return true;

		return false;
	}

	@Override
	public Response post(ConnectionFactory conn, User user) {
		if (verifyData(user) && this.dao.post(conn, user))
			return Response.POST_SUCCESS;

		return Response.POST_FAILED;
	}

	@Override
	public Response put(ConnectionFactory conn, User user) {
		if (verifyData(user) && this.dao.put(conn, user)) 
			return Response.UPDATE_SUCCESS;
			
		return Response.UPDATE_FAILED;
	}

	@Override
	public Response delete(ConnectionFactory conn, User user, Integer id) {
		if (verifyData(user) && this.dao.delete(conn, user, id)) 
			return Response.DELETE_SUCCESS;

		return Response.DELETE_FAILED;
	}

	@Override
	public User getById(ConnectionFactory conn, Integer id) {
		if (id != null) {
			EntityManager em = conn.getConnection();
			try {
				return em.find(User.class, id);
			} catch (PersistenceException e) {
				System.out.println("Desfazendo transações... \nMotivo: " + e.getMessage());
				return null;
			} finally {
				em.close();
			}
		}

		return null;
	}

	@Override
	public List<User> getAll(ConnectionFactory conn, User userInstance) {
		return this.dao.getAll(conn, userInstance);
	}
}
