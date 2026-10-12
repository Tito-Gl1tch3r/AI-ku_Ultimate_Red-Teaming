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

package com.bernardomg.example.jpa.model.key.embedded;

import java.io.Serializable;
import java.util.Objects;
import java.util.StringJoiner;

import javax.persistence.Column;
import javax.persistence.EmbeddedId;
import javax.persistence.Entity;
import javax.persistence.Table;

/**
 * Entity with a composite embedded id.
 * <p>
 * The {@link EmbeddableCompositeKey} is used as the embedded id.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 * @see EmbeddableCompositeKey
 */
@Entity(name = "EmbeddedCompositeKeyEntity")
@Table(name = "embedded_key_entities")
public class EmbeddedCompositeKeyEntity implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long      serialVersionUID = -7439275648624068461L;

    /**
     * Embedded id.
     */
    @EmbeddedId
    private EmbeddableCompositeKey key;

    /**
     * Name of the entity.
     */
    @Column(name = "name", nullable = false)
    private String                 name             = "";

    /**
     * Default constructor.
     */
    public EmbeddedCompositeKeyEntity() {
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

        final EmbeddedCompositeKeyEntity other = (EmbeddedCompositeKeyEntity) obj;
        return Objects.equals(key, other.key);
    }

    /**
     * Returns the embedded id.
     *
     * @return the embedded id
     */
    public final EmbeddableCompositeKey getKey() {
        return key;
    }

    /**
     * Returns the name of the entity.
     *
     * @return the entity's name
     */
    public String getName() {
        return name;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(key);
    }

    /**
     * Sets the embedded id.
     *
     * @param identifier
     *            the id to set in the entity
     */
    public final void setKey(final EmbeddableCompositeKey identifier) {
        key = Objects.requireNonNull(identifier,
                "Received a null pointer as the identifier");
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

    @Override
    public final String toString() {
        return new StringJoiner(" | ", this.getClass().getSimpleName() + "[ ",
                " ]").add("key=" + key).toString();
    }

}
