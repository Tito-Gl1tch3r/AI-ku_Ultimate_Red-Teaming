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

package com.bernardomg.example.jpa.test.unit.converter;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import com.bernardomg.example.jpa.model.converter.BooleanToStringConverter;

/**
 * Unit tests for {@link BooleanToStringConverter} checking that converter
 * transforms boolean values correctly.
 * <p>
 * Checks the following cases:
 * <ol>
 * <li>The boolean value {@code true} is converted correctly to a string.</li>
 * <li>The boolean value {@code false} is converted correctly to a string.</li>
 * <li>The string equivalent to {@code true} is converted correctly to a
 * boolean.</li>
 * <li>The string equivalent to {@code false} is converted correctly to a
 * boolean.</li>
 * <li>A random string is converted to {@code false}.</li>
 * </ol>
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
public final class TestBooleanToStringConverter {

    /**
     * Default constructor.
     */
    public TestBooleanToStringConverter() {
        super();
    }

    /**
     * Tests that the string equivalent to {@code false} is converted correctly
     * to a boolean.
     */
    @Test
    public final void testToBoolean_False() {
        final BooleanToStringConverter converter; // The converter to test

        converter = new BooleanToStringConverter();

        Assertions.assertEquals(converter.convertToEntityAttribute("F"),
                Boolean.FALSE);
    }

    /**
     * Tests that a random string is converted to {@code false}.
     */
    @Test
    public final void testToBoolean_Other() {
        final BooleanToStringConverter converter; // The converter to test

        converter = new BooleanToStringConverter();

        Assertions.assertEquals(converter.convertToEntityAttribute("ABCDE"),
                Boolean.FALSE);
    }

    /**
     * Tests that the string equivalent to {@code true} is converted correctly
     * to a boolean.
     */
    @Test
    public final void testToBoolean_True() {
        final BooleanToStringConverter converter; // The converter to test

        converter = new BooleanToStringConverter();

        Assertions.assertEquals(converter.convertToEntityAttribute("T"),
                Boolean.TRUE);
    }

    /**
     * Tests that the boolean value {@code false} is converted correctly to a
     * string.
     */
    @Test
    public final void testToString_False() {
        final BooleanToStringConverter converter; // The converter to test

        converter = new BooleanToStringConverter();

        Assertions.assertEquals(converter.convertToDatabaseColumn(false), "F");
    }

    /**
     * Tests that the boolean value {@code true} is converted correctly to a
     * string.
     */
    @Test
    public final void testToString_True() {
        final BooleanToStringConverter converter; // The converter to test

        converter = new BooleanToStringConverter();

        Assertions.assertEquals(converter.convertToDatabaseColumn(true), "T");
    }

}
