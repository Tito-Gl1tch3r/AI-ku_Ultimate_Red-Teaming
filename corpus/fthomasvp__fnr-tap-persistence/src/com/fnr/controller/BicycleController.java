package com.fnr.controller;

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceException;

import com.fnr.connection.ConnectionFactory;
import com.fnr.dao.DAO;
import com.fnr.enums.Response;
import com.fnr.interfaces.IController;
import com.fnr.interfaces.IDAO;
import com.fnr.model.Bicycle;

public class BicycleController implements IController<Bicycle>{
	private IDAO<Bicycle> dao;

	public BicycleController() {
		this.dao = new DAO<Bicycle>();
	}

	private boolean verifyData(Bicycle bike) {
		if (bike.getBicycleStatus() != null && bike.getBrand() != null && bike.getColor() != null && bike.getModel() != null)
			return true;
		return false;
	}

	@Override
	public Response post(ConnectionFactory conn, Bicycle bike) {
		if (verifyData(bike) && this.dao.post(conn, bike))
			return Response.POST_SUCCESS;
		return Response.POST_FAILED;
	}

	@Override
	public Response put(ConnectionFactory conn, Bicycle bike) {
		if (verifyData(bike) && this.dao.put(conn, bike)) 
			return Response.UPDATE_SUCCESS;
		return Response.UPDATE_FAILED;
	}

	@Override
	public Response delete(ConnectionFactory conn, Bicycle bicycle, Integer bicycleId) {
		if (bicycleId != null && this.dao.delete(conn, bicycle, bicycleId)) 
			return Response.DELETE_SUCCESS;
		return Response.DELETE_FAILED;
	}

	@Override
	public Bicycle getById(ConnectionFactory conn, Integer id) {
		if (id != null) {
			EntityManager em = conn.getConnection();
			try {
				return em.find(Bicycle.class, id);
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
	public List<Bicycle> getAll(ConnectionFactory conn, Bicycle bicycleInstance) {
		return this.dao.getAll(conn, bicycleInstance);
	}
}