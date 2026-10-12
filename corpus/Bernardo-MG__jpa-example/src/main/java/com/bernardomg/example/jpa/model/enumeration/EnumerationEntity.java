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

package com.bernardomg.example.jpa.model.enumeration;

import java.io.Serializable;
import java.util.Objects;
import java.util.StringJoiner;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.EnumType;
import javax.persistence.Enumerated;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;

/**
 * JPA entity with an enum field.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 * @see NumbersEnum
 */
@Entity(name = "EnumerationEntity")
@Table(name = "enum_entities")
public final class EnumerationEntity implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long serialVersionUID = -3464036501932820671L;

    /**
     * Enumeration value to be stored as an ordinal in the table.
     */
    @Enumerated(EnumType.ORDINAL)
    @Column(name = "enum_ordinal", nullable = false)
    private NumbersEnum       enumOrdinal;

    /**
     * Enumeration value to be stored as a string in the table.
     */
    @Enumerated(EnumType.STRING)
    @Column(name = "enum_string", nullable = false)
    private NumbersEnum       enumString;

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
    public EnumerationEntity() {
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

        final EnumerationEntity other = (EnumerationEntity) obj;
        return Objects.equals(id, other.id);
    }

    /**
     * Returns the enumeration value to be stored as an ordinal in the table.
     *
     * @return the enumeration value to be stored as an ordinal in the table
     */
    public final NumbersEnum getEnumOrdinal() {
        return enumOrdinal;
    }

    /**
     * Returns the enumeration value to be stored as a string in the table.
     *
     * @return the enumeration value to be stored as a string in the table
     */
    public final NumbersEnum getEnumString() {
        return enumString;
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
     * Sets the enumeration value to be stored as an ordinal in the table.
     *
     * @param value
     *            the enumeration value to be stored as an ordinal in the table
     */
    public final void setEnumOrdinal(final NumbersEnum value) {
        enumOrdinal = Objects.requireNonNull(value,
                "Received a null pointer as enum");
    }

    /**
     * Sets the enumeration value to be stored as a string in the table.
     *
     * @param value
     *            the enumeration value to be stored as a string in the table
     */
    public final void setEnumString(final NumbersEnum value) {
        enumString = Objects.requireNonNull(value,
                "Received a null pointer as enum");
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
