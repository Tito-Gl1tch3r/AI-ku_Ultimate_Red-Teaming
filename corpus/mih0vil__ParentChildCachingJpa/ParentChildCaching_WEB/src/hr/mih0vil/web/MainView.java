package hr.mih0vil.web;

import java.io.Serializable;
import java.util.List;

import javax.ejb.EJB;
import javax.faces.event.ActionEvent;
import javax.inject.Named;

import org.omnifaces.cdi.ViewScoped;

import hr.mih0vil.parentchild.Employee;
import hr.mih0vil.parentchild.EmployeeWithDeparment;
import hr.mihovil.ejb.EmployeeService;

@Named
@ViewScoped
public class MainView implements Serializable{

	private static final long serialVersionUID = 1L;
	
	@EJB
	EmployeeService employeeService;
	
	private List<Employee> employees;
	private List<EmployeeWithDeparment> employeesWithDeparment;
	
	public void test(ActionEvent event) {
		try {
			System.out.println("test()");
			employees = employeeService.getEmployeesHigherPayedWithDeparments();
			employeesWithDeparment = employeeService.getHigherPayedEmpoyeesWithDepartment();
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	public List<Employee> getEmployees() {
		return employees;
	}

	public void setEmployees(List<Employee> employees) {
		this.employees = employees;
	}

	public List<EmployeeWithDeparment> getEmployeesWithDeparment() {
		return employeesWithDeparment;
	}

	public void setEmployeesWithDeparment(List<EmployeeWithDeparment> employeesWithDeparment) {
		this.employeesWithDeparment = employeesWithDeparment;
	}
}
