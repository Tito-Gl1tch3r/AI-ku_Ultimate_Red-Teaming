package com.ninfinity.HQLSQL;

import java.util.List;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;
import org.hibernate.query.Query;

public class ReadUsingHQL {
	public static void main(String[] args) {
		Configuration cfg = new Configuration();
		cfg.configure("hibernate.cfg.xml");
		SessionFactory sf = cfg.buildSessionFactory();

		Session session = sf.openSession();
		Transaction tx = session.beginTransaction();

		/*
		 * 1.Select all Record
		 * 
		 * String hql = "from Teacher"; Query hq = session.createQuery(hql);
		 * List<Teacher> tList = hq.list();
		 * 
		 * System.out.println("Teacher list is :"); for(Teacher t : tList) {
		 * System.out.println(t); }
		 */

		/*
		 * 2. Get One Record String hql = "from Teacher where id=3"; Query<Teacher> nq =
		 * session.createQuery(hql);
		 * 
		 * Teacher t = nq.uniqueResult();
		 * 
		 * System.out.println(t);
		 */

		/*
		 * 3. Where with multiple Records String hql = "from Teacher where city='Pune'";
		 * Query hq = session.createQuery(hql);
		 * 
		 * List<Teacher> tlist = hq.list();
		 * 
		 * for(Teacher t : tlist) { System.out.println(t); }
		 */

		/*
		 * 4. Use Alise with Hql
		 * 
		 * String hql = "from Teacher as t where t.city='Pune'"; Query hq =
		 * session.createQuery(hql);
		 * 
		 * List<Teacher> tlist = hq.list();
		 * 
		 * for(Teacher t : tlist) { System.out.println(t); }
		 */

		/*
		 * 5.Using varaible
		 * 
		 * String hql = "from Teacher as t where t.city=:x"; 
		 * Query hq =session.createQuery(hql);
		 * 
		 * hq.setParameter("x", "Nashik");
		 * 
		 * List<Teacher> tlist = hq.list();
		 * 
		 * for(Teacher t : tlist) { System.out.println(t); }
		 * 
		 */
		
		
		/*
		 * 6. Delete 
		 * String hql = "delete from Teacher as t where t.city=:x";
		 *  Query hq =session.createQuery(hql);
		 * 
		 * hq.setParameter("x", "Nashik");
		 * 
		 * int n = hq.executeUpdate();
		 * 
		 * System.out.println(n + "Records Deleted");
		 */
		
		
		/*
		 * 7.Update
		 * 
		 * String hql = "update from Teacher as t set subject =:x where t.city=:y ";
		 * 
		 * Query hq =session.createQuery(hql);
		 * 
		 * hq.setParameter("x", "ML");
		 * 
		 * hq.setParameter("y", "Pune");
		 * 
		 * int n = hq.executeUpdate();
		 * 
		 * System.out.println(n + "Records Updated");
		 */ 
		

		/*
		 * 8.Pagination(to display data to and from terms)
		 * 
		 * String hql = "from Teacher";
		 * 
		 * Query hq =session.createQuery(hql);
		 * 
		 * hq.setFirstResult(5);
		 * 
		 * hq.setMaxResults(15);
		 * 
		 * List<Teacher> tlist = hq.list();
		 * 
		 * for(Teacher t : tlist) { System.out.println(t); }
		 */ 
			
		session.close();
		sf.close();
	}

}
