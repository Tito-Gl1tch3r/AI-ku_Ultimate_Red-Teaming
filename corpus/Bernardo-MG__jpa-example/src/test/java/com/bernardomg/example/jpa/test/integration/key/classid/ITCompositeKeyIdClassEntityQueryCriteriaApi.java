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

package com.bernardomg.example.jpa.test.integration.key.classid;

import javax.persistence.EntityManager;
import javax.persistence.Query;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.junit4.AbstractJUnit4SpringContextTests;

import com.bernardomg.example.jpa.model.key.classid.CompositeKeyIdClassEntity;
import com.bernardomg.example.jpa.test.config.annotation.PersistenceIntegrationTest;
import com.bernardomg.example.jpa.test.config.criteria.key.classid.CompositeKeyIdClassEntityCriteriaFactory;

/**
 * Integration tests for a {@link CompositeKeyIdClassEntity} testing it loads
 * values correctly by using the criteria API.
 * <p>
 * Checks the following cases:
 * <ol>
 * <li>Retrieving an entity by its ids returns the correct one.</li>
 * </ol>
 * <p>
 * This is meant to be used along a Spring context, which will set up the
 * repository and all of it's requirements.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 * @see CompositeKeyIdClassEntity
 */
@PersistenceIntegrationTest
public class ITCompositeKeyIdClassEntityQueryCriteriaApi
        extends AbstractJUnit4SpringContextTests {

    /**
     * The persistence entity manager.
     */
    @Autowired
    private EntityManager entityManager;

    /**
     * Default constructor.
     */
    public ITCompositeKeyIdClassEntityQueryCriteriaApi() {
        super();
        // TODO: Add the query results counts to the configuration files
    }

    /**
     * Tests that retrieving an entity by its ids returns the correct one.
     */
    @Test
    public final void testFindByIds() {
        final Query query;                      // Query for the entity
        final CompositeKeyIdClassEntity entity; // The entity

        // Builds the query
        query = entityManager
                .createQuery(CompositeKeyIdClassEntityCriteriaFactory
                        .findByIds(entityManager, 1, 2l));

        // Acquires the entity
        entity = (CompositeKeyIdClassEntity) query.getSingleResult();

        // The ids are correct
        Assertions.assertEquals(1, entity.getId());
        Assertions.assertEquals(2l, entity.getSupportId());
    }

}
