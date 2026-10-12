package hr.mih0vil.parentchild;

import java.io.Serializable;
import java.math.BigDecimal;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.NamedNativeQueries;
import javax.persistence.NamedNativeQuery;


/**
 * The persistent class for the EMPLOYEES database table.
 * 
 */
@Entity
@NamedNativeQueries({
	@NamedNativeQuery(name="EmployeeWithDeparment.getHigherPayed", resultClass=EmployeeWithDeparment.class, query=
			"select E.EMPLOYEE_ID, E.FIRST_NAME, E.LAST_NAME, E.SALARY, D.DEPARTMENT_NAME \r\n" + 
			"from EMPLOYEES e \r\n" + 
			"join DEPARTMENTS d  on  E.DEPARTMENT_ID =   D.DEPARTMENT_ID \r\n" + 
			"where 1=1 \r\n" + 
			"and E.SALARY > 10000 \r\n" + 
			"")
})
public class EmployeeWithDeparment implements Serializable {
	private static final long serialVersionUID = 1L;

	@Id
	@Column(name="EMPLOYEE_ID")
	private Long employeeId;

	@Column(name="FIRST_NAME")
	private String firstName;

	@Column(name="LAST_NAME")
	private String lastName;

	private BigDecimal salary;

	@Column(name="DEPARTMENT_NAME")
	private String departmentName;

	public EmployeeWithDeparment() {
	}

	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + ((employeeId == null) ? 0 : employeeId.hashCode());
		return result;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		EmployeeWithDeparment other = (EmployeeWithDeparment) obj;
		if (employeeId == null) {
			if (other.employeeId != null)
				return false;
		} else if (!employeeId.equals(other.employeeId))
			return false;
		return true;
	}

	@Override
	public String toString() {
		return "EmployeeWithDeparment [employeeId=" + employeeId + ", firstName=" + firstName + ", lastName=" + lastName
				+ ", salary=" + salary + ", departmentName=" + departmentName + "]";
	}

	public Long getEmployeeId() {
		return employeeId;
	}

	public void setEmployeeId(Long employeeId) {
		this.employeeId = employeeId;
	}

	public String getFirstName() {
		return firstName;
	}

	public void setFirstName(String firstName) {
		this.firstName = firstName;
	}

	public String getLastName() {
		return lastName;
	}

	public void setLastName(String lastName) {
		this.lastName = lastName;
	}

	public BigDecimal getSalary() {
		return salary;
	}

	public void setSalary(BigDecimal salary) {
		this.salary = salary;
	}

	public String getDepartmentName() {
		return departmentName;
	}

	public void setDepartmentName(String departmentName) {
		this.departmentName = departmentName;
	}
	

}
