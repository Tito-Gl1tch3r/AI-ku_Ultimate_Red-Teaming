/**
 * The MIT License (MIT)
 * <p>
 * Copyright (c) 2016-2021 the the original author or authors.
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

package com.bernardomg.example.jpa.test.integration.temporal.timestamp;

import java.sql.Timestamp;
import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;

import javax.persistence.EntityManager;
import javax.persistence.Query;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.junit.jupiter.EnabledIf;
import org.springframework.test.context.junit4.AbstractJUnit4SpringContextTests;

import com.bernardomg.example.jpa.test.config.annotation.PersistenceIntegrationTest;
import com.bernardomg.example.jpa.test.config.criteria.temporal.TimestampEntityCriteriaFactory;

/**
 * Integration tests for a {@code TimestampEntity} testing it loads values
 * correctly by using the criteria API.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@PersistenceIntegrationTest
@EnabledIf(expression = "#{!'${jpa.adapter.class}'.contains('Hibernate')}",
        reason = "Supports persisted timestamp", loadContext = true)
public class ITTimestampEntityQueryCriteriaApi
        extends AbstractJUnit4SpringContextTests {

    /**
     * Calendar for the test ranges.
     */
    private Calendar      calendar;

    /**
     * Java date for the test ranges.
     */
    private Date          date;

    /**
     * The persistence entity manager.
     */
    @Autowired
    private EntityManager entityManager;

    /**
     * Timestamp for the test ranges.
     */
    private Timestamp     timestamp;

    /**
     * String to generate the time for the test ranges.
     */
    private final String  timestampString = "1991-05-02 11:11:11";

    /**
     * Default constructor.
     */
    public ITTimestampEntityQueryCriteriaApi() {
        super();
    }

    /**
     * Initializes the time to be used in the tests.
     *
     * @throws ParseException
     *             if the time string can't be parsed
     */
    @BeforeEach
    public final void setUpTime() throws ParseException {
        final DateFormat format; // Format for parsing the time string

        format = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss", Locale.ENGLISH);

        date = format.parse(timestampString);

        timestamp = new Timestamp(date.getTime());

        calendar = Calendar.getInstance();
        calendar.setTime(date);
    }

    /**
     * Tests that retrieving all the entities after a timestamp gives the
     * correct number of them when using a {@code Calendar} for the timestamp.
     */
    @Test
    public final void testGetAfterTime_Calendar() {
        final Integer readCount;

        readCount = getAfterTimeCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities after a timestamp gives the
     * correct number of them when using a Java {@code Date} for the timestamp.
     */
    @Test
    public final void testGetAfterTime_Java() {
        final Integer readCount;

        readCount = getAfterTimeJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities after a timestamp gives the
     * correct number of them when using a {@code Timestamp} for the timestamp.
     */
    @Test
    public final void testGetAfterTime_Sql() {
        final Integer readCount;

        readCount = getAfterTimeSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities before a timestamp gives the
     * correct number of them when using a {@code Calendar} for the timestamp.
     */
    @Test
    public final void testGetBeforeTime_Calendar() {
        final Integer readCount;

        readCount = getBeforeTimeCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities before a timestamp gives the
     * correct number of them when using a Java {@code Date} for the timestamp.
     */
    @Test
    public final void testGetBeforeTime_Java() {
        final Integer readCount;

        readCount = getBeforeTimeJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities before a timestamp gives the
     * correct number of them when using a {@code Timestamp} for the timestamp.
     */
    @Test
    public final void testGetBeforeTime_Sql() {
        final Integer readCount;

        readCount = getBeforeTimeSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities in a timestamp gives the correct
     * number of them when using a {@code Calendar} for the timestamp.
     */
    @Test
    public final void testGetInTime_Calendar() {
        final Integer readCount;

        readCount = getInTimeCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Tests that retrieving all the entities in a timestamp gives the correct
     * number of them when using a Java {@code Date} for the timestamp.
     */
    @Test
    public final void testGetInTime_Java() {
        final Integer readCount;

        readCount = getInTimeJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Tests that retrieving all the entities in a timestamp gives the correct
     * number of them when using a {@code Timestamp} for the timestamp.
     */
    @Test
    public final void testGetInTime_Sql() {
        final Integer readCount;

        readCount = getInTimeSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterTimeCalendarQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findAfterTimestamp(entityManager, calendar));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterTimeJavaQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findAfterTimestamp(entityManager, date));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterTimeSqlQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findAfterSqlTimestamp(entityManager, timestamp));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeTimeCalendarQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findBeforeTimestamp(entityManager, calendar));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeTimeJavaQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findBeforeTimestamp(entityManager, date));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeTimeSqlQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findBeforeSqlTimestamp(entityManager, timestamp));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInTimeCalendarQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findInTimestamp(entityManager, calendar));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInTimeJavaQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findInTimestamp(entityManager, date));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInTimeSqlQuery() {
        return entityManager.createQuery(TimestampEntityCriteriaFactory
                .findInSqlTimestamp(entityManager, timestamp));
    }

}
