package com.fnr.view;

import java.io.UnsupportedEncodingException;
import java.security.NoSuchAlgorithmException;

import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPasswordField;

import com.fnr.connection.ConnectionFactory;
import com.fnr.exceptions.InvalidUser;
import com.fnr.model.User;
import com.fnr.utils.LoginInfo;
import com.fnr.utils.Utils;

public class ShowLogin {
	
	public static ConnectionFactory showLoginView() {
		
		User user = null;
		LoginInfo login = null;
		ConnectionFactory conn;
		try {
			conn = null;
			do {
				String userName = JOptionPane.showInputDialog(null, "Informe o nome de usuário do banco: (employee | administrator)");
				
				JPanel panel = new JPanel();
				JLabel label = new JLabel("Informe a senha");
				JPasswordField pass = new JPasswordField(10);
				
				panel.add(label);
				panel.add(pass);
				
				String[] options = new String[]{"Confirmar", "Cancelar"};
				int option = JOptionPane.showOptionDialog(null, panel, "Login",
				                         JOptionPane.NO_OPTION, JOptionPane.PLAIN_MESSAGE,
				                         null, options, options[0]);
				
				char[] password = null;
				if(option == 0) {
				    password = pass.getPassword();
				}

				login = new LoginInfo(userName, new String(password));
				
				if(login != null) {
					conn = new ConnectionFactory(login);
					user = getUserBikeStore(conn);
					conn.setUser(user);
				}
			} while (conn == null);
			
			return conn;
			
		} catch (InvalidUser e) {
			JOptionPane.showMessageDialog(null, e.getMessage());
		} catch (Exception e) {
			JOptionPane.showMessageDialog(null, e.getMessage());
		}
		return null;
	}
	
	public static User getUserBikeStore(ConnectionFactory conn) throws NoSuchAlgorithmException, UnsupportedEncodingException {
		String email = JOptionPane.showInputDialog("Informe o email");
		
		JPanel panel = new JPanel();
		JLabel label = new JLabel("Informe a senha");
		JPasswordField pass = new JPasswordField(10);
		
		panel.add(label);
		panel.add(pass);
		
		String[] options = new String[]{"Confirmar", "Cancelar"};
		int option = JOptionPane.showOptionDialog(null, panel, "Login",
		                         JOptionPane.NO_OPTION, JOptionPane.PLAIN_MESSAGE,
		                         null, options, options[0]);
		
		char[] password = null;
		if(option == 0) {
		    password = pass.getPassword();
		}

		return Utils.authUser(conn, email, Utils.encryptPassword(new String(password)));
	}
}