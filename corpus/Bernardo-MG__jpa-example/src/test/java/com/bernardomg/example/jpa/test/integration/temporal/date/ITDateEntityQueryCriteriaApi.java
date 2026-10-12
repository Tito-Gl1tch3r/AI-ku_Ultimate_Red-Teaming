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

package com.bernardomg.example.jpa.test.integration.temporal.date;

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
import com.bernardomg.example.jpa.test.config.criteria.temporal.DateEntityCriteriaFactory;

/**
 * Integration tests for a {@code DateEntity} testing it loads values correctly
 * by using the criteria API.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@PersistenceIntegrationTest
@EnabledIf(expression = "#{!'${jpa.adapter.class}'.contains('Hibernate')}",
        reason = "Supports persisted dates", loadContext = true)
public class ITDateEntityQueryCriteriaApi
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
     * String to generate the date for the test ranges.
     */
    private final String  dateString = "1991-05-02";

    /**
     * The persistence entity manager.
     */
    @Autowired
    private EntityManager entityManager;

    /**
     * SQL date for the test ranges.
     */
    private java.sql.Date sqlDate;

    /**
     * Default constructor.
     */
    public ITDateEntityQueryCriteriaApi() {
        super();
    }

    /**
     * Initializes the date to be used in the tests.
     *
     * @throws ParseException
     *             if the date string can't be parsed
     */
    @BeforeEach
    public final void setUpDate() throws ParseException {
        final DateFormat format; // Format for parsing the date string

        format = new SimpleDateFormat("yyyy-MM-dd", Locale.ENGLISH);

        date = format.parse(dateString);

        sqlDate = new java.sql.Date(date.getTime());

        calendar = Calendar.getInstance();
        calendar.setTime(date);
    }

    /**
     * Tests that retrieving all the entities after a date gives the correct
     * number of them when using a {@code Calendar} for the date.
     */
    @Test
    public final void testGetAfterDate_Calendar() {
        final Integer readCount;

        readCount = getAfterDateCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities after a date gives the correct
     * number of them when using a Java {@code Date} for the date.
     */
    @Test
    public final void testGetAfterDate_Java() {
        final Integer readCount;

        readCount = getAfterDateJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities after a date gives the correct
     * number of them when using a SQL {@code Date} for the date.
     */
    @Test
    public final void testGetAfterDate_Sql() {
        final Integer readCount;

        readCount = getAfterDateSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(3, readCount);
    }

    /**
     * Tests that retrieving all the entities before a date gives the correct
     * number of them when using a {@code Calendar} for the date.
     */
    @Test
    public final void testGetBeforeDate_Calendar() {
        final Integer readCount;

        readCount = getBeforeDateCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities before a date gives the correct
     * number of them when using a Java {@code Date} for the date.
     */
    @Test
    public final void testGetBeforeDate_Java() {
        final Integer readCount;

        readCount = getBeforeDateJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities before a date gives the correct
     * number of them when using a SQL {@code Date} for the date.
     */
    @Test
    public final void testGetBeforeDate_Sql() {
        final Integer readCount;

        readCount = getBeforeDateSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(2, readCount);
    }

    /**
     * Tests that retrieving all the entities in a date gives the correct number
     * of them when using a {@code Calendar} for the date.
     */
    @Test
    public final void testGetInDate_Calendar() {
        final Integer readCount;

        readCount = getInDateCalendarQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Tests that retrieving all the entities in a date gives the correct number
     * of them when using a Java {@code Date} for the date.
     */
    @Test
    public final void testGetInDate_Java() {
        final Integer readCount;

        readCount = getInDateJavaQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Tests that retrieving all the entities in a date gives the correct number
     * of them when using a SQL {@code Date} for the date.
     */
    @Test
    public final void testGetInDate_Sql() {
        final Integer readCount;

        readCount = getInDateSqlQuery().getResultList().size();

        // Reads the expected number of entities
        Assertions.assertEquals(1, readCount);
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterDateCalendarQuery() {
        return entityManager.createQuery(DateEntityCriteriaFactory
                .findAfterDate(entityManager, calendar));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterDateJavaQuery() {
        return entityManager.createQuery(
                DateEntityCriteriaFactory.findAfterDate(entityManager, date));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getAfterDateSqlQuery() {
        return entityManager.createQuery(DateEntityCriteriaFactory
                .findAfterSqlDate(entityManager, sqlDate));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeDateCalendarQuery() {
        return entityManager.createQuery(DateEntityCriteriaFactory
                .findBeforeDate(entityManager, calendar));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeDateJavaQuery() {
        return entityManager.createQuery(
                DateEntityCriteriaFactory.findBeforeDate(entityManager, date));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getBeforeDateSqlQuery() {
        return entityManager.createQuery(DateEntityCriteriaFactory
                .findBeforeSqlDate(entityManager, sqlDate));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInDateCalendarQuery() {
        return entityManager.createQuery(
                DateEntityCriteriaFactory.findInDate(entityManager, calendar));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInDateJavaQuery() {
        return entityManager.createQuery(
                DateEntityCriteriaFactory.findInDate(entityManager, date));
    }

    /**
     * Returns the query for the test.
     * 
     * @return the query for the test
     */
    private final Query getInDateSqlQuery() {
        return entityManager.createQuery(DateEntityCriteriaFactory
                .findInSqlDate(entityManager, sqlDate));
    }

}
