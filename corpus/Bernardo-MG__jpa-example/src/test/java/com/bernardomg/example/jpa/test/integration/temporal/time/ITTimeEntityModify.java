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

import org.junit.jupiter.api.Assertions;
import org.springframework.test.context.junit.jupiter.EnabledIf;

import com.bernardomg.example.jpa.model.temporal.TimeEntity;
import com.bernardomg.example.jpa.test.config.test.integration.AbstractITEntityModify;

/**
 * Integration tests for a {@code TimeEntity} testing it can be modified.
 *
 * @author Bernardo Mart&iacute;nez Garrido
 */
@EnabledIf(expression = "#{!'${jpa.adapter.class}'.contains('Hibernate')}",
        reason = "Supports persisted time", loadContext = true)
public class ITTimeEntityModify extends AbstractITEntityModify<TimeEntity> {

    /**
     * Value to set on the time for the tests.
     */
    private final String timeString = "11:11:11";

    /**
     * Default constructor.
     */
    public ITTimeEntityModify() {
        super(TimeEntity::new, 6);
    }

    @Override
    protected final void assertEntityModified(final TimeEntity entity) {
        final DateFormat format; // Format for parsing the time string
        final Date date;         // Parsed time
        final Calendar calendar; // Parsed time as calendar

        format = new SimpleDateFormat("hh:mm:ss", Locale.ENGLISH);

        try {
            date = format.parse(timeString);
            calendar = Calendar.getInstance();
            calendar.setTime(date);

            Assertions.assertEquals(date, entity.getDate());
            Assertions.assertEquals(calendar, entity.getCalendar());
            Assertions.assertEquals(new Time(date.getTime()),
                    entity.getSqlTime());
        } catch (final ParseException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    protected final void modifyEntity(final TimeEntity entity) {
        final DateFormat format; // Format for parsing the time string
        final Date date;         // Parsed time
        final Calendar calendar; // Parsed time as calendar

        format = new SimpleDateFormat("hh:mm:ss", Locale.ENGLISH);

        try {
            date = format.parse(timeString);
            calendar = Calendar.getInstance();
            calendar.setTime(date);

            entity.setCalendar(calendar);
            entity.setDate(date);
            entity.setSqlTime(new Time(date.getTime()));
        } catch (final ParseException e) {
            throw new RuntimeException(e);
        }
    }

}
