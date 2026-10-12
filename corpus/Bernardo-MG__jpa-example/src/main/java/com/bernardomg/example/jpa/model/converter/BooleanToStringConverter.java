/**
 * The MIT License (MIT)
 * <p>
 * Copyright (c) 2016-2021 the original author or authors.
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

package com.bernardomg.example.jpa.model.converter;

import java.io.Serializable;
import java.util.Objects;

import javax.persistence.AttributeConverter;
import javax.persistence.Converter;

/**
 * Converter mapping boolean values to string values.
 * <p>
 * It will convert a {@code true} value to a {@code T} string, and a
 * {@code false} value to a {@code F} string. It also performs the reverse
 * operation, from the strings to boolean values.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@Converter
public final class BooleanToStringConverter
        implements AttributeConverter<Boolean, String>, Serializable {

    /**
     * Serialization ID.
     */
    private static final long serialVersionUID = -5072734197181618754L;

    /**
     * Default constructor.
     */
    public BooleanToStringConverter() {
        super();
    }

    /**
     * Converts the value stored in the entity attribute into the data
     * representation to be stored in the database.
     * <p>
     * In this case, it means converting a {@code true} value to a {@code T}
     * string, and a {@code false} value to a {@code F} string.
     */
    @Override
    public final String convertToDatabaseColumn(final Boolean value) {
        final String result;

        Objects.requireNonNull(value, "Received a null pointer as value");

        if (Boolean.TRUE.equals(value)) {
            result = "T";
        } else {
            result = "F";
        }

        return result;
    }

    /**
     * Converts the data stored in the database column into the value to be
     * stored in the entity attribute.
     * <p>
     * In this case, it means converting a {@code T} string to a {@code true}
     * value, and any other string to a {@code false} value.
     */
    @Override
    public final Boolean convertToEntityAttribute(final String value) {
        Objects.requireNonNull(value, "Received a null pointer as value");

        return "T".equals(value);
    }

}
