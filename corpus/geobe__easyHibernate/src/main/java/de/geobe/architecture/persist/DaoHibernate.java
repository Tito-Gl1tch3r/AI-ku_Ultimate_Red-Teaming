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

import org.hibernate.*;
import org.hibernate.query.Query;

import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.Predicate;
import javax.persistence.criteria.Root;
import javax.persistence.metamodel.Attribute;
import javax.persistence.metamodel.IdentifiableType;
import java.io.Serializable;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Dao implementation for Hibernate 5.x persistence layer
 * Encapsulate all database operations with hibernate persistence layer
 *
 * @param <PersistType> a persisted type that is handled by this dao
 * @author georg beier
 */
public class DaoHibernate<PersistType> {

    private Class<?> accessedType;
    private DbHibernate dbHibernate;

    /**
     * create new Dao object
     *
     * @param persistType The class of the PersistType. Must be given because Java
     *                    eliminates generic type parameters at compile time and
     *                    Hibernate needs type information at runtime!
     * @param dbac        The Hibernate database access object
     */
    public DaoHibernate(Class<?> persistType, DbHibernate dbac) {
        accessedType = persistType;
        dbHibernate = dbac;
    }

    /**
     * commits a transaction on all daos in this thread that are linked to the
     * same dbHibernate. Causes a transaction rollback if commit fails.
     * @return true if successful, false if at least one object is "stale" (i.e. object was
     * changed by another thread or process)
     */
    public boolean commit() {
        Session s = dbHibernate.getActiveSession();
        Transaction t = s.getTransaction();
        try {
            if (t != null) {
                t.commit();
            }
            return true;
        } catch (RuntimeException ex) {
            t.rollback();
            return false;
        }
    }

    /**
     * performs a rollback on all daos in this thread that are linked to the
     * same dbAccess object which implies to the same session
     */
    public void rollback() {
        Session s = dbHibernate.getActiveSession();
        Transaction t = s.getTransaction();
        if (t != null) {
            t.rollback();
        }
    }

    /**
     * closes the database session on this dao's connection to the database. <br>
     * affects all daos in the same thread that are linked to the same database
     * connection. <br>
     * closing the session will commit open transaction,
     *
     * @see DbHibernate#closeSession()
     */
    public void closeSession() {
        dbHibernate.closeSession();
    }

    /**
     * save object to persistent storage
     * Also starts a transaction, if none is active
     *
     * @param obj object to be saved
     * @return true if successful, false if object is "stale" (i.e. object was
     * changed by another thread or process)
     */
    public boolean save(PersistType obj) {
        Session s = dbHibernate.getActiveSession();
        try {
            Transaction t = s.getTransaction();
            s.saveOrUpdate(obj);
            return true;
        } catch (StaleObjectStateException stex) {
            s.refresh(obj);
            return false;
        } catch (RuntimeException rex) {
            Transaction t = s.getTransaction();
            if (t != null) {
                t.rollback();
            }
            s.close();
            throw rex;
        }
    }

    /*
     * Fetch object from persistent storage
     * Also starts a transaction, if none is active
     *
     * @param id
     *            key property of object
     * @return object, if found, else null
     */
    @SuppressWarnings("unchecked")
    public PersistType fetch(Serializable id) {
        Session s = dbHibernate.getActiveSession();
        Object result = s.get(accessedType, id);
        return (PersistType) result;
    }

    /*
     * Fetch all objects of PersistType in persistent storage
     * Also starts a transaction, if none is active
     *
     * @return list of all objects
     */
    @SuppressWarnings("unchecked")
    public List<PersistType> fetchAll() {
        Session s = dbHibernate.getActiveSession();
        return (List<PersistType>) s.createQuery(
                "from " + accessedType.getCanonicalName()).list();
    }

