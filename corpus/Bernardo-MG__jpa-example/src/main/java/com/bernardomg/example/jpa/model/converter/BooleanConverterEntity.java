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
import java.util.StringJoiner;

import javax.persistence.Column;
import javax.persistence.Convert;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import javax.persistence.Transient;

/**
 * JPA entity making use of the {@link BooleanToStringConverter}.
 * <p>
 * It contains a boolean flag field, which will be stored as a string in the
 * database's table.
 * <p>
 * The conversion is simple. The {@code true} value is transformed into the
 * {@code T} string, and the {@code false} value will be transformed into the
 * {@code F} string.
 * <p>
 * This transformation is done in both directions, so the entity will always
 * keep a boolean, while the table will always keep a string.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 * @see BooleanToStringConverter
 */
@Entity(name = "BooleanConverterEntity")
@Table(name = "boolean_converter_entities")
public final class BooleanConverterEntity implements Serializable {

    /**
     * Serialization ID.
     */
    @Transient
    private static final long serialVersionUID = 1328776989450853491L;

    /**
     * Boolean flag.
     * <p>
     * It is a boolen in the entity, but will be stored as a string in the
     * database.
     */
    @Convert(converter = BooleanToStringConverter.class)
    @Column(name = "flag", nullable = false, length = 1)
    private Boolean           flag;

    /**
     * Entity's ID.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false, unique = true)
    private Integer           id               = null;

    /**
     * Default constructor.
     */
    public BooleanConverterEntity() {
        super();
    }

    @Override
    public final boolean equals(final Object obj) {
        if (this == obj) {
            return true;
        }

        if (obj == null) {
            return false;
        }

        if (getClass() != obj.getClass()) {
            return false;
        }

        final BooleanConverterEntity other = (BooleanConverterEntity) obj;
        return Objects.equals(id, other.id);
    }

    /**
     * Returns the boolean flag.
     *
     * @return the boolean flag
     */
    public final Boolean getFlag() {
        return flag;
    }

    /**
     * Returns the entity's id.
     *
     * @return the entity's id
     */
    public final Integer getId() {
        return id;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(id);
    }

    /**
     * Sets the boolean flag.
     *
     * @param value
     *            the flag to set on the entity
     */
    public final void setFlag(final Boolean value) {
        flag = Objects.requireNonNull(value, "Received a null pointer as flag");
    }

    /**
     * Sets the entity's id.
     *
     * @param identifier
     *            the ID for the entity
     */
    public final void setId(final Integer identifier) {
        id = Objects.requireNonNull(identifier,
                "Received a null pointer as identifier");
    }

    @Override
    public final String toString() {
        return new StringJoiner(" | ", this.getClass().getSimpleName() + "[ ",
                " ]").add("id=" + id).toString();
    }

}
