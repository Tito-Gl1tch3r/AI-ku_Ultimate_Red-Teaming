package com.fnr.controller;

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceException;

import com.fnr.connection.ConnectionFactory;
import com.fnr.dao.DAO;
import com.fnr.enums.Response;
import com.fnr.interfaces.IController;
import com.fnr.interfaces.IDAO;
import com.fnr.model.BicycleStatus;

public class BicycleStatusController implements IController<BicycleStatus>{
	private IDAO<BicycleStatus> dao;

	public BicycleStatusController() {
		this.dao = new DAO<BicycleStatus>();
	}

	private boolean verifyData(BicycleStatus bikeStatus) {
		if (bikeStatus.getBicycleStatus() != null && bikeStatus.getDescription() != null)
			return true;
		return false;
	}

	@Override
	public Response post(ConnectionFactory conn, BicycleStatus bikeStatus) {
		if (verifyData(bikeStatus) && this.dao.post(conn, bikeStatus))
			return Response.POST_SUCCESS;
		return Response.POST_FAILED;
	}

	@Override
	public Response put(ConnectionFactory conn, BicycleStatus bikeStatus) {
		if (verifyData(bikeStatus) && this.dao.put(conn, bikeStatus)) 
			return Response.UPDATE_SUCCESS;
		return Response.UPDATE_FAILED;
	}

	@Override
	public Response delete(ConnectionFactory conn, BicycleStatus bicycleStatus, Integer bicycleStatusId) {
		if (bicycleStatusId != null && this.dao.delete(conn, bicycleStatus, bicycleStatusId)) 
			return Response.DELETE_SUCCESS;
		return Response.DELETE_FAILED;
	}

	@Override
	public BicycleStatus getById(ConnectionFactory conn, Integer id) {
		if (id != null) {
			EntityManager em = conn.getConnection();
			try {
				return em.find(BicycleStatus.class, id);
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
	public List<BicycleStatus> getAll(ConnectionFactory conn, BicycleStatus bicycleStatusInstance) {
		return this.dao.getAll(conn, bicycleStatusInstance);
	}
}