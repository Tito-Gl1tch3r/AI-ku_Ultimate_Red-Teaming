package com.fnr.connection;

import javax.persistence.EntityManager;
import javax.persistence.EntityManagerFactory;
import javax.persistence.Persistence;

import com.fnr.exceptions.InvalidUser;
import com.fnr.model.User;
import com.fnr.utils.LoginInfo;

public class ConnectionFactory {
	private String userPU;
	private User user;
	private EntityManagerFactory emf;
	
	public ConnectionFactory() {}
	public ConnectionFactory(LoginInfo login) throws InvalidUser {
		definePuUnit(login);
	}
	
	public void definePuUnit(LoginInfo login) throws InvalidUser {
		if(LoginInfo.userName.equals("administrator") && LoginInfo.password.equals("4567")) {
			this.userPU = "Administrador";
			this.emf = Persistence.createEntityManagerFactory("administratorPU");
			
		}else if(LoginInfo.userName.equals("employee") && LoginInfo.password.equals("7654")){
			this.userPU = "Empregado";
			this.emf = Persistence.createEntityManagerFactory("employeePU");
			
		}else {
			throw new InvalidUser("Usuário não cadastrado no banco de dados");
		}
	}
	
	public EntityManager getConnection() {
		return this.emf.createEntityManager();
	}
	public EntityManagerFactory getEMFactory() {
		return this.emf;
	}
	public String getUserPu() {
		return userPU;
	}
	public User getUser() {
		return user;
	}
	public void setUser(User user) {
		this.user = user;
	}
	
}
