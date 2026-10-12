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

package com.bernardomg.example.jpa.test.integration.collection.collection;

import javax.persistence.EntityManager;
import javax.persistence.Query;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.test.context.junit4.AbstractJUnit4SpringContextTests;

import com.bernardomg.example.jpa.test.config.annotation.PersistenceIntegrationTest;

/**
 * Integration tests for a {@code CollectionEntity} testing it loads values
 * correctly by using JPQL queries.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@PersistenceIntegrationTest
public class ITCollectionEntityQueryJpql
        extends AbstractJUnit4SpringContextTests {

    /**
     * The persistence entity manager.
     */
    @Autowired
    private EntityManager entityManager;

    /**
     * The query to acquire all the entities.
     */
    @Value("${query.collection.findAllWithValue}")
    private String        findAllWithValue;

    /**
     * Default constructor.
     */
    public ITCollectionEntityQueryJpql() {
        super();
    }

    /**
     * Tests that retrieving all the entities with a a value returns the
     * expected number of entities.
     */
    @Test
    public final void testFindAllWithValue() {
        final Integer readCount;

        readCount = getQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getQuery() {
        final Integer value; // Value to find
        final Query query;

        // Queried value
        value = 2;

        query = entityManager.createQuery(findAllWithValue);
        query.setParameter("value", value);

        return query;
    }

}
