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

package com.bernardomg.example.jpa.model.embedded;

import java.io.Serializable;
import java.util.Objects;
import java.util.StringJoiner;

import javax.persistence.AttributeOverride;
import javax.persistence.AttributeOverrides;
import javax.persistence.Column;
import javax.persistence.Embedded;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;

/**
 * JPA entity using an embeddable class.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 * @see EmbeddableData
 */
@Entity(name = "EmbeddedEntity")
@Table(name = "embedded_entities")
public class EmbeddedEntity implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long serialVersionUID = 1L;

    /**
     * Embedded data.
     */
    @Embedded
    @AttributeOverrides({ @AttributeOverride(name = "description",
            column = @Column(nullable = false)), })
    private EmbeddableData    embeddedData;

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
    public EmbeddedEntity() {
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

        final EmbeddedEntity other = (EmbeddedEntity) obj;
        return Objects.equals(id, other.id);
    }

    /**
     * Returns the embedded data.
     *
     * @return the embedded data
     */
    public EmbeddableData getEmbeddedData() {
        return embeddedData;
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
     * Sets the embedded data.
     *
     * @param embeddedData
     *            the embedded data to set in the entity.
     */
    public void setEmbeddedData(final EmbeddableData embeddedData) {
        this.embeddedData = embeddedData;
    }

    /**
     * Sets the entity's id.
     *
     * @param identifier
     *            the id to set in the entity
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
