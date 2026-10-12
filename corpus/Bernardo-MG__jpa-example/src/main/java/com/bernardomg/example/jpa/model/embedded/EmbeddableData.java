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

import javax.persistence.Column;
import javax.persistence.Embeddable;

/**
 * Embeddabble entity to be added into a JPA entity.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@Embeddable
public final class EmbeddableData implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long serialVersionUID = 8309421350684881450L;

    /**
     * Description of the entity.
     */
    @Column(name = "description", nullable = false)
    private String            description      = "";

    /**
     * Name of the entity.
     */
    @Column(name = "name", nullable = false)
    private String            name             = "";

    /**
     * Default constructor.
     */
    public EmbeddableData() {
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

        final EmbeddableData other = (EmbeddableData) obj;
        return Objects.equals(name, other.name)
                && Objects.equals(description, other.description);
    }

    /**
     * Returns the description of the entity.
     *
     * @return the description of the entity
     */
    public final String getDescription() {
        return description;
    }

    /**
     * Returns the name of the entity.
     *
     * @return the name of the entity
     */
    public final String getName() {
        return name;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(name, description);
    }

    /**
     * Sets the description of the entity.
     *
     * @param value
     *            the description to set in the entity
     */
    public final void setDescription(final String value) {
        description = Objects.requireNonNull(value,
                "Received a null pointer as description");
    }

    /**
     * Sets the name of the entity.
     *
     * @param value
     *            the name to set in the entity
     */
    public final void setName(final String value) {
        name = Objects.requireNonNull(value, "Received a null pointer as name");
    }

    @Override
    public final String toString() {
        return new StringJoiner(" | ", this.getClass().getSimpleName() + "[ ",
                " ]").add("name=" + name).add("description=" + description)
                        .toString();
    }

}
