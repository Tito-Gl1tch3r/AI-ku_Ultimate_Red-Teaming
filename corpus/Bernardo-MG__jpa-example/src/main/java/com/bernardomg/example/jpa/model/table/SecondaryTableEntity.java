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

package com.bernardomg.example.jpa.model.table;

import java.io.Serializable;
import java.util.Objects;
import java.util.StringJoiner;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.PrimaryKeyJoinColumn;
import javax.persistence.SecondaryTable;
import javax.persistence.Table;
import javax.persistence.Transient;

/**
 * JPA entity divided into a secondary table.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@Entity(name = "SecondaryTableEntity")
@Table(name = "two_tables_entities_a")
@SecondaryTable(name = "two_tables_entities_b",
        pkJoinColumns = @PrimaryKeyJoinColumn(name = "entity_id",
                referencedColumnName = "id"))
public final class SecondaryTableEntity implements Serializable {

    /**
     * Serialization ID.
     */
    @Transient
    private static final long serialVersionUID = 1328776989450853491L;

    /**
     * First field.
     */
    @Column(name = "field1", nullable = false, table = "two_tables_entities_a")
    private String            field1           = "";

    /**
     * Second field.
     */
    @Column(name = "field2", nullable = false, table = "two_tables_entities_b")
    private String            field2           = "";

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
    public SecondaryTableEntity() {
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

        final SecondaryTableEntity other = (SecondaryTableEntity) obj;
        return Objects.equals(id, other.id);
    }

    /**
     * Returns the first field.
     *
     * @return the first field
     */
    public final String getField1() {
        return field1;
    }

    /**
     * Returns the second field.
     *
     * @return the second field
     */
    public final String getField2() {
        return field2;
    }

    /**
     * Returns the ID assigned to this entity.
     *
     * @return the entity's ID
     */
    public final Integer getId() {
        return id;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(id);
    }

    /**
     * Sets the first field.
     *
     * @param field
     *            the field to set in the entity
     */
    public final void setField1(final String field) {
        field1 = Objects.requireNonNull(field,
                "Received a null pointer as field 1");
    }

    /**
     * Sets the second field.
     *
     * @param field
     *            the field to set in the entity
     */
    public final void setField2(final String field) {
        field2 = Objects.requireNonNull(field,
                "Received a null pointer as field 2");
    }

    /**
     * Sets the ID assigned to this entity.
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
