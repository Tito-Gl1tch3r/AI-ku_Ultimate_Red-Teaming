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

package com.bernardomg.example.jpa.test.integration.temporal.time;

import java.sql.Time;
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
import org.springframework.beans.factory.annotation.Value;
import org.springframework.test.context.junit.jupiter.EnabledIf;
import org.springframework.test.context.junit4.AbstractJUnit4SpringContextTests;

import com.bernardomg.example.jpa.test.config.annotation.PersistenceIntegrationTest;

/**
 * Integration tests for a {@code DateEntity} testing it loads values correctly
 * by using JPQL queries.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@PersistenceIntegrationTest
@EnabledIf(expression = "#{!'${jpa.adapter.class}'.contains('Hibernate')}",
        reason = "Supports persisted time", loadContext = true)
public class ITTimeEntityQueryJpql extends AbstractJUnit4SpringContextTests {

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
     * The query to acquire all the after a time, using the calendar.
     */
    @Value("${query.afterTime.calendar}")
    private String        findAfterTimeCalendar;

    /**
     * The query to acquire all the after a time, using the Java date.
     */
    @Value("${query.afterTime.java}")
    private String        findAfterTimeJava;

    /**
     * The query to acquire all the after a time, using the SQL time.
     */
    @Value("${query.afterTime.sql}")
    private String        findAfterTimeSql;

    /**
     * The query to acquire all the before a time, using the calendar.
     */
    @Value("${query.beforeTime.calendar}")
    private String        findBeforeTimeCalendar;

    /**
     * The query to acquire all the before a time, using the Java date.
     */
    @Value("${query.beforeTime.java}")
    private String        findBeforeTimeJava;

    /**
     * The query to acquire all the before a time, using the SQL time.
     */
    @Value("${query.beforeTime.sql}")
    private String        findBeforeTimeSql;

    /**
     * The query to acquire all the before a time, using the calendar.
     */
    @Value("${query.inTime.calendar}")
    private String        findInTimeCalendar;

    /**
     * The query to acquire all the before a time, using the Java date.
     */
    @Value("${query.inTime.java}")
    private String        findInTimeJava;

    /**
     * The query to acquire all the before a time, using the SQL time.
     */
    @Value("${query.inTime.sql}")
    private String        findInTimeSql;

    /**
     * Time for the test ranges.
     */
    private Time          time;

    /**
     * String to generate the time for the test ranges.
     */
    private final String  timeString = "11:11:11";

    /**
     * Default constructor.
     */
    public ITTimeEntityQueryJpql() {
        super();
    }

    /**
     * Initializes the time to be used in the tests.
     *
     * @throws ParseException
     *             if the time string can't be parsed
     */
    @BeforeEach
    public final void setUpDate() throws ParseException {
        final DateFormat format; // Format for parsing the time string

        format = new SimpleDateFormat("hh:mm:ss", Locale.ENGLISH);

        date = format.parse(timeString);

        time = new Time(date.getTime());

        calendar = Calendar.getInstance();
        calendar.setTime(date);
    }

    /**
     * Tests that retrieving all the entities after a time gives the correct
     * number of them when using a {@code Calendar} for the time.
     */
    @Test
    public final void testGetAfterTime_Calendar() {
        final Integer readCount;

        readCount = getAfterTimeCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities after a time gives the correct
     * number of them when using a Java {@code Date} for the time.
     */
    @Test
    public final void testGetAfterTime_Java() {
        final Integer readCount;

        readCount = getAfterTimeJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities after a time gives the correct
     * number of them when using a {@code Time} for the time.
     */
    @Test
    public final void testGetAfterTime_Sql() {
        final Integer readCount;

        readCount = getAfterTimeSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities before a time gives the correct
     * number of them when using a {@code Calendar} for the time.
     */
    @Test
    public final void testGetBeforeTime_Calendar() {
        final Integer readCount;

        readCount = getBeforeTimeCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities before a time gives the correct
     * number of them when using a Java {@code Date} for the time.
     */
    @Test
    public final void testGetBeforeTime_Java() {
        final Integer readCount;

        readCount = getBeforeTimeJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities before a time gives the correct
     * number of them when using a {@code Time} for the time.
     */
    @Test
    public final void testGetBeforeTime_Sql() {
        final Integer readCount;

        readCount = getBeforeTimeSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities in a time gives the correct number
     * of them when using a {@code Calendar} for the time.
     */
    @Test
    public final void testGetInTime_Calendar() {
        final Integer readCount;

        readCount = getInTimeCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Tests that retrieving all the entities in a time gives the correct number
     * of them when using a Java {@code Date} for the time.
     */
    @Test
    public final void testGetInTime_Java() {
        final Integer readCount;

        readCount = getInTimeJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Tests that retrieving all the entities in a time gives the correct number
     * of them when using a {@code Time} for the time.
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
        final Query query;

        query = entityManager.createQuery(findAfterTimeCalendar);
        query.setParameter("time", calendar);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterTimeJavaQuery() {
        final Query query;

        query = entityManager.createQuery(findAfterTimeJava);
        query.setParameter("time", date);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterTimeSqlQuery() {
        final Query query;

        query = entityManager.createQuery(findAfterTimeSql);
        query.setParameter("time", time);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeTimeCalendarQuery() {
        final Query query;

        query = entityManager.createQuery(findBeforeTimeCalendar);
        query.setParameter("time", calendar);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeTimeJavaQuery() {
        final Query query;

        query = entityManager.createQuery(findBeforeTimeJava);
        query.setParameter("time", date);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeTimeSqlQuery() {
        final Query query;

        query = entityManager.createQuery(findBeforeTimeSql);
        query.setParameter("time", time);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInTimeCalendarQuery() {
        final Query query;

        query = entityManager.createQuery(findInTimeCalendar);
        query.setParameter("time", calendar);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInTimeJavaQuery() {
        final Query query;

        query = entityManager.createQuery(findInTimeJava);
        query.setParameter("time", date);

        return query;
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInTimeSqlQuery() {
        final Query query;

        query = entityManager.createQuery(findInTimeSql);
        query.setParameter("time", time);

        return query;
    }

}
