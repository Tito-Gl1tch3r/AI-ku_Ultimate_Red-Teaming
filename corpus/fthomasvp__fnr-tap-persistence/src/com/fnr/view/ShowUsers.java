package com.fnr.view;

import java.io.UnsupportedEncodingException;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.List;

import javax.swing.JOptionPane;

import com.fnr.connection.ConnectionFactory;
import com.fnr.controller.UserController;
import com.fnr.interfaces.IController;
import com.fnr.model.User;
import com.fnr.utils.Utils;

public class ShowUsers {
	static IController<User> userController = new UserController();
	
	public static void showUsersView(ConnectionFactory conn) {
		
		int menuOption = 0;
		do {
			menuOption = Integer.parseInt(JOptionPane.showInputDialog(null, "Digite uma opção:"
					+ "\n1 - Cadastrar"
					+ "\n2 - Listar"
					+ "\n3 - Buscar por código"
					+ "\n4 - Atualizar"
					+ "\n5 - Remover"
					+ "\n\n0 - Voltar"));
			
			switch(menuOption) {
				case 1:
					try {
						JOptionPane.showMessageDialog(null, postUser(conn));
					}catch(NoSuchAlgorithmException | UnsupportedEncodingException e) {
						e.printStackTrace();
					}
					break;
					
				case 2:
					listUsers(conn);
					break;
					
				case 3:
					listById(conn);
					break;
					
				case 4:
					try {
						JOptionPane.showMessageDialog(null, update(conn));
					}catch(NoSuchAlgorithmException | UnsupportedEncodingException e) {
						e.printStackTrace();
					}
					break;
				
				case 5:
					JOptionPane.showMessageDialog(null, remove(conn));
					break;
					
				case 0:
					break;
				
				default: JOptionPane.showMessageDialog(null, "Informe uma opção válida!");
			}
			
		}while(menuOption != 0);
		
	}
	
	private static String remove(ConnectionFactory conn) {
		if(conn.getUser().getIsAdmin()) {
			int userId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do usuário"));
			User user = userController.getById(conn, userId);
			
			return userController.delete(conn, user, userId).getMessage();
			
		}else {
			return "Empregado não pode realizar alterações no banco";
		}
	}
	
	private static String update(ConnectionFactory conn) throws NoSuchAlgorithmException, UnsupportedEncodingException {
		if(conn.getUser().getIsAdmin()) {
			int userId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do usuário"));
			User user = userController.getById(conn, userId);
			
			String name = JOptionPane.showInputDialog("Informe o nome \n-->Nome atual: "+user.getName());
			user.setName(name);
			String email = JOptionPane.showInputDialog("Informe o email \n-->EMail atual: "+user.getEmail());
			user.setEmail(email);
			String password = JOptionPane.showInputDialog("Informe o email \n-->Senha atual: "+user.getPassword());
			user.setPassword(Utils.encryptPassword(password));
			boolean isAdmin = Boolean.parseBoolean(JOptionPane.showInputDialog("Informe se é Administrador \n-->Cargo atual: "+user.getIsAdmin()));
			user.setIsAdmin(isAdmin);
			
			user.setDateTimeUpdate(LocalDateTime.now());
			user.setDateTimeUpdateUserId(conn.getUser().getUserId());	
			
			return userController.put(conn, user).getMessage();
		}else {
			return "Empregado não pode realizar alterações no banco";
		}
		
	}
	
	private static void listById(ConnectionFactory conn) {
		if(conn.getUser() != null) {
			
			int userId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do usuário"));
			User u = userController.getById(conn, userId);
			
			JOptionPane.showMessageDialog(null, "ID: "+u.getUserId() +" | Nome: "+u.getName()+" | Email: "+u.getEmail()+" | É administrador: "+u.getIsAdmin());
		}
	}
	
	private static void listUsers(ConnectionFactory conn) {
			List<User> users = userController.getAll(conn, new User());
			
			if(users.isEmpty()) {
				
				JOptionPane.showMessageDialog(null, "Não há usuários cadastrados");
			}else {
				
				for (User u : users) {
					System.out.println("ID: "+u.getUserId() +"\tNome: "+u.getName()+"\tEmail: "+u.getEmail()+"\tÉ Administrador: "+u.getIsAdmin());
				}
			}
	}
	
	private static String postUser(ConnectionFactory conn) throws NoSuchAlgorithmException, UnsupportedEncodingException {
		if(conn.getUser().getIsAdmin()) {
			String name = JOptionPane.showInputDialog(null, "Informe o nome");
			String email = JOptionPane.showInputDialog(null, "Informe o email");
			String password = JOptionPane.showInputDialog(null, "Informe a senha");
			boolean isAdmin = Boolean.parseBoolean(JOptionPane.showInputDialog("É administrador? \nTrue (SIM) \nFalse (NÃO)"));
			
			User user = new User(name, email, Utils.encryptPassword(password), isAdmin);
			user.setDateTimeCreation(LocalDateTime.now());
			user.setDateTimeCreationUserId(conn.getUser().getUserId());		
			
			return userController.post(conn, user).getMessage();
		}else {
			return "Empregado não pode realizar alterações no banco";
		}
	}
}