    /**
     * Iterate over all objects of PersistType in pages.
     * Method uses ScrollableResults class and closes it after each iteration.
     * This makes iteration much slower on large data sets
     * but it is safe to break iteration at any time.
     * <p>
     * Also starts a transaction, if none is active
     *
     * @param pageSize number of objects per page
     * @param startAt  row in result where to start
     * @return Iterator on Lists of PersistType objects, each holding one page
     */
    @SuppressWarnings("unchecked")
    public Iterator<List<PersistType>> iteratePages(int pageSize, int startAt) {
        return iteratePages(pageSize, startAt, "");
    }

    /**
     * Restrict and/or order iteration over objects of type PersistType in pages by extending the basic HQL query.
     * The basic query is "from PersistType", predicates String is appended after a blank.
     * Method uses ScrollableResults class and closes it after each iteration.
     * This makes iteration much slower on large data sets
     * but it is safe to break iteration at any time.
     * <p>
     * Also starts a transaction, if none is active
     *
     * @param pageSize number of objects per page
     * @param startAt  row in result where to start
     * @param predicates String with syntactically correct HQL predicates
     * @return Iterator on Lists of PersistType objects, each holding one page
     */
    @SuppressWarnings("unchecked")
    public Iterator<List<PersistType>> iteratePages(int pageSize, int startAt, String predicates) {
        if (predicates != null && predicates.length() > 0) {
            predicates = " " + predicates;
        } else {
            predicates = "";
        }
        Session session = dbHibernate.getActiveSession();
        Query<PersistType> query = session
                .createQuery("from " + accessedType.getCanonicalName() + predicates)
                .setCacheMode(CacheMode.IGNORE);

        return new Iterator<List<PersistType>>() {
            int scrollIndex = startAt;
            boolean hasNextBeenCalled = false;
            boolean lastNextCallResult = false;
            ScrollableResults scrollableResults;
            List<PersistType> pageList;

            /**
             * Initialze scrolableResults to next page, if not already done
             * @return true if not at the end
             */
            @Override
            public boolean hasNext() {
                if (!hasNextBeenCalled) {
                    scrollableResults = query.scroll(ScrollMode.FORWARD_ONLY);
                    scrollableResults.scroll(scrollIndex);
                    scrollIndex += pageSize;
                    lastNextCallResult = scrollableResults.next();
                    hasNextBeenCalled = true;
                }
                return lastNextCallResult;
            }

            @Override
            public List<PersistType> next() {
                pageList = nextPage();
                hasNextBeenCalled = false;
                return Collections.unmodifiableList(pageList);
            }

            private List<PersistType> nextPage() {
                List<PersistType> page = new ArrayList<>(pageSize);
                if (!hasNextBeenCalled) {
                    hasNext();
                }
                while (page.size() < pageSize) {
                    if (lastNextCallResult) {
                        page.add((PersistType) scrollableResults.get(0));
                        lastNextCallResult = scrollableResults.next();
                    } else {
                        break;
                    }
                }
                scrollableResults.close();
                return page;
            }
        };
    }

    /**
     * Iterate over all objects of PersistType using Hibernate ScrollableResults class.
     * Hibernate class ScrollableResults is used to scroll through results. This is very fast
     * for very large result sets. But ScrollableResults object is only closed at the end of
     * iteration. So the whole result set should always be iterated to the end. Use iteratePages
     * to safely work only on a limited part.
     * <p>
     * Also starts a transaction, if none is active
     *
     * @return Iterator on all objects of PersistType
     */
    @SuppressWarnings("unchecked")
    public Iterator<PersistType> iterateAll() {
        return iterateAll("");
    }

