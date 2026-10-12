package com.ninfinity.criteria;

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
        
        int rollNumber;
    	String name;
    	String branch;
    	int marks;
    	
    	for(int i = 0;i<=20;i++) {
    		Student s1 = new Student();
    		s1.setRollNumber(i);
    		s1.setName("Arjun" + i);
    		
    		if(i%5==0) {
    			s1.setBranch("Comp");
    		}else if(i%3==0){
    			s1.setBranch("ETC");
    		}else {
    			s1.setBranch("Mech");
    		}
    		
    		marks = (int)(Math.random() *100);
        	s1.setMarks(marks);
            
        	session.save(s1);
    	}
    	
    	
        
        tx.commit();
		session.close();
		sf.close();
	}

}
