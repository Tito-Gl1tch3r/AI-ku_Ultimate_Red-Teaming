package com.ninfinity.mapping.onetomany;

import java.util.ArrayList;
import java.util.List;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

public class TestApp2 {
	public static void main(String[] args) {
		
		Configuration cfg= new Configuration();
		cfg.configure("hibernate.cfg.xml");
		SessionFactory sf = cfg.buildSessionFactory();

		Session session = sf.openSession(); 
		Transaction tx = session.beginTransaction();
		
//		Person p1 = new Person();
//		p1.setpId(1);
//		p1.setName("Arjun");
//		
//		Address a1 = new Address();
//		a1.setaId(1);
//		a1.setCity("Pune");
//		a1.setPerson(p1);
//		
//		Address a2 = new Address();
//		a2.setaId(2);
//		a2.setCity("Mumbai");
//		a2.setPerson(p1);
//		
//		List<Address> aList = new ArrayList<Address>();
//		aList.add(a1);
//		aList.add(a2);
//		
//		p1.setAddList(aList);
//		
//		session.save(p1);
//		session.save(a1);
//		session.save(a2);
//		
//		tx.commit();
		
		Person p1 = session.get(Person.class, 1);
		
		System.out.println("Person ID is : "+ p1.getpId());
		System.out.println("person name is : "+ p1.getName());
		
		System.out.println(p1.getAddList().size());
		
		session.close();
		sf.close();
	}

}
