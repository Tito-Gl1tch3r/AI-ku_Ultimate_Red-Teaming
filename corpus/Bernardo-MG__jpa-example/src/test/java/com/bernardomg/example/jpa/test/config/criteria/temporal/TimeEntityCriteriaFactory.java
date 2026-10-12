/**
 * The MIT License (MIT)
 * <p>
 * Copyright (c) 2016-2021 the the original author or authors.
 * <p>
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * <p>
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * <p>
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package com.bernardomg.example.jpa.test.config.criteria.temporal;

import java.util.Calendar;
import java.util.Date;

import javax.persistence.EntityManager;
import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.Root;

import com.bernardomg.example.jpa.model.temporal.TimeEntity;
import com.bernardomg.example.jpa.model.temporal.TimeEntity_;

/**
 * Factory for creating criteria API queries for the {@link TimeEntity}.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
public class TimeEntityCriteriaFactory {

    /**
     * Finds all the entities with a time after the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time after the specified time
     */
    public static final CriteriaQuery<TimeEntity> findAfterSqlTime(
            final EntityManager entityManager, final java.sql.Time time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.greaterThan(entity.get(TimeEntity_.sqlTime), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time after the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time after the specified time
     */
    public static final CriteriaQuery<TimeEntity> findAfterTime(
            final EntityManager entityManager, final Calendar time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(
                builder.greaterThan(entity.get(TimeEntity_.calendar), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time after the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time after the specified time
     */
    public static final CriteriaQuery<TimeEntity>
            findAfterTime(final EntityManager entityManager, final Date time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.greaterThan(entity.get(TimeEntity_.date), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time before the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time before the specified time
     */
    public static final CriteriaQuery<TimeEntity> findBeforeSqlTime(
            final EntityManager entityManager, final java.sql.Time time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.lessThan(entity.get(TimeEntity_.sqlTime), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time before the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time before the specified time
     */
    public static final CriteriaQuery<TimeEntity> findBeforeTime(
            final EntityManager entityManager, final Calendar time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.lessThan(entity.get(TimeEntity_.calendar), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time before the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time before the specified time
     */
    public static final CriteriaQuery<TimeEntity>
            findBeforeTime(final EntityManager entityManager, final Date time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.lessThan(entity.get(TimeEntity_.date), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time equal to the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time equal to the specified time
     */
    public static final CriteriaQuery<TimeEntity> findInSqlTime(
            final EntityManager entityManager, final java.sql.Time time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.equal(entity.get(TimeEntity_.sqlTime), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time equal to the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time equal to the specified time
     */
    public static final CriteriaQuery<TimeEntity>
            findInTime(final EntityManager entityManager, final Calendar time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.equal(entity.get(TimeEntity_.calendar), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Finds all the entities with a time equal to the specified time.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @param time
     *            the limit time for the query
     * @return all the entities with a time equal to the specified time
     */
    public static final CriteriaQuery<TimeEntity>
            findInTime(final EntityManager entityManager, final Date time) {
        final CriteriaBuilder builder;         // Builder
        final CriteriaQuery<TimeEntity> query; // Query
        final Root<TimeEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(TimeEntity.class);
        entity = query.from(TimeEntity.class);

        // Generates a select query
        query.select(entity);
        query.where(builder.equal(entity.get(TimeEntity_.date), time));

        // Orders by the id
        query.orderBy(builder.asc(entity.get(TimeEntity_.id)));

        return query;
    }

    /**
     * Private constructor to avoid initialization.
     */
    private TimeEntityCriteriaFactory() {
        super();
    }

}
