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
import java.util.ArrayList;
import java.util.Collection;
import java.util.Objects;
import java.util.StringJoiner;

import javax.persistence.CollectionTable;
import javax.persistence.Column;
import javax.persistence.ElementCollection;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.JoinColumn;
import javax.persistence.Table;

/**
 * Entity using a collection of embeddable objects.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 * @see EmbeddableData
 */
@Entity(name = "ElementCollectionEntity")
@Table(name = "element_collection_entities")
public class ElementCollectionEntity implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long          serialVersionUID = 2888164164144934845L;

    /**
     * Entity's ID.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false, unique = true)
    private Integer                    id               = null;

    /**
     * Name of the entity.
     * <p>
     * This is to have additional data apart from the id, to be used on the
     * tests.
     */
    @Column(name = "name", nullable = false)
    private String                     name             = "";

    /**
     * Embeddable objects.
     */
    @ElementCollection
    @CollectionTable(name = "element_collection_entities_values",
            joinColumns = @JoinColumn(name = "collection_id"))
    private Collection<EmbeddableData> values           = new ArrayList<EmbeddableData>();

    /**
     * Default constructor.
     */
    public ElementCollectionEntity() {
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

        final ElementCollectionEntity other = (ElementCollectionEntity) obj;
        return Objects.equals(id, other.id);
    }

    /**
     * Returns the entity's id.
     *
     * @return the entity's id
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
     * Returns the embeddable objects.
     *
     * @return the embeddable objects
     */
    public Collection<EmbeddableData> getValues() {
        return values;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(id);
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
     * Sets the embeddable objects.
     *
     * @param value
     *            embeddable objects to set in the entity
     */
    public void setValues(final Collection<EmbeddableData> value) {
        values = Objects.requireNonNull(value,
                "Received a null pointer as values");
    }

    @Override
    public final String toString() {
        return new StringJoiner(" | ", this.getClass().getSimpleName() + "[ ",
                " ]").add("id=" + id).toString();
    }

}
