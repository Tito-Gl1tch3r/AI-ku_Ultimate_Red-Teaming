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

package com.bernardomg.example.jpa.test.config.criteria.value;

import javax.persistence.EntityManager;
import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.Root;

import com.bernardomg.example.jpa.model.value.BooleanEntity;
import com.bernardomg.example.jpa.model.value.BooleanEntity_;

/**
 * Factory for creating criteria API queries for the {@code BooleanEntity}.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
public class BooleanEntityCriteriaFactory {

    /**
     * Generates a query to find all the entities.
     *
     * @param entityManager
     *            the entity manager with the entity's data
     * @return the query to find all the entities
     */
    public static final CriteriaQuery<BooleanEntity>
            findAll(final EntityManager entityManager) {
        final CriteriaBuilder builder;                  // Builder
        final CriteriaQuery<BooleanEntity> query; // Query
        final Root<BooleanEntity> entity;         // Root entity

        // Prepares the criteria API query
        builder = entityManager.getCriteriaBuilder();
        query = builder.createQuery(BooleanEntity.class);
        entity = query.from(BooleanEntity.class);

        // Generates a select query
        query.select(entity);

        // Orders by the id
        query.orderBy(builder.asc(entity.get(BooleanEntity_.id)));

        return query;
    }

    /**
     * Private constructor to avoid initialization.
     */
    private BooleanEntityCriteriaFactory() {
        super();
    }

}
