package com.fnr.view;

import java.time.LocalDateTime;
import java.util.List;

import javax.swing.JOptionPane;

import com.fnr.connection.ConnectionFactory;
import com.fnr.controller.AttendController;
import com.fnr.controller.BicycleController;
import com.fnr.controller.BicycleStatusController;
import com.fnr.controller.CustomerController;
import com.fnr.interfaces.IController;
import com.fnr.model.Attend;
import com.fnr.model.Bicycle;
import com.fnr.model.BicycleStatus;
import com.fnr.model.Customer;

public class ShowAttends {
	static IController<Attend> attendController = new AttendController();
	static IController<Bicycle> bicycleController = new BicycleController();
	static IController<BicycleStatus> bicycleStatusController = new BicycleStatusController();
	static IController<Customer> customerController = new CustomerController();

	public static void showAttendsView(ConnectionFactory conn) {

		int menuOption = 0;
		do {
			menuOption = Integer
					.parseInt(JOptionPane.showInputDialog(null, "Digite uma opção:" + "\n1 - Cadastrar" + "\n2 - Listar"
							+ "\n3 - Buscar por código" + "\n4 - Atualizar" + "\n5 - Remover" + "\n\n0 - Voltar"));

			switch (menuOption) {
			case 1:
				JOptionPane.showMessageDialog(null, postAttend(conn));
				break;

			case 2:
				listAttends(conn);
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

			default:
				JOptionPane.showMessageDialog(null, "Informe uma opção válida!");
			}

		} while (menuOption != 0);

	}

	private static String remove(ConnectionFactory conn) {
		if (conn.getUser().getIsAdmin()) {
			int attendId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do atendimento"));
			Attend attend = attendController.getById(conn, attendId);

			return attendController.delete(conn, attend, attendId).getMessage();

		} else {
			
			return "Empregado não pode realizar alterações no banco";
		}
	}

	private static String update(ConnectionFactory conn) {
		if (conn.getUser().getIsAdmin()) {
			System.out.println("------------------------Atendimentos--------------------------------");
			listAttends(conn);
			int attendId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do atendimento"));
			Attend attend = attendController.getById(conn, attendId);
			
			Double value = Double.parseDouble(JOptionPane.showInputDialog("Informe o valor do atendimento (R$) \nValor atual: "+attend.getValue()));
			attend.setValue(value);
			
			int bicycleStatusId = Integer.parseInt(JOptionPane.showInputDialog("Informe o Status ID da Bicicleta \n--> ID Status Atual: " 
			+ attend.getBicycleStatus().getBicycleStatus() + " - " + attend.getBicycleStatus().getBicycleStatusId()));
			BicycleStatus bicycleStatus = bicycleStatusController.getById(conn, bicycleStatusId);
			
			int bicycleId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID da Bicicleta \n--> ID bicicleta Atual: " + attend.getBicycle().getBicycleId()));
			Bicycle bicycle = bicycleController.getById(conn, bicycleId);
			
			attend.setBicycleStatus(bicycleStatus);
			attend.setBicycle(bicycle);
			
			attend.setDateTimeUpdate(LocalDateTime.now());
			attend.setDateTimeUpdateUserId(conn.getUser().getUserId());

			return attendController.put(conn, attend).getMessage();
		} else {
			
			return "Empregado não pode realizar alterações no banco";
		}

	}

	private static void listById(ConnectionFactory conn) {
		if (conn.getUser() != null) {

			int attendId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do atendimento"));
			Attend a = attendController.getById(conn, attendId);

			JOptionPane.showMessageDialog(null, "ID: " + a.getAttendId() + " | Nome do cliente: "
					+ a.getCustomer().getName() + " | Valor Total: " + a.getValue());
		}
	}

	private static void listAttends(ConnectionFactory conn) {
		List<Attend> attends = attendController.getAll(conn, new Attend());

		if (attends.isEmpty()) {

			JOptionPane.showMessageDialog(null, "Não há atendimentos cadastrados");
		} else {

			for (Attend a : attends) {
				System.out.println("ID: " + a.getAttendId() + " | Nome do cliente: " + a.getCustomer().getName()
						+ " | Bicicleta:  " + a.getBicycle().getBrand() + " - " + a.getBicycle().getModel()
						+ " | Valor Total: " + a.getValue());
			}
		}
	}

	private static String postAttend(ConnectionFactory conn) {
		if (conn.getUser().getIsAdmin()) {

			System.out.println("------------------------Bicicletas--------------------------------");

			ShowBicycles.listBicycles(conn);
			int bicycleId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID da bicicleta"));
			Bicycle bicycle = bicycleController.getById(conn, bicycleId);

			System.out.println("\n------------------------Status das Bicicletas--------------------------------");

			List<BicycleStatus> bStatus = bicycleStatusController.getAll(conn, new BicycleStatus());
			for (BicycleStatus b : bStatus) {
				System.out.println("Status: " + b.getBicycleStatus() + "\tDescri��o: " + b.getDescription() + "\tID: "
						+ b.getBicycleStatusId());
			}
			int bicycleStatusId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do status da bicicleta"));
			BicycleStatus bicycleStatus = bicycleStatusController.getById(conn, bicycleStatusId);

			System.out.println("\n------------------------Clientes--------------------------------");

			ShowCustomers.listCustomers(conn);
			int customerId = Integer.parseInt(JOptionPane.showInputDialog("Informe o ID do cliente"));
			Customer customer = customerController.getById(conn, customerId);

			Double value = Double.parseDouble(JOptionPane.showInputDialog("Informe o valor do atendimento (R$)"));

			Attend attend = new Attend(bicycle, bicycleStatus, customer, value);
			attend.setDateTimeCreation(LocalDateTime.now());
			attend.setDateTimeCreationUserId(conn.getUser().getUserId());

			return attendController.post(conn, attend).getMessage();
		} else {
			
			return "Empregado não pode realizar alterações no banco";
		}
	}
}
