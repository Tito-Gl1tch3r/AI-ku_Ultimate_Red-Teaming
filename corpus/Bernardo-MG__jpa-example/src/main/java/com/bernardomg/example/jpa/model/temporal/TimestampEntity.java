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
import java.sql.Timestamp;
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
 * JPA entity storing timestamp.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@Entity(name = "TimestampEntity")
@Table(name = "timestamp_entities")
public final class TimestampEntity implements Serializable {

    /**
     * Serialization ID.
     */
    private static final long serialVersionUID = 6542083220180639970L;

    /**
     * Timestamp stored in a calendar.
     */
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "calendar_timestamp", nullable = false)
    private Calendar          calendar;

    /**
     * Timestamp stored in a date.
     */
    @Temporal(TemporalType.TIMESTAMP)
    @Column(name = "java_timestamp", nullable = false)
    private Date              date;

    /**
     * Entity's ID.
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false, unique = true)
    private Integer           id               = null;

    /**
     * Time stored in a SQL timestamp.
     */
    @Column(name = "sql_timestamp", nullable = false)
    private Timestamp         sqlTimestamp;

    /**
     * Default constructor.
     */
    public TimestampEntity() {
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

        final TimestampEntity other = (TimestampEntity) obj;
        return Objects.equals(id, other.id);
    }

    /**
     * Returns the timestamp stored in a {@code Calendar}.
     *
     * @return the timestamp stored in a {@code Calendar}
     */
    public final Calendar getCalendar() {
        return calendar;
    }

    /**
     * Returns the timestamp stored in a {@code Date}.
     *
     * @return the timestamp stored in a {@code Date}
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
     * Returns the timestamp stored in a SQL {@code Timestamp}.
     *
     * @return the timestamp stored in a SQL {@code Timestamp}
     */
    public final Timestamp getSqlTimestamp() {
        return sqlTimestamp;
    }

    @Override
    public final int hashCode() {
        return Objects.hash(id);
    }

    /**
     * Sets the entity's timestamp stored in a {@code Calendar}.
     *
     * @param value
     *            the timestamp to set in the entity
     */
    public final void setCalendar(final Calendar value) {
        calendar = Objects.requireNonNull(value,
                "Received a null pointer as timestamp");
    }

    /**
     * Sets the entity's timestamp stored in a {@code Date}.
     *
     * @param value
     *            the timestamp to set in the entity
     */
    public final void setDate(final Date value) {
        date = Objects.requireNonNull(value,
                "Received a null pointer as timestamp");
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
     * Sets the entity's timestamp stored in a SQL {@code Time}.
     *
     * @param value
     *            the time to set in the entity
     */
    public final void setSqlTimestamp(final Timestamp value) {
        sqlTimestamp = Objects.requireNonNull(value,
                "Received a null pointer as timestamp");
    }

    @Override
    public final String toString() {
        return new StringJoiner(" | ", this.getClass().getSimpleName() + "[ ",
                " ]").add("id=" + id).toString();
    }

}
