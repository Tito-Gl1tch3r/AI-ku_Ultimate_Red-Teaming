package com.ninfinity.ProjectOne;

import java.io.FileInputStream;
import java.util.Date;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.cfg.Configuration;

/**
 * Hello world!
 *
 */
public class App 
{
    public static void main( String[] args ) throws Exception
    {
        System.out.println( "Hello World!" );
        Configuration cfg = new Configuration();
        cfg.configure("hibernate.cfg.xml");
        SessionFactory sf = cfg.buildSessionFactory();
        
        System.out.println(sf);
        System.out.println(sf.isClosed());
        
//        Student s1 = new Student(7, "Ganesh", "pune");
        
      
        
        Manager m1 = new Manager();
        m1.setId(1);
        m1.setName("Karan");
        m1.setCity("Mumbai");
        m1.setDateOfJoining(new Date());
        m1.setPermt(true);
        m1.setSalary(1200000);
        
        FileInputStream fis = new FileInputStream("src/main/java/arjunlogo.png");
        
        byte[] data = new byte[fis.available()];
        fis.read(data);
        fis.close();
        m1.setPhoto(data);
        
        Session session = sf.openSession();
        Transaction tx = session.beginTransaction();
        
        session.save(m1);
        
        tx.commit();
        session.close();
        sf.close();
        
    }
}
