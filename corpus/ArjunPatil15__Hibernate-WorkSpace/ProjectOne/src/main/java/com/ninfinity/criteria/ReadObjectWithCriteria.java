package com.ninfinity.criteria;

import java.util.List;

import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.Root;

import org.hibernate.Criteria;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Projection;
import org.hibernate.criterion.Projections;
import org.hibernate.criterion.Restrictions;
import org.hibernate.query.Query;

public class ReadObjectWithCriteria {
	public static void main(String[] args) {
		Configuration cfg = new Configuration();
        cfg.configure("hibernate.cfg.xml");
        SessionFactory sf = cfg.buildSessionFactory();
        
        Session session = sf.openSession();
        Transaction tx = session.beginTransaction();
        
        Criteria criteria=  session.createCriteria(Student.class);
        
//        criteria.setFirstResult(5);
//        criteria.setMaxResults(15);
    
//        criteria.add(Restrictions.gt("marks",28));

//        criteria.addOrder(Order.asc("marks"));
  
//        criteria.setProjection(Projections.property("name"));
        
//        There are many more api to explore
        
//        List<String> list = criteria.list();  
//        
//        for(String s : list) {
//        	System.out.println(s);
//        }
        
        
        CriteriaBuilder criteriaBuilder = session.getCriteriaBuilder();
        
        CriteriaQuery<Student> createQuery = criteriaBuilder.createQuery(Student.class);
        
        Root<Student> root = createQuery.from(Student.class);
        
        createQuery.select(root);
        
        Query<Student> query = session.createQuery(createQuery);
        
        List<Student> resultList = query.getResultList();
        
        for(Student s : resultList) {
        	System.out.println(s);
        }
        
        session.close();
		sf.close();
	}
}
