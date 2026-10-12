package net.robinfriedli.jxp.persist;

import java.util.List;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.testng.annotations.*;

import com.google.common.collect.Lists;
import com.google.common.truth.Truth;
import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.JxpBuilder;
import net.robinfriedli.jxp.api.UninitializedParent;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.collections.NodeList;
import net.robinfriedli.jxp.collections.UninitializedNodeList;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;
import net.robinfriedli.jxp.queries.Conditions;
import net.robinfriedli.jxp.queries.Query;
import net.robinfriedli.jxp.queries.xpath.XQueryBuilder;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import static net.robinfriedli.jxp.queries.xpath.XConditions.*;
import static org.testng.Assert.*;

public class LazyContextTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder()
            .setDefaultContextType(JxpBackend.DefaultContextType.LAZY)
            .mapClass("country", Country.class)
            .mapClass("state", State.class)
            .mapClass("city", City.class)
            .build();
    }

    @Test
    public void testXPathQuery() throws ParserConfigurationException {
        City london = new City("London", 8900000);
        City manchester = new City("Manchester", 500000);
        City birmingham = new City("Birmingham", 1000000);

        City zurich = new City("Zurich", 400000);
        City geneva = new City("Geneva", 200000);

        City newYork = new City("New York", 8800000);
        City sanFrancisco = new City("San Francisco", 880000);
        City chicago = new City("Chicago", 2700000);

        Country uk = new Country("United Kingdom", "United Kingdom", true, Lists.newArrayList(london, manchester, birmingham));
        Country switzerland = new Country("Schweiz", "Switzerland", true, Lists.newArrayList(zurich, geneva));
        Country england = new Country("England", "England", false, Lists.newArrayList());
        Country us = new Country("United States", "United States", true, Lists.newArrayList(newYork, sanFrancisco, chicago));

        Document document = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument();
        Element rootElem = document.createElement("countries");
        rootElem.setAttribute("xmlns", "countrySpace");
        document.appendChild(rootElem);

        Context context = jxp.getContext(document);
        context.persist("src/test/resources/output/xPathQueryTest" + System.currentTimeMillis() + ".xml");
        context.invoke(() -> {
            uk.persist(context);
            switzerland.persist(context);
            england.addSubElement(london.copy(true, true));
            england.addSubElement(birmingham.copy(true, true));
            england.persist(context);
            us.persist(context);
        });

        XQueryBuilder query = XQueryBuilder.find("country/city").where(and(
            or(
                attribute("population").greaterEquals(1000000),
                attribute("population").is(400000)
            ),
            or(
                attribute("name").startsWith("Zu"),
                attribute("name").endsWith("on"),
                attribute("name").contains("ew")
            )
        ));
        String xPath = query.getXPath(context);
        List<XmlElement> xmlElements = context.xPathQuery(xPath);
        assertEquals(xmlElements.size(), 4);
        for (XmlElement xmlElement : xmlElements) {
            assertTrue(xmlElement.getParent() instanceof UninitializedParent);
            Truth.assertThat(xmlElement.getAttribute("name").getValue()).isAnyOf("London", "Zurich", "New York");
            String parentName = xmlElement.getParent().getAttribute("englishName").getValue();
            XmlElement parent = xmlElement.getParent();
            assertFalse(parent instanceof UninitializedParent);
            Truth.assertThat(parentName).isAnyOf("United Kingdom", "England", "United States", "Switzerland");
            assertTrue(parent.getSubElements().contains(xmlElement));
            switch (parentName) {
                case "United Kingdom":
                case "United States":
                    assertEquals(parent.getSubElements().size(), 3);
                    break;
                case "England":
                case "Switzerland":
                    assertEquals(parent.getSubElements().size(), 2);
                    break;
                default:
                    fail();
                    break;
            }
        }

        XQueryBuilder query1 = XQueryBuilder.find("country").where(and(
            or(
                and(
                    attribute("sovereign").is(false),
                    attribute("englishName").startsWith("Eng"),
                    attribute("name").contains("ngl"),
                    attribute("name").endsWith("land")
                ),
                attribute("name").startsWith("United"),
                attribute("englishName").endsWith("land")
            ),
            not(
                and(
                    attribute("name").startsWith("United"),
                    attribute("name").endsWith("States")
                )
            )
        ));
        String xPath1 = query1.getXPath(context);
        List<XmlElement> xmlElements1 = context.xPathQuery(xPath1);
        assertEquals(xmlElements1.size(), 3);
        for (XmlElement xmlElement : xmlElements1) {
            Truth.assertThat(xmlElement.getAttribute("name").getValue()).isAnyOf("United Kingdom", "Schweiz", "England");
        }

        XQueryBuilder query2 = XQueryBuilder.find("country/city").where(or(
            and(
                not(
                    and(
                        attribute("population").in(200000, 400000, 1000000, 8900000),
                        attribute("name").in("Birmingham", "New York")
                    )
                ),
                attribute("population").greaterThan(200000),
                attribute("population").lowerThan(1000000)
            ),
            and(
                or(
                    attribute("population").greaterThan(8000000),
                    attribute("population").lowerThan(1000000)
                ),
                attribute("name").in("London", "Manchester", "Birmingham"),
                not(
                    or(
                        attribute("name").in("New York"),
                        attribute("name").contains("ches"),
                        attribute("name").endsWith("ham")
                    )
                )
            )
        ));
        String xPath2 = query2.getXPath(context);
        List<XmlElement> xmlElements2 = context.xPathQuery(xPath2);
        assertEquals(xmlElements2.size(), 5);
        for (XmlElement xmlElement : xmlElements2) {
            Truth.assertThat(xmlElement.getAttribute("name").getValue()).isAnyOf("London", "Manchester", "Zurich", "San Francisco");
        }
    }

    @Test
    public void testLazyParentInitialization() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));

        String xPath = XQueryBuilder.find("country/state/city").where(
            attribute("name").is("London")
        ).getXPath(context);

        List<XmlElement> xmlElements = context.xPathQuery(xPath);
        assertEquals(xmlElements.size(), 1);

        XmlElement xmlElement = xmlElements.get(0);
        assertTrue(xmlElement.getParent() instanceof UninitializedParent);
        String parentName = xmlElement.getParent().getAttribute("name").getValue();
        XmlElement parent = xmlElement.getParent();
        assertEquals(parentName, "Greater London");
        assertFalse(parent instanceof UninitializedParent);
        assertEquals(parent.getSubElements().size(), 1);
        assertTrue(parent.getSubElements().contains(xmlElement));

        assertTrue(parent.getParent() instanceof UninitializedParent);
        String parentParentName = parent.getParent().getAttribute("name").getValue();
        XmlElement parentParent = parent.getParent();
        assertEquals(parentParentName, "United Kingdom");
        assertTrue(parentParent instanceof Country);
        assertEquals(parentParent.getSubElements().size(), 3);
        assertEquals(parentParent.getSubElementsRecursive().size(), 6);

        XmlElement manchester = parentParent.query(Conditions.attribute("name").is("Manchester")).getOnlyResult();
        assertNotNull(manchester);
        XmlElement manchesterParent = manchester.getParent();
        assertEquals(manchesterParent.getAttribute("name").getValue(), "Greater Manchester");
        assertEquals(manchesterParent.getParent(), parentParent);
    }

    @Test
    public void testGetElements() {
        CachedContext cachedContext = jxp.createCachedContext(getTestResource("/countries.xml"));
        LazyContext context = jxp.createLazyContext(getTestResource("/countries.xml"));
        List<XmlElement> elements = context.getElements();
        assertEquals(elements.size(), cachedContext.getElements().size());

        Query query = Query.evaluate(Conditions.attribute("name").is("London"));
        long count = query.execute(context.getElementsRecursive()).count();
        assertEquals(count, 2);

        context.invoke(false, true, () -> {
            XmlElement london = query.execute(context.getElementsRecursive()).requireFirstResult();
            london.delete();
            long reCount = query.execute(context.getElementsRecursive()).count();
            assertEquals(reCount, 1);
            XmlElement remainingLondon = query.execute(context.getElementsRecursive()).requireOnlyResult();
            remainingLondon.setAttribute("name", "test_change");
            long reCount2 = query.execute(context.getElementsRecursive()).count();
            assertEquals(reCount2, 0);
            long testCount = context.query(Conditions.attribute("name").is("test_change")).count();
            assertEquals(testCount, 1);

            City city = new City("city", 1);
            State state = new State("state", 1, Lists.newArrayList(city));
            Country country = new Country("Country", "Country", true, Lists.newArrayList());
            country.addSubElement(state);
            country.persist(context);
            XmlElement countryResult = context.query(Conditions.attribute("englishName").is("Country")).getOnlyResult();
            assertNotNull(countryResult);
            XmlElement stateResult = countryResult.query(Conditions.tagName("state")).getOnlyResult();
            assertNotNull(stateResult);
            XmlElement cityResult = stateResult.getSubElement("city");
            assertNotNull(cityResult);
            assertEquals(cityResult.getAttribute("population").getInt(), 1);

            country.delete();
            XmlElement foundCountry = context.query(Conditions.attribute("englishName").is("Country")).getOnlyResult();
            assertNull(foundCountry);
            long count1 = context.query(Conditions.attribute("name").is("state")).count();
            long count2 = context.query(Conditions.attribute("name").is("city")).count();
            assertEquals(count1, 0);
            assertEquals(count2, 0);

            country.persist(context);
            XmlElement foundCountry2 = context.query(Conditions.attribute("englishName").is("Country")).getOnlyResult();
            assertNotNull(foundCountry2);
            country.delete();
            XmlElement foundCountry3 = context.query(Conditions.attribute("englishName").is("Country")).getOnlyResult();
            assertNull(foundCountry3);
        });

        context.invoke(false, true, () -> {
            City city = new City("city", 1);
            State state = new State("state", 1, Lists.newArrayList(city));
            Country country = new Country("Country", "Country", true, Lists.newArrayList());
            country.addSubElement(state);
            country.persist(context);

            XmlElement changedLondon = context.query(Conditions.attribute("name").is("test_change")).getOnlyResult();
            assertNotNull(changedLondon);
            changedLondon.setAttribute("name", "London");
        });

        long count1 = query.execute(context.getElementsRecursive()).count();
        assertEquals(count1, 1);
        XmlElement country = context.query(Conditions.attribute("englishName").is("Country")).getOnlyResult();
        assertNotNull(country);
        XmlElement city = country.query(Conditions.attribute("name").is("city")).getOnlyResult();
        assertNotNull(city);
        assertEquals(city.getAttribute("population").getInt(), 1);

        context.invoke(false, false, () -> {
            XmlElement london = query.execute(context.getElementsRecursive()).requireOnlyResult();
            london.setAttribute("name", "test_change");
            long count2 = query.execute(context.getElementsRecursive()).count();
            assertEquals(count2, 1);

            country.delete();
            long countryCount = context.query(Conditions.attribute("englishName").is("Country")).count();
            assertEquals(countryCount, 1);
            long cityCounty = context.query(Conditions.attribute("name").is("city")).count();
            assertEquals(cityCounty, 1);
        });
    }

    @Test
    public void testMixedQueries() {
        LazyContext context = jxp.createLazyContext(getTestResource("/fullcountries.xml"));
        List<XmlElement> relevantElements = context.xPathQuery(XQueryBuilder.find("continent/country").where(attribute("name").startsWith("S")).getXPath(context));
        XmlElement switzerland = Query.evaluate(Conditions.attribute("name").is("Switzerland")).execute(relevantElements).getOnlyResult();
        XmlElement sweden = Query.evaluate(Conditions.attribute("name").is("Sweden")).execute(relevantElements).getOnlyResult();
        assertNotNull(switzerland);
        assertNotNull(sweden);
        List<XmlElement> results = Query.evaluate(Conditions.attribute("name").startsWith("Slov")).execute(relevantElements).collect();
        assertEquals(results.size(), 2);
        context.invoke(() -> {
            switzerland.setAttribute("population", 8570000);
            sweden.setAttribute("population", 10230000);
            for (XmlElement result : results) {
                result.delete();
            }
        });


        List<XmlElement> results2 = context.xPathQuery(XQueryBuilder.find("continent/country").where(attribute("name").startsWith("Slov")).getXPath(context));
        assertEquals(results2.size(), 0);
        List<XmlElement> results3 = context.xPathQuery(XQueryBuilder.find("continent/country").where(attribute("name").startsWith("Slov")).getXPath(context));
        assertEquals(results3.size(), 0);
        List<XmlElement> switzerlandResults = context.xPathQuery(XQueryBuilder.find("continent/country").where(attribute("name").is("Switzerland")).getXPath(context));
        assertEquals(switzerlandResults.size(), 1);
        assertEquals(switzerlandResults.get(0).getAttribute("population").getInt(), 8570000);
        List<XmlElement> swedenResults = context.xPathQuery(XQueryBuilder.find("continent/country").where(attribute("name").is("Sweden")).getXPath(context));
        assertEquals(swedenResults.size(), 1);
        assertEquals(swedenResults.get(0).getAttribute("population").getInt(), 10230000);

        context.persist(String.format("src/test/resources/output/%s%s%s.xml", getClass().getSimpleName(), "@testMixedQueries", System.currentTimeMillis()));
    }

    @Test
    public void testLazyInitialization() {
        LazyContext context = jxp.createLazyContext(getTestResource("/countries.xml"));
        XmlElement documentElement = context.getDocumentElement();
        NodeList childNodeList = documentElement.internal().getInternalChildNodeList();

        assertTrue(childNodeList instanceof UninitializedNodeList);
        UninitializedNodeList uninitializedNodeList = (UninitializedNodeList) childNodeList;
        assertFalse(uninitializedNodeList.isInitialized());

        XmlElement england = documentElement.requireSubElement("England");
        NodeList englandChildNodeList = england.internal().getInternalChildNodeList();
        assertTrue(englandChildNodeList instanceof UninitializedNodeList);
        UninitializedNodeList uninitializedEnglandNodeList = (UninitializedNodeList) englandChildNodeList;
        assertFalse(uninitializedEnglandNodeList.isInitialized());
        assertTrue(uninitializedNodeList.isInitialized());
    }

}
