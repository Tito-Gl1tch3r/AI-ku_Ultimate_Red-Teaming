package com.fnr.controller;

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceException;

import com.fnr.connection.ConnectionFactory;
import com.fnr.dao.DAO;
import com.fnr.enums.Response;
import com.fnr.interfaces.IController;
import com.fnr.interfaces.IDAO;
import com.fnr.model.Attend;

public class AttendController implements IController<Attend>{
	private IDAO<Attend> dao;

	public AttendController() {
		this.dao = new DAO<Attend>();
	}

	private boolean verifyData(Attend att) {
		if (att.getBicycle() != null && att.getBicycleStatus() != null && att.getCustomer() != null && att.getValue() != null)
			return true;
		return false;
	}

	@Override
	public Response post(ConnectionFactory conn, Attend att) {
		if (verifyData(att) && this.dao.post(conn, att))
			return Response.POST_SUCCESS;
		return Response.POST_FAILED;
	}

	@Override
	public Response put(ConnectionFactory conn, Attend att) {
		if (verifyData(att) && this.dao.put(conn, att)) 
			return Response.UPDATE_SUCCESS;
		return Response.UPDATE_FAILED;
	}

	@Override
	public Response delete(ConnectionFactory conn, Attend att, Integer attendId) {
		if (attendId != null && this.dao.delete(conn, att, attendId)) 
			return Response.DELETE_SUCCESS;
		return Response.DELETE_FAILED;
	}

	@Override
	public Attend getById(ConnectionFactory conn, Integer id) {
		if (id != null) {
			EntityManager em = conn.getConnection();
			try {
				return em.find(Attend.class, id);
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
	public List<Attend> getAll(ConnectionFactory conn, Attend attInstance) {
		return this.dao.getAll(conn, attInstance);
	}
}