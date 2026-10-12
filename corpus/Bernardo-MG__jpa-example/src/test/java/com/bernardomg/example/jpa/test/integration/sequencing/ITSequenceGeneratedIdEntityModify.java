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

package com.bernardomg.example.jpa.test.integration.sequencing;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Disabled;
import org.springframework.test.context.junit.jupiter.EnabledIf;

import com.bernardomg.example.jpa.model.sequencing.SequenceGeneratedIdEntity;
import com.bernardomg.example.jpa.test.config.test.integration.AbstractITEntityModify;

/**
 * Integration tests for a {@code SequenceGeneratedIdEntity} testing it can be
 * modified.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@EnabledIf(
        expression = "#{!('${jpa.adapter.class}'.contains('Hibernate') && '${jpa.database}'.equals('MYSQL'))}",
        reason = "Supports sequences", loadContext = true)
@Disabled("The dynamic disable option is not working correctly")
public class ITSequenceGeneratedIdEntityModify
        extends AbstractITEntityModify<SequenceGeneratedIdEntity> {

    /**
     * Value to set on the name for the tests.
     */
    private final String name = "The new name";

    /**
     * Default constructor.
     */
    public ITSequenceGeneratedIdEntityModify() {
        super(SequenceGeneratedIdEntity::new, 1);
    }

    @Override
    protected final void
            assertEntityModified(final SequenceGeneratedIdEntity entity) {
        Assertions.assertEquals(name, entity.getName());
    }

    @Override
    protected final void modifyEntity(final SequenceGeneratedIdEntity entity) {
        entity.setName(name);
    }

}
