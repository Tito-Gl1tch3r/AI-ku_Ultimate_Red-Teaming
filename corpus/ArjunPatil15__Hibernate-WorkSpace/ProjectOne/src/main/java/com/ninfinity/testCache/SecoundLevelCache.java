package com.ninfinity.testCache;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

public class SecoundLevelCache {
	public static void main(String[] args) {
		Configuration cfg = new Configuration();
		cfg.configure("hibernate.cfg.xml");
		SessionFactory sf = cfg.buildSessionFactory();

		Session session = sf.openSession();
		Transaction tx = session.beginTransaction();

		Developer developer = session.get(Developer.class, 3);
		System.out.println(developer);



		//tx.commit();
		session.close();

		Session session2 = sf.openSession();

		Developer developer2 = session2.get(Developer.class, 3);
		System.out.println(developer2);

		session2.close();

		Session session3 = sf.openSession();

		Developer developer3 = session3.get(Developer.class, 3);
		System.out.println(developer3);


		sf.close();
	}

}
