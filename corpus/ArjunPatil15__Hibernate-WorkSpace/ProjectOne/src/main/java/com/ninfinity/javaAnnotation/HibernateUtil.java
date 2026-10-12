package com.ninfinity.javaAnnotation;

import java.util.Properties;

import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;
import org.hibernate.cfg.Environment;

public class HibernateUtil {
	public static SessionFactory sf;
	
	public static SessionFactory getSessionFactory() {
		if (sf==null) {
			Configuration cfg = new Configuration();
			
			Properties prop = new Properties();
			
			prop.put(Environment.DRIVER, "com.mysql.cj.jdbc.Driver");
			prop.put(Environment.URL, "jdbc:mysql://localhost:3306/hiberdata");
			prop.put(Environment.USER, "root");
			prop.put(Environment.PASS, "qwerty123");
			
			prop.put(Environment.DIALECT, "org.hibernate.dialect.MySQL8Dialect");
			prop.put(Environment.HBM2DDL_AUTO, "create");
			prop.put(Environment.SHOW_SQL, "true");
			prop.put(Environment.FORMAT_SQL, "true");
			
			cfg.addAnnotatedClass(Person.class);
			
			cfg.setProperties(prop);
			
			sf = cfg.buildSessionFactory();
			
		}
		
		return sf;
	}

}
