package com.ninfinity.criteria;

import java.util.List;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.hibernate.query.Query;

public class ReadObjects {
	public static void main(String[] args) {
		Configuration cfg = new Configuration();
        cfg.configure("hibernate.cfg.xml");
        SessionFactory sf = cfg.buildSessionFactory();
        
        Session session = sf.openSession();
        Transaction tx = session.beginTransaction();
        
//        String hql = "from Student";
//        
//        Query query = session.createQuery(hql);
        
//        Query query = session.createNamedQuery("getAllStudents");
//        
//        List<Student> list =  query.list();
//        
//        for(Student s : list) {
//        	System.out.println(s);
//        }
//        
     
//        
//        String hql = "from Student as s where s.rollNumber = :y";
//        
//        Query query2 = session.createQuery(hql);
//       
        Query query2 = session.createNamedQuery("getStudentByRollNumber");
        
        query2.setParameter("y", 4);
        
        Student uniqueResult = (Student)query2.uniqueResult();
        
        System.out.println(uniqueResult);
        
        session.close();
		sf.close();
	}

}
