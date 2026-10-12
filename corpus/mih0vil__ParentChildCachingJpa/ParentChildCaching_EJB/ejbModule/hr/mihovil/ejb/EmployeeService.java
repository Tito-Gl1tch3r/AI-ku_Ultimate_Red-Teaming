package hr.mihovil.ejb;

import java.util.List;

import javax.ejb.LocalBean;
import javax.ejb.Stateless;
import javax.ejb.TransactionAttribute;
import javax.ejb.TransactionAttributeType;
import javax.persistence.EntityManager;
import javax.persistence.PersistenceContext;

import hr.mih0vil.parentchild.Department;
import hr.mih0vil.parentchild.Employee;
import hr.mih0vil.parentchild.EmployeeWithDeparment;

/**
 * Session Bean implementation class EmployeeService
 */
@Stateless
@LocalBean
public class EmployeeService {
	
	@PersistenceContext
	EntityManager em;

    public EmployeeService() {
    	System.out.println("EmployeeService()");
    }

    public List<Employee> getEmployeesHigherPayed() {
    	return em.createNamedQuery("Employee.getHigherPayed", 
    			Employee.class).getResultList();
    }
    
    public List<Department> getDepartmentsForEmployeesHigherPayed() {
    	return em.createNamedQuery("Department.Employee.getHigherPayed", 
    			Department.class).getResultList();
    }
    
    @TransactionAttribute(TransactionAttributeType.NOT_SUPPORTED)   
    public List<Employee> getEmployeesHigherPayedWithDeparments() {
    	List<Employee> emps = getEmployeesHigherPayed(); //get employees
    	List<Department> deps = getDepartmentsForEmployeesHigherPayed(); //get departments to which retrieved employees relate to
    	for (Employee e: emps) {
    		e.getDepartment(); //get the department from cache now while we are in the transaction
    	}
    	return emps;
    }
    
    @TransactionAttribute(TransactionAttributeType.NOT_SUPPORTED)   
    public List<EmployeeWithDeparment> getHigherPayedEmpoyeesWithDepartment() {
    	return em.createNamedQuery("EmployeeWithDeparment.getHigherPayed", 
    			EmployeeWithDeparment.class).getResultList();
    }
    
    
    
}