    /**
     * Restrict and/or order iteration over objects of type PersistType by extending the basic HQL query.
     * The basic query is "from PersistType", predicates String is appended after a blank.
     * The query MUST return only objects of type PersistType!
     * The internally used ScrollableResults object is only closed at the end of iteration.
     * So the whole result set should always be iterated to the end. Use iteratePages to safely
     * work only on a limited part.
     * <p>
     * Also starts a transaction, if none is active
     *
     * @param predicates String with syntactically correct HQL predicates
     * @return Iterator on all objects of PersistType
     */
    @SuppressWarnings("unchecked")
    public Iterator<PersistType> iterateAll(String predicates) {
        if (predicates != null && predicates.length() > 0) {
            predicates = " " + predicates;
        } else {
            predicates = "";
        }
        Session session = dbHibernate.getActiveSession();
        ScrollableResults scrollableResults = session
                .createQuery("from " + accessedType.getCanonicalName() + predicates)
                .setCacheMode(CacheMode.IGNORE)
                .scroll(ScrollMode.FORWARD_ONLY);

        /*
         * emulate an Iterator on ScrollableResults
         */
        return new Iterator<PersistType>() {
            boolean hasNextBeenCalled = false;
            boolean lastNextCallResult = false;

            @Override
            public boolean hasNext() {
                if (!hasNextBeenCalled) {
                    lastNextCallResult = scrollableResults.next();
                    hasNextBeenCalled = true;
                }
                if (!lastNextCallResult) {
                    if (scrollableResults != null) {
                        scrollableResults.close();
                    }
                }
                return lastNextCallResult;
            }

            @Override
            public PersistType next() {
                if (!hasNextBeenCalled) {
                    lastNextCallResult = scrollableResults.next();
                    hasNextBeenCalled = true;
                    if (!lastNextCallResult) {
                        throw new NoSuchElementException();
                    }
                }
                PersistType nextObject = (PersistType) scrollableResults.get(0);
                hasNextBeenCalled = false;
                return nextObject;
            }
        };
    }

    /**
     * executes hibernate query <br>
     * (e.g. select address from person p join p.address)
     * Also starts a transaction, if none is active
     *
     * @param query simple HQL query string
     * @return list of returned objects
     */
    @SuppressWarnings("unchecked")
    public List<Object> find(String query) {
        Session s = dbHibernate.getActiveSession();
        return s.createQuery(query).list();
    }

    /**
     * executes hibernate query with parameters <br>
     * (e.g. from person p where p.name = :name)
     * Also starts a transaction, if none is active
     *
     * @param query  HQL query string containing named parameters in hibernate
     *               style (e.g. :name)
     * @param params map of actual parameters with parameter name as key (without :)
     *               and actual parameter value as value
     * @return list of returned objects
     */
    @SuppressWarnings("unchecked")
    public List<Object> find(String query, Map<String, Object> params) {
        Session s = dbHibernate.getActiveSession();
        Query<?> hibernateQuery = s.createQuery(query);//, accessedType);
        for (String pname : params.keySet()) {
            hibernateQuery.setParameter(pname, params.get(pname));
        }
        return (List<Object>) hibernateQuery.list();
    }

    /**
     * Query by example. Find objects that are "similar" to the sample object.<br>
     * String properties are matched with <i>like</i>, so SQL wildcards (%) can
     * be used.
     * Only single valued attributes are considered, no arrays or collections
     *
     * @param sample a sample object
     * @return list of objects that conform to sample in all not null properties
     */
    public List<PersistType> findByExample(PersistType sample) {
        return findByExample(sample, new ArrayList<>());
    }

