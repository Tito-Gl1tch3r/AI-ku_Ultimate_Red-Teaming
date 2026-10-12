package net.robinfriedli.jxp.queries;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import org.testng.annotations.*;

import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.JxpBuilder;
import net.robinfriedli.jxp.api.StringConverter;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Continent;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;
import net.robinfriedli.jxp.exceptions.QueryException;
import net.robinfriedli.jxp.persist.Context;

import static net.robinfriedli.jxp.queries.Conditions.*;
import static org.testng.Assert.*;

public class QueryTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder()
            .mapClass("city", City.class)
            .mapClass("state", State.class)
            .mapClass("country", Country.class)
            .mapClass("continent", Continent.class)
            .build();
    }

    @Test
    public void testOrderByIntegerAttribute() {
        Context context = jxp.createContext(getTestResource("/fullcountries.xml"));
        List<Country> sortedCountries = context.query(instanceOf(Country.class), Country.class).order(Order.attribute("iso", Integer.class)).collect();

        assertTrue(sortedCountries.size() > 10);

        assertEquals(sortedCountries.get(0).getAttribute("iso").getInt(), 4);
        assertEquals(sortedCountries.get(1).getAttribute("iso").getInt(), 8);
        assertEquals(sortedCountries.get(2).getAttribute("iso").getInt(), 10);
        assertEquals(sortedCountries.get(3).getAttribute("iso").getInt(), 12);
        assertEquals(sortedCountries.get(4).getAttribute("iso").getInt(), 16);
        assertEquals(sortedCountries.get(5).getAttribute("iso").getInt(), 20);
        assertEquals(sortedCountries.get(6).getAttribute("iso").getInt(), 24);
        assertEquals(sortedCountries.get(7).getAttribute("iso").getInt(), 28);
        assertEquals(sortedCountries.get(8).getAttribute("iso").getInt(), 31);
        assertEquals(sortedCountries.get(9).getAttribute("iso").getInt(), 32);
    }

    @Test
    public void testOrderByStringAttribute() {
        Context context = jxp.createContext(getTestResource("/fullcountries.xml"));
        List<Country> countries = context.query(instanceOf(Country.class), Country.class).order(Order.attribute("name", Order.Direction.DESCENDING)).collect();

        assertTrue(countries.size() > 10);

        assertEquals(countries.get(0).getAttribute("name").getValue(), "Zimbabwe");
        assertEquals(countries.get(1).getAttribute("name").getValue(), "Zambia");
        assertEquals(countries.get(2).getAttribute("name").getValue(), "Zaire");
        assertEquals(countries.get(3).getAttribute("name").getValue(), "Yugoslavia");
        assertEquals(countries.get(4).getAttribute("name").getValue(), "Yemen");
        assertEquals(countries.get(5).getAttribute("name").getValue(), "Western Sahara");
        assertEquals(countries.get(6).getAttribute("name").getValue(), "Wallis And Futuna Islands");
        assertEquals(countries.get(7).getAttribute("name").getValue(), "Virgin Islands (U.S.)");
        assertEquals(countries.get(8).getAttribute("name").getValue(), "Virgin Islands (British)");
        assertEquals(countries.get(9).getAttribute("name").getValue(), "Vietnam");
        assertEquals(countries.get(10).getAttribute("name").getValue(), "Venezuela");
    }

    /**
     * Queries should fail because they find both a state and city and match the query condition while attempting to
     * cast the result city.
     */
    @Test
    public void testExpectConversionError() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));
        expectException(QueryException.class, () -> context.query(attribute("name").is("Zurich"), City.class).collect());
        expectException(QueryException.class, () -> context.query(attribute("name").is("Zurich"), City.class).count());
    }

    @Test
    public void testSimpleQueries() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));
        XmlElement england = context.query(and(
            attribute("sovereign").is(false),
            not(attribute("name").is("Scotland"))
        )).requireOnlyResult();
        XmlElement switzerland = context.query(attribute("englishName").in("Switzerland", "Swiss", "Schweiz")).requireOnlyResult();
        XmlElement london = context.query(
            and(
                attribute("population").greaterThan(800000),
                subElementOf(england),
                instanceOf(City.class),
                textContent().isEmpty()
            )
        ).requireOnlyResult();
        Set<XmlElement> ldnSet = Query.evaluate(and(
            attribute("population").greaterThan(8000000),
            tagName("city")
        )).execute(context.getElementsRecursive()).collect(Collectors.toSet());
        assertFalse(england.getAttribute("sovereign").getBool());
        assertEquals(england.getAttribute("name").getValue(), "England");
        assertEquals(london.getParent(), england);
        assertEquals(switzerland.getAttribute("name").getValue(), "Schweiz");
        assertEquals(ldnSet.iterator().next().getAttribute("name").getValue(), "London");

        List<XmlElement> found = context.query(attribute("name").is(4)).collect();// this no longer throws an exception since 1.1
        assertEquals(found.size(), 0);
        expectException(IllegalStateException.class, () -> context.query(attribute("name").is(context)).collect());

        XmlElement unitedKingdom = context.requireElement("United Kingdom");
        XmlElement foundLondon = context.query(and(
            attribute("name").is("London"),
            parentMatches(parentMatches(attribute("name").is("United Kingdom")))
        )).requireOnlyResult();
        assertEquals(foundLondon, unitedKingdom.requireSubElement("Greater London").requireSubElement("London"));
        assertEquals(Query.evaluate(attribute("englishName").startsWith("Swe")).execute(context.getElements()).count(), 1);
    }

    @Test
    public void testAddConversion() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));
        XmlElement london = context.query(and(
            attribute("name").is("London"),
            parentMatches(instanceOf(State.class))
        )).requireOnlyResult();
        StringConverter.map(null, City.class, s -> new City(s, 1000), c -> c.getAttribute("name").getValue());
        assertTrue(StringConverter.canConvert(City.class));
        City newCity = london.getAttribute("name").getValue(City.class);
        assertEquals(newCity.getAttribute("population").getInt(), 1000);
        assertEquals(newCity.getAttribute("name").getValue(), "London");
    }

    @Test
    public void testSubElementsMatch() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));
        XmlElement unitedKingdom = context.query(allSubElementsMatch(and(
            or(
                attribute("name").startsWith("Greater"),
                attribute("name").contains("Edinburgh")
            ),
            parentMatches(attribute("name").startsWith("United"))
        ))).requireOnlyResult();
        assertEquals(unitedKingdom.getAttribute("name").getValue(), "United Kingdom");

        XmlElement cityOfEdinburgh = context.query(existsSubElement(and(
            attribute("name").is("Edinburgh"),
            parentMatches(instanceOf(State.class))
        ))).requireOnlyResult();

        assertEquals(cityOfEdinburgh.getAttribute("name").getValue(), "City of Edinburgh");
        assertTrue(cityOfEdinburgh instanceof State);
        assertTrue(cityOfEdinburgh.getParent() instanceof Country);
    }

}
