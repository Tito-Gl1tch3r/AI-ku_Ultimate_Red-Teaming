package com.fnr.view;

import javax.swing.JOptionPane;

import com.fnr.connection.ConnectionFactory;

public class BikeStoreDemo {

	public static void main(String[] args) {
		
		ConnectionFactory conn = null; 
		try {
			
			do {
				conn = ShowLogin.showLoginView();
			}while(conn == null);

			int menuOption;
			do {
				menuOption = Integer.parseInt(JOptionPane.showInputDialog(null, "Cargo: " + conn.getUserPu() 
				+"\n\nDigite uma opção:"
						+ "\n1 - Bicicletas"
						+ "\n2 - Atendimentos"
						+ "\n3 - Clientes"
						+ "\n4 - Usuários"
						+ "\n0 - Logout"
						+ "\n\n-1 - SAIR"));
				
				switch(menuOption) {
					case 1:
						ShowBicycles.showBicyclesView(conn);
						break;
						
					case 2:
						ShowAttends.showAttendsView(conn);
						break;
						
					case 3:
						ShowCustomers.showCustomersView(conn);
						break;
						
					case 4:
						ShowUsers.showUsersView(conn);
						break;
						
					case 0:
						conn.getEMFactory().close();
						conn = ShowLogin.showLoginView();
						break;
						
					case -1:
						conn.getEMFactory().close();
						break;
						
					default: JOptionPane.showMessageDialog(null, "Informe um valor válido!");
				}
					
			}while(menuOption != -1);
				
		} catch(Exception e1) {
			JOptionPane.showMessageDialog(null, e1.getMessage());
		}finally {
			conn.getEMFactory().close();
		}

	}

}
