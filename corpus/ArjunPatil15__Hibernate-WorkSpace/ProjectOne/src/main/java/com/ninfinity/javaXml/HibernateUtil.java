package com.ninfinity.javaXml;

import java.util.Properties;

import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;
import org.hibernate.cfg.Environment;

public class HibernateUtil {
	public static SessionFactory sf;

	public static SessionFactory getSessionFactory() {

		if(sf==null) {	
			Configuration cfg = new Configuration();

			Properties props = new Properties();


			props.put(Environment.DRIVER, "com.mysql.cj.jdbc.Driver");
			props.put(Environment.URL, "jdbc:mysql://localhost:3306/hiberdata");
			props.put(Environment.USER, "root");
			props.put(Environment.PASS, "qwerty123");

			props.put(Environment.DIALECT, "org.hibernate.dialect.MySQL8Dialect");
			props.put(Environment.HBM2DDL_AUTO, "create");
			props.put(Environment.SHOW_SQL, "true");
			props.put(Environment.FORMAT_SQL, "true");

			cfg.setProperties(props);
			
			//use 
			cfg.addResource("com/ninfinity/javaXml/Employee.hbm.xml");

			sf = cfg.buildSessionFactory();
		}


		return sf;
	}
}
