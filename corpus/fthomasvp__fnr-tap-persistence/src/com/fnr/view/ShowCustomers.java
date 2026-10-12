package com.fnr.view;

import java.time.LocalDateTime;
import java.util.List;

import javax.swing.JOptionPane;

import com.fnr.connection.ConnectionFactory;
import com.fnr.controller.CustomerController;
import com.fnr.interfaces.IController;
import com.fnr.model.Customer;

public class ShowCustomers {
static IController<Customer> customerController = new CustomerController();
	
	public static void showCustomersView(ConnectionFactory conn) {
		
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
					JOptionPane.showMessageDialog(null, postCustomer(conn));
					break;
					
				case 2:
					listCustomers(conn);
					break;
					
				case 3:
					listById(conn);
					break;
					
				case 4:
					JOptionPane.showMessageDialog(null, update(conn));
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
	
	protected static String remove(ConnectionFactory conn) {
		if(conn.getUser().getIsAdmin()) {
			int customerId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do cliente"));
			Customer customer = customerController.getById(conn, customerId);
			
			return customerController.delete(conn, customer, customerId).getMessage();
			
		}else {
			return "Empregado não pode realizar alterações no banco";
		}
	}
	
	protected static String update(ConnectionFactory conn) {
		if(conn.getUser().getIsAdmin()) {
			int customerId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do cliente"));
			Customer customer = customerController.getById(conn, customerId);
			
			String name = JOptionPane.showInputDialog("Informe o nome \n-->Nome atual: "+customer.getName());
			customer.setName(name);
			String email = JOptionPane.showInputDialog("Informe o email \n-->EMail atual: "+customer.getEmail());
			customer.setEmail(email);
			String phone = JOptionPane.showInputDialog("Informe o email \n-->Celular atual: "+customer.getPhone());
			customer.setPhone(phone);
			String residencialPhone = JOptionPane.showInputDialog("Informe o email \n-->Email atual: "+customer.getResidencial_Phone());
			customer.setPhone(residencialPhone);
			String address = JOptionPane.showInputDialog("Informe o endereço \n-->Endereço atual: "+customer.getAddress());
			customer.setAddress(address);
			
			customer.setDateTimeUpdate(LocalDateTime.now());
			customer.setDateTimeUpdateUserId(conn.getUser().getUserId());	
			
			return customerController.put(conn, customer).getMessage();
		}else {
			return "Empregado não pode realizar alterações no banco";
		}
		
	}
	
	protected static void listById(ConnectionFactory conn) {
		if(conn.getUser() != null) {
			
			int customerId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do cliente"));
			Customer c = customerController.getById(conn, customerId);
			
			JOptionPane.showMessageDialog(null, "ID: "+c.getcustomerId() +" | Nome: "+c.getName()+" | Endereço: "+c.getAddress() + " | Celular: "+c.getPhone());
		}
	}
	
	protected static void listCustomers(ConnectionFactory conn) {
			List<Customer> customers = customerController.getAll(conn, new Customer());
			
			if(customers.isEmpty()) {
				
				JOptionPane.showMessageDialog(null, "Não há clientes cadastrados");
			}else {
				
				for (Customer c : customers) {
					System.out.println("ID: "+c.getcustomerId() +"\tNome: "+c.getName()+"\tEndereço: "+c.getEmail()+"\tCelular: "+c.getPhone());
				}
			}
	}
	
	protected static String postCustomer(ConnectionFactory conn) {
		if(conn.getUser().getIsAdmin()) {
			String name = JOptionPane.showInputDialog(null, "Informe o nome");
			String email = JOptionPane.showInputDialog(null, "Informe o email");
			String phone = JOptionPane.showInputDialog(null, "Informe o número do celular");
			String residencialPhone = JOptionPane.showInputDialog(null, "Informe o número do telefone residencial");
			String address = JOptionPane.showInputDialog(null, "Informe o endereço completo \nEx.: Rua da Harmonia, 305. Casa Amarela");
			
			Customer customer = new Customer(name, email, phone, residencialPhone, address);
			customer.setDateTimeCreation(LocalDateTime.now());
			customer.setDateTimeCreationUserId(conn.getUser().getUserId());		
			
			return customerController.post(conn, customer).getMessage();
		}else {
			return "Empregado não pode realizar alterações no banco";
		}
	}
}
