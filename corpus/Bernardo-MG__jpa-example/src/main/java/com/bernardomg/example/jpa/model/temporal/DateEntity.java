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

package com.bernardomg.example.jpa.model.temporal;

import java.io.Serializable;
import java.util.Calendar;
import java.util.Date;
import java.util.Objects;
import java.util.StringJoiner;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import javax.persistence.Temporal;
import javax.persistence.TemporalType;

/**
 * JPA entity storing full dates.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@Entity(name = "DateEntity")
@Table(name = "date_entities")
public final class DateEntity implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long serialVersionUID = -2916327167109215126L;

    /**
     * Date stored in a calendar.
     */
    @Temporal(TemporalType.DATE)
    @Column(name = "calendar_date", nullable = false)
    private Calendar          calendar;

    /**
     * Date stored in a date.
     */
    @Temporal(TemporalType.DATE)
    @Column(name = "java_date", nullable = false)
    private Date              date;

    /**
     * Entity's ID.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false, unique = true)
    private Integer           id               = null;

    /**
     * Date stored in a SQL date.
     */
    @Column(name = "sql_date", nullable = false)
    private java.sql.Date     sqlDate;

    /**
     * Default constructor.
     */
    public DateEntity() {
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

        final DateEntity other = (DateEntity) obj;
        return Objects.equals(id, other.id);
    }

    /**
     * Returns the date stored in a {@code Calendar}.
     *
     * @return the date stored in a {@code Calendar}
     */
    public final Calendar getCalendar() {
        return calendar;
    }

    /**
     * Returns the date stored in a {@code Date}.
     *
     * @return the date stored in a {@code Date}
     */
    public final Date getDate() {
        return date;
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
     * Returns the date stored in a SQL {@code Date}.
     *
     * @return the date stored in a SQL {@code Date}
     */
    public final java.sql.Date getSqlDate() {
        return sqlDate;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(id);
    }

    /**
     * Sets the entity's date stored in a {@code Calendar}.
     *
     * @param value
     *            the date to set in the entity
     */
    public final void setCalendar(final Calendar value) {
        calendar = Objects.requireNonNull(value,
                "Received a null pointer as date");
    }

    /**
     * Sets the entity's date stored in a {@code Date}.
     *
     * @param value
     *            the date to set in the entity
     */
    public final void setDate(final Date value) {
        date = Objects.requireNonNull(value, "Received a null pointer as date");
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

    /**
     * Sets the entity's date stored in a SQL {@code Date}.
     *
     * @param value
     *            the date to set in the entity
     */
    public final void setSqlDate(final java.sql.Date value) {
        sqlDate = Objects.requireNonNull(value,
                "Received a null pointer as date");
    }

    @Override
    public final String toString() {
        return new StringJoiner(" | ", this.getClass().getSimpleName() + "[ ",
                " ]").add("id=" + id).toString();
    }

}
