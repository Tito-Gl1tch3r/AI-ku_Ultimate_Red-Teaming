package com.ninfinity.inheritance.three;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

public class ReadObject {
	public static void main(String[] args) {
		Configuration cfg = new Configuration();
        cfg.configure("hibernate.cfg.xml");
        SessionFactory sf = cfg.buildSessionFactory();
        
        Session session = sf.openSession();
        Transaction tx = session.beginTransaction();
        
       int id = 1;
       
       Person p = session.get(Person.class, id);
       
       if((p instanceof Person) && !(p instanceof Employee) && !(p instanceof Student)) {
    	   System.out.println("This is Person Object");
    	   System.out.println(p);
       }else if((p instanceof Person) && (p instanceof Employee) && !(p instanceof Student)) {
    	   System.out.println("This is Employee Object");
    	   System.out.println(p);
       }else if((p instanceof Person) && !(p instanceof Employee) && (p instanceof Student)) {
    	   System.out.println("This is Student Object");
    	   System.out.println(p);
       }else {
    	   System.out.println("No Object present with id :"+ id);
       }
        
        
//        tx.commit();
		session.close();
		sf.close();
	}

}
