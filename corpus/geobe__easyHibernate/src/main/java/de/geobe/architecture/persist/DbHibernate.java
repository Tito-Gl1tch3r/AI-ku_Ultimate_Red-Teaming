/*
 *  The MIT License (MIT)
 *
 *                            Copyright (c) 2021. Georg Beier
 *
 *                            Permission is hereby granted, free of charge, to any person obtaining a copy
 *                            of this software and associated documentation files (the "Software"), to deal
 *                            in the Software without restriction, including without limitation the rights
 *                            to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *                            copies of the Software, and to permit persons to whom the Software is
 *                            furnished to do so, subject to the following conditions:
 *
 *                            The above copyright notice and this permission notice shall be included in all
 *                            copies or substantial portions of the Software.
 *
 *                            THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *                            IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *                            FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *                            AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *                            LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *                            OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *                            SOFTWARE.
 *
 *
 */

package de.geobe.architecture.persist;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.hibernate.boot.Metadata;
import org.hibernate.boot.MetadataBuilder;
import org.hibernate.boot.MetadataSources;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.service.ServiceRegistry;

import java.util.List;

/**
 * Manage hibernate database access for a single database. More then one DbHibernate object can be used to
 * connect to different databases. Basic configuration is defined in an xml configuration file
 * (default hibernate.cfg.xml), other files can be passed to the constructor.<br>
 * This is a "heavy weight" object because connectiong to a database is a complex operation. Thus objects of this
 * class should be constructed at program start and closed before its end.
 *
 * @author georg beier
 */
public class DbHibernate {

    private final SessionFactory sessionFactory;
    private Session activeSession;

    /**
     *
     */
    public void closeDatabase() {
        closeSession();
        sessionFactory.close();
    }

    /**
     * open a session and associate it with a transaction
     */
    private Session openSession() {
        activeSession = sessionFactory.openSession();
        return activeSession;
    }

    /**
     * close active session and automatically commit open transactions
     */
    public void closeSession() {
        if (activeSession != null && activeSession.isOpen()) {
            Transaction t = activeSession.getTransaction();
            if (t.isActive()) {
                t.commit();
            }
            activeSession.close();
        }
    }

    /**
     * create a new session if necessary. also start a transaction if necessary.
     *
     * @return an open session
     */
    public Session getActiveSession() {
        if (activeSession == null || !activeSession.isOpen()) {
            openSession();
        }
        Transaction t = activeSession.getTransaction();
        if (t == null || !t.isActive()) {
            activeSession.beginTransaction();
        }
        return activeSession;
    }

    public String toString() {
        return "(activeSession: " + getActiveSession() + ")";
    }

    public DbHibernate(List<String> fqcns) {
        this(fqcns, "");
    }

    public DbHibernate(List<String> fqcns, String resourceName) {
        StandardServiceRegistryBuilder serviceRegistryBuilder = new StandardServiceRegistryBuilder();
        if (resourceName.equals("")) {
            serviceRegistryBuilder.configure();
        } else {
            serviceRegistryBuilder.configure(resourceName);
        }
        ServiceRegistry serviceRegistry = serviceRegistryBuilder.build();

        MetadataSources metadataSources = new MetadataSources(serviceRegistry);
        fqcns.forEach(metadataSources::addAnnotatedClassName);
        MetadataBuilder metadataBuilder = metadataSources.getMetadataBuilder();
        Metadata metadata = metadataBuilder.build();
        sessionFactory = metadata.buildSessionFactory();
    }

}