    /**
     * Query by example. Find objects that are "similar" to the sample object.<br>
     * String properties are matched with <i>like</i>, so SQL wildcards (%) can
     * be used.
     * Only single valued attributes are considered, no arrays or collections.
     * Also starts a transaction, if none is active<br>
     *
     * @param sample   a sample object
     * @param excluded properties not considered im matching
     * @return list of objects that conform to sample in all not null properties
     */
    @SuppressWarnings("unchecked")
    public List<PersistType> findByExample(PersistType sample,
                                           Collection<String> excluded) {
        Session s = dbHibernate.getActiveSession();
        CriteriaBuilder criteriaBuilder = s.getCriteriaBuilder();
        CriteriaQuery<PersistType> criteriaQuery =
                (CriteriaQuery<PersistType>) criteriaBuilder.createQuery(accessedType);
        Root<PersistType> root = (Root<PersistType>) criteriaQuery.from(accessedType);
        IdentifiableType<?> parent = root.getModel();
        // figure out names of all Singular attributes in the inheritance chain of entities
        List<String> attributeNames = new ArrayList<>();
        while (parent != null) {
            attributeNames.addAll(
                    parent.getDeclaredSingularAttributes().stream().
                            filter((attribute ->
                                    !excluded.contains(attribute.getName())
                                            && !attribute.getJavaType().isArray())
                            ).map(Attribute::getName).collect(Collectors.toList())
            );
            parent = parent.getSupertype();
        }
        // a list of directly accessible field names of sample object
        List<String> fieldNames = Arrays.stream(accessedType.getFields()).
                map(Field::getName).collect(Collectors.toList());
        // a list of all accessible getter method names of sample object
        List<String> getterNames = Arrays.stream(accessedType.getMethods()).
                filter(method ->
                        method.getName().startsWith("get") && method.getParameterCount() == 0
                ).map(Method::getName).collect(Collectors.toList());
        // build a map to collect all not null attributes in sample object
        Map<String, Object> qbeValues = new HashMap<>();
        // loop over all persistent attributes
        attributeNames.forEach(attName -> {
            try {
                Object val = null;
                // direct field access possible?
                if (fieldNames.contains(attName)) {
                    val = accessedType.getField(attName).get(sample);
                } else if (getterNames.contains(getterFor(attName))) {
                    // there is a getter method?
                    val = accessedType.getMethod(getterFor(attName)).invoke(sample);
                }
                // only consider fields that are neither NULL nor 0
                if (!(val == null || (val instanceof Number && ((Number) val).longValue() == 0))) {
                    qbeValues.put(attName, val);
                }
            } catch (NoSuchFieldException | IllegalAccessException | NoSuchMethodException | InvocationTargetException e) {
                // should be impossible to get here
                e.printStackTrace();
            }
        });
        // now we  can create a list of query predicates
        List<Predicate> predicateList = new ArrayList<>(qbeValues.size());
        qbeValues.keySet().forEach(key -> {
            Object val = qbeValues.get(key);
            if (val instanceof String) {
                String stval = (String) val;
                predicateList.add(criteriaBuilder.like(root.get(key), stval));
            } else {
                predicateList.add(criteriaBuilder.equal(root.get(key), val));
            }
        });
        Predicate[] predicates = predicateList.toArray(Predicate[]::new);
        // all predicates of the list must be met
        criteriaQuery.select(root).where(predicates);
        // finally create and execute the query
        Query<PersistType> query = s.createQuery(criteriaQuery);
        return query.getResultList();
    }

    /**
     * Delete object from persistent storage.
     * Also starts a transaction, if none is active
     *
     * @param obj object to be deleted
     */
    public void delete(PersistType obj) {
        Session s = dbHibernate.getActiveSession();
        s.delete(obj);
    }

    /**
     * Delete all objects of PersistType from persistent storage
     * Also starts a transaction, if none is active
     */
    public void deleteAll() {
        Session s = dbHibernate.getActiveSession();
        s.createQuery("delete " + accessedType.getCanonicalName())
                .executeUpdate();
    }

    /**
     * helpful when debugging ...
     */
    public String toString() {
        return "(accessedType: " + accessedType + ")" + "(dbAccess: "
                + dbHibernate + ")";
    }

    /**
     * build getter name for attribute name
     *
     * @param attName name of jpa attribute
     * @return name of corresponding getter method
     */
    private String getterFor(String attName) {
        return "get" + attName.substring(0, 1).toUpperCase() + attName.substring(1);
    }

}
