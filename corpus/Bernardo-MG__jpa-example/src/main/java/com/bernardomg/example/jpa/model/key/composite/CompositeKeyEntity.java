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

package com.bernardomg.example.jpa.model.key.composite;

import java.io.Serializable;
import java.util.Objects;
import java.util.StringJoiner;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

/**
 * Entity with a composite id.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@Entity(name = "CompositeKeyEntity")
@Table(name = "composite_key_entities")
public class CompositeKeyEntity implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long serialVersionUID = -1329643517693090051L;

    /**
     * First id.
     */
    @Id
    @Column(name = "id1", nullable = false, unique = true)
    private Integer           id;

    /**
     * Name of the entity.
     */
    @Column(name = "name", nullable = false)
    private String            name             = "";

    /**
     * Second id.
     */
    @Id
    @Column(name = "id2", nullable = false, unique = true)
    private Long              supportId;

    /**
     * Default constructor.
     */
    public CompositeKeyEntity() {
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

        final CompositeKeyEntity other = (CompositeKeyEntity) obj;
        return Objects.equals(id, other.id)
                && Objects.equals(supportId, other.supportId);
    }

    /**
     * Returns the first id.
     *
     * @return the first id
     */
    public final Integer getId() {
        return id;
    }

    /**
     * Returns the name of the entity.
     *
     * @return the entity's name
     */
    public String getName() {
        return name;
    }

    /**
     * Returns the second id.
     *
     * @return the second id
     */
    public final Long getSupportId() {
        return supportId;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(id, supportId);
    }

    /**
     * Sets the first id.
     *
     * @param identifier
     *            the first id for the entity
     */
    public final void setId(final Integer identifier) {
        id = Objects.requireNonNull(identifier,
                "Received a null pointer as id 1");
    }

    /**
     * Sets the name of the entity.
     *
     * @param value
     *            the name to set on the entity
     */
    public void setName(final String value) {
        name = Objects.requireNonNull(value, "Received a null pointer as name");
    }

    /**
     * Sets the second id.
     *
     * @param identifier
     *            the second id for the entity
     */
    public final void setSupportId(final Long identifier) {
        supportId = Objects.requireNonNull(identifier,
                "Received a null pointer as id 2");
    }

    @Override
    public final String toString() {
        return new StringJoiner(" | ", this.getClass().getSimpleName() + "[ ",
                " ]").add("id=" + id).add("supportId=" + supportId).toString();
    }

}
