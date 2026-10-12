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
import javax.persistence.criteria.CriteriaQuery;

import org.junit.jupiter.api.Assertions;
import org.springframework.beans.factory.annotation.Autowired;

import com.bernardomg.example.jpa.model.key.classid.CompositeKey;
import com.bernardomg.example.jpa.model.key.classid.CompositeKeyIdClassEntity;
import com.bernardomg.example.jpa.test.config.criteria.key.classid.CompositeKeyIdClassEntityCriteriaFactory;
import com.bernardomg.example.jpa.test.config.test.integration.AbstractITEntityModify;

/**
 * Integration tests for a {@link CompositeKeyIdClassEntity} testing it can be
 * modified.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 * @see CompositeKeyIdClassEntity
 */
public class ITCompositeKeyIdClassEntityModify
        extends AbstractITEntityModify<CompositeKeyIdClassEntity> {

    private static final CompositeKeyIdClassEntity getNewEntity() {
        final CompositeKeyIdClassEntity entity;

        entity = new CompositeKeyIdClassEntity();
        entity.setId(10);
        entity.setSupportId(10l);

        return entity;
    }

    /**
     * The persistence entity manager.
     */
    @Autowired
    private EntityManager entityManager;

    /**
     * Value to set on the name for the tests.
     */
    private final String  name = "ABC";

    /**
     * Default constructor.
     */
    public ITCompositeKeyIdClassEntityModify() {
        super(ITCompositeKeyIdClassEntityModify::getNewEntity, 4);
    }

    @Override
    protected final void
            assertEntityModified(final CompositeKeyIdClassEntity entity) {
        Assertions.assertEquals(name, entity.getName());
    }

    @Override
    protected CriteriaQuery<CompositeKeyIdClassEntity>
            getCriteriaQuery(final Object id) {
        return CompositeKeyIdClassEntityCriteriaFactory.findByIds(entityManager,
                ((CompositeKey) id).getId(),
                ((CompositeKey) id).getSupportId());
    }

    @Override
    protected final Object getId() {
        final CompositeKey id;

        id = new CompositeKey();
        id.setId(1);
        id.setSupportId(1l);

        return id;
    }

    @Override
    protected final void modifyEntity(final CompositeKeyIdClassEntity entity) {
        entity.setName(name);
    }

}
