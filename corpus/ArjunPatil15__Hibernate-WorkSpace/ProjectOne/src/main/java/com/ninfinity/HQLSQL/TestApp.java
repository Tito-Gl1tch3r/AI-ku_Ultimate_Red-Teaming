package com.ninfinity.HQLSQL;

import java.util.Iterator;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

public class TestApp {
	public static void main(String[] args) {
		Configuration cfg = new Configuration();
        cfg.configure("hibernate.cfg.xml");
        SessionFactory sf = cfg.buildSessionFactory();
        
        Session session = sf.openSession();
        Transaction tx = session.beginTransaction();
        
		/*
		 * Teacher t1 = new Teacher(1, "Arjun", "Pune", "Math", "arjun@gmail.com");
		 * Teacher t2 = new Teacher(2, "Ram", "Pune", "Python", "ram@gmail.com");
		 * Teacher t3 = new Teacher(3, "Karan", "Nashik", "OOP", "karan@gmail.com");
		 * Teacher t4 = new Teacher(4, "Mohan", "Mumbai", "DSA", "Mohan@gmail.com");
		 * Teacher t5 = new Teacher(5, "Kunal", "Pune", "Java", "kunal@gmail.com");
		 * 
		 * session.save(t1); session.save(t2); session.save(t3); session.save(t4);
		 * session.save(t5);
		 */
        
        int id; 
        String name;
    	String city;
    	String subject;
    	String email;
        
        for(int i = 6; i<=25;i++) {
        	
        	Teacher t = new Teacher();
        	
        	id = i;
        	name = "Arjun" + i;
        	city = "Pune" + i;
        	subject = "Java" + i;
        	email = "arjun" + i + "@gmail.com";
        	
        	t.setId(id);
        	t.setName(name);
        	t.setCity(city);
        	t.setSubject(subject);
        	t.setEmail(email);
        	
        	session.save(t);
        }
        
        tx.commit();
		session.close();
		sf.close();
	}

}
