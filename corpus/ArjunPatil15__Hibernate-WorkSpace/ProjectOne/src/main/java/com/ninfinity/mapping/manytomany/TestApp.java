package com.ninfinity.mapping.manytomany;

import java.util.ArrayList;
import java.util.List;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

public class TestApp {
	public static void main(String[] args) {

		Configuration cfg= new Configuration();
		cfg.configure("hibernate.cfg.xml");
		SessionFactory sf = cfg.buildSessionFactory();

		Session session = sf.openSession(); 
		Transaction tx = session.beginTransaction();
		
		Employee e1 = new Employee();
		e1.seteId(1);
		e1.setEmpName("Rahul");
		
		Employee e2 = new Employee();
		e2.seteId(2);
		e2.setEmpName("Kunal");
		
		Employee e3 = new Employee();
		e3.seteId(3);
		e3.setEmpName("Soham");
		
		Project p1 = new Project();
		p1.setpId(1);
		p1.setProjName("Library Mangement");
		
		Project p2 = new Project();
		p2.setpId(2);
		p2.setProjName("Hospital Mangement");
		
		Project p3 = new Project();
		p3.setpId(3);
		p3.setProjName("ChatBot Mangement");
		
		List<Employee> eList = new ArrayList<Employee>();
		eList.add(e1);
		eList.add(e2);
		eList.add(e3);
		
		List<Project> pList = new ArrayList<Project>();
		pList.add(p1);
		pList.add(p2);
		pList.add(p3);
		
		
		e1.setaList(pList);
		e2.setaList(pList);
		e3.setaList(pList);
		
		p1.seteList(eList);
		p2.seteList(eList);
		p3.seteList(eList);
		
		session.save(p1);
		session.save(p2);
		session.save(p3);
		session.save(e1);
		session.save(e2);
		session.save(e3);
		
		
		

		tx.commit();
		session.close();
		sf.close();
	}

}
