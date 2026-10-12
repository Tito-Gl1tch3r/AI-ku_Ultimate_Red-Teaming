package com.ninfinity.mapping.onetoone;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

public class TestApp {
	public static void main(String[] args) {


		Configuration cfg= new Configuration(); cfg.configure("hibernate.cfg.xml");
		SessionFactory sf = cfg.buildSessionFactory();

		Session session = sf.openSession(); 
		Transaction tx = session.beginTransaction();

//		Question q1 = new Question(); q1.setqId(1);
//		q1.setQues("What is an Interface ?");
//
//		Question q2 = new Question(); q2.setqId(2);
//		q2.setQues("What is Wrapper ?");
//
//		Answer a1 = new Answer(); a1.setaId(1);
//		a1.setAnswer(" Its 100% Abstrsct Class");
//
//		Answer a2 = new Answer(); a2.setaId(2);
//		a2.setAnswer("Facility for primitive to work as Object");
//
//		q1.setAns(a1); q2.setAns(a2);
//
//		a1.setQues(q1); a2.setQues(q2);
//
//		session.save(q1); session.save(q2); session.save(a1); session.save(a2);
//
//
//		tx.commit();

		Question q = session.get(Question.class, 2);
		
		System.out.println("Question is :" + q.getQues());
		System.out.println("Answer is :"+ q.getAns().getAnswer());
		
		session.close();
		sf.close();
	}

}
