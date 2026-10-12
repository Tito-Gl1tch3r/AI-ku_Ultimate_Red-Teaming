package com.ninfinity.mapping.onetomany;

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
		
		Question q1 = new Question();
		q1.setQid(1);
		q1.setQues("What is an Interface ?");
		
		Answer a1 = new Answer();
		a1.setAid(1);
		a1.setAns("Its 100% abstract Class");
		
		Answer a2 = new Answer();
		a2.setAid(2);
		a2.setAns("Goes with policy of one decl and multiple Implementation");
		
		Answer a3 = new Answer();
		a3.setAid(3);
		a3.setAns("Its says what to do without saying how it can be done");
		
		List<Answer> aList = new ArrayList<Answer>();
		aList.add(a1);
		aList.add(a2);
		aList.add(a3);
		
		q1.setAns(aList);
		session.save(q1);
		session.save(a1);
		session.save(a2);
		session.save(a3);
		
		tx.commit();
		session.close();
		sf.close();
		
	}

}
