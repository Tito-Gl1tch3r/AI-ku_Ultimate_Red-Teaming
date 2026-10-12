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

package com.bernardomg.example.jpa.test.integration.simple;

import org.junit.jupiter.api.Assertions;

import com.bernardomg.example.jpa.model.simple.DefaultSimpleEntity;
import com.bernardomg.example.jpa.test.config.test.integration.AbstractITEntityModify;

/**
 * Integration tests for a {@code SimpleEntity} testing it can be modified.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
public class ITSimpleEntityModify
        extends AbstractITEntityModify<DefaultSimpleEntity> {

    /**
     * Value to set on the name for the tests.
     */
    private final String name = "The new name";

    /**
     * Default constructor.
     */
    public ITSimpleEntityModify() {
        super(DefaultSimpleEntity::new, 30);
    }

    @Override
    protected final void
            assertEntityModified(final DefaultSimpleEntity entity) {
        Assertions.assertEquals(name, entity.getName());
    }

    @Override
    protected final void modifyEntity(final DefaultSimpleEntity entity) {
        entity.setName(name);
    }

}
