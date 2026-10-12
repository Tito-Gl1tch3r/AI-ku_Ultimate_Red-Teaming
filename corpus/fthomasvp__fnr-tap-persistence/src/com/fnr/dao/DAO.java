package com.fnr.dao;

import java.util.List;

import javax.persistence.EntityManager;
import javax.persistence.PersistenceException;

import com.fnr.connection.ConnectionFactory;
import com.fnr.interfaces.IDAO;

public class DAO<T> implements IDAO<T> {

	@Override
	public boolean post(ConnectionFactory conn, T entity) {
		EntityManager em = conn.getConnection();
		try {
			em.getTransaction().begin();
			em.persist(entity);
			em.getTransaction().commit();
			return true;
		} catch (PersistenceException e) {
			em.getTransaction().rollback();
			e.printStackTrace();
			return false;
		} finally {
			em.close();
		}
		
	}

	@SuppressWarnings("unchecked")
	@Override
	public List<T> getAll(ConnectionFactory conn, T entity) {
		EntityManager em = conn.getConnection();
		try {
			return em.createQuery("from " + entity.getClass().getSimpleName()).getResultList();
		} catch (PersistenceException e) {
			System.out.println("Desfazendo transações... \nMotivo: " + e.getMessage());
			return null;
		} finally {
			em.close();
		}
		
	}

	public boolean put(ConnectionFactory conn, T entity) {
		EntityManager em = conn.getConnection();
		try {
			em.getTransaction().begin();
			em.merge(entity);
			em.getTransaction().commit();
			return true;
		} catch (PersistenceException e) {
			em.getTransaction().rollback();
			System.out.println("Desfazendo transa��es... \nMotivo: " + e.getMessage());
			return false;
		} finally {
			em.close();
		}	
	}

	@Override
	public boolean delete(ConnectionFactory conn, T entity, Integer id) {
		EntityManager em = conn.getConnection();
		try {
			em.getTransaction().begin();
			em.remove(em.find(entity.getClass(), id));
			em.getTransaction().commit();
			return true;
		} catch (PersistenceException e) {
			em.getTransaction().rollback();
			System.out.println("Desfazendo transa��es... \nMotivo: " + e.getMessage());
			return false;
		} finally {
			em.close();
		}
	}
}