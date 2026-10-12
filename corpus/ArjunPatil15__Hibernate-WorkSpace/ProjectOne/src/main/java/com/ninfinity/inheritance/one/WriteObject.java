package com.ninfinity.inheritance.one;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

public class WriteObject {
	public static void main(String[] args) {
		Configuration cfg = new Configuration();
        cfg.configure("hibernate.cfg.xml");
        SessionFactory sf = cfg.buildSessionFactory();
        
        Session session = sf.openSession();
        Transaction tx = session.beginTransaction();
        
        
        Employee e1 = new Employee();
        e1.setId(1);
        e1.setName("Karan");
        e1.setCity("Pune");
        e1.setDept("HR");
        e1.setSalary(100000);
        
        
        Student s1 = new Student();
        s1.setId(2);
        s1.setName("Kunal");
        s1.setCity("Mumbai");
        s1.setBranch("Computer");
        s1.setMarks(99);
        
        
        session.save(s1);
        session.save(e1);
        
        tx.commit();
		session.close();
		sf.close();
	}

}
