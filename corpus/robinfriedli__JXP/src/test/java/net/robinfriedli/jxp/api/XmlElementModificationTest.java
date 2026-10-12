package net.robinfriedli.jxp.api;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.testng.annotations.*;

import com.google.common.collect.Lists;
import com.google.common.truth.Truth;
import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;
import net.robinfriedli.jxp.entities.TestElem;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.queries.QueryResult;
import net.robinfriedli.jxp.queries.ResultStream;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import static net.robinfriedli.jxp.queries.Conditions.*;
import static org.testng.Assert.*;

public class XmlElementModificationTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder()
            .mapClass("city", City.class)
            .mapClass("state", State.class)
            .mapClass("country", Country.class)
            .build();
    }

    @Test
    public void testRemoveAttribute() {
        doWithCopiedContext("/countries.xml", context -> {
            State zurich = context.requireElement("Zurich", State.class);
            context.invoke(() -> zurich.removeAttribute("population"));

            XmlAttribute provisionalPopulation = zurich.getAttribute("population");
            assertEquals(provisionalPopulation.getClass(), XmlAttribute.Provisional.class);
            assertEquals(provisionalPopulation.getValue(), "");
            assertEquals((int) provisionalPopulation.getValue(Integer.class), 0);

            Country unitedKingdom = context.requireElement("United Kingdom", Country.class);
            context.invoke(() -> unitedKingdom.getAttribute("englishName").remove());
            expectException(IllegalArgumentException.class, () -> unitedKingdom.getAttribute("englishName").remove());
        });
    }

    @Test
    public void testSimpleElementChange() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));
        City london = new City("London", 8908000);
        XmlElement unitedKingdom = context.requireElement("United Kingdom");

        context.invoke(() -> unitedKingdom.addSubElement(london));

        context.invoke(() -> {
            XmlElement originalLondon = unitedKingdom.query(and(
                attribute("population").is(8900000),
                attribute("name").is("London")
            )).requireOnlyResult();
            originalLondon.delete();
        });

        XmlElement effectiveLondon = unitedKingdom.query(attribute("name").is("London")).getOnlyResult();
        assertNotNull(effectiveLondon);
        assertEquals(effectiveLondon.getAttribute("population").getInt(), 8908000);
        assertEquals(context.query(and(
            attribute("name").is("London"),
            parentMatches(attribute("englishName").is("United Kingdom"))
        )).count(), 1);
    }

    @Test
    public void testInsertDelete() {
        doWithCopiedContext("/countries.xml", context -> {
            XmlElement england = context.requireElement("England");
            City london = england.requireSubElement("London", City.class);
            City manchester = england.requireSubElement("Manchester", City.class);

            context.invoke(() -> england.removeSubElement(london));
            context.invoke(() -> england.addSubElement(london));

            assertTrue(england.getSubElements().contains(london));
            assertEquals(london.getParent(), england);

            context.invoke(() -> {
                england.removeSubElement(london);
                england.addSubElement(london);
            });

            assertTrue(england.getSubElements().contains(london));
            assertEquals(london.getParent(), england);

            context.invoke(() -> {
                List<Node<?>> subElements = Lists.newArrayList(england.getSubElements());
                england.delete();
                england.persist(context);
                england.addSubElements(subElements);
            });

            assertEquals(england.getSubElements().size(), 2);
            assertTrue(england.getSubElements().contains(london));

            City birmingham = new City("Birmingham", 1000000);
            context.invoke(() -> {
                england.addSubElement(birmingham);
                england.delete();
                england.persist(context);
                england.addSubElement(birmingham);
                england.addSubElement(london);
            });

            assertEquals(england.getSubElements().size(), 2);
            assertTrue(england.getSubElements().contains(london));
            assertTrue(england.getSubElements().contains(birmingham));

            context.invoke(true, false, () -> {
                england.delete();
                england.addSubElement(london);
                england.removeSubElement(london);
                england.addSubElement(london);
                england.addSubElement(birmingham);
                england.persist(context);
                england.addSubElement(manchester);
                birmingham.setAttribute("population", "1086000");
            });

            assertEquals(england.getSubElements().size(), 3);
            assertEquals(birmingham.getAttribute("population").getInt(), 1086000);
        });
    }

    @Test
    public void testElementCopy() {
        doWithCopiedContext("/countries.xml", context -> {
            ResultStream<Country> query = context.query(attribute("englishName").is("Switzerland"), Country.class);
            QueryResult<Country, Set<Country>> result = query.getResult(Collectors.toSet());
            assertEquals(result.requireOnlyResult().getId(), "Switzerland");

            TestElem elem = context.invoke(() -> {
                TestElem test = new TestElem("test", "test");
                test.addSubElement(new TestElem("test1", "test1"));
                test.addSubElement(new TestElem("test2", "test2"));
                test.persist(context);
                return test;
            });

            context.invoke(() -> {
                XmlElement copy = elem.copy(true, true);
                elem.setTextContent("test");
                assertEquals(elem.getTextContent(), "test");
                assertEquals(copy.getTextContent(), "");
                assertEquals(copy.getAttribute("testAtr1").getValue(), "test");
                assertEquals(copy.getAttribute("testAtr2").getValue(), "test");
                List<XmlElement> subElements = copy.getSubElements();
                assertEquals(subElements.size(), 2);
                for (XmlElement subElement : subElements) {
                    Truth.assertThat(subElement.getAttribute("testAtr1").getValue()).isAnyOf("test1", "test2");
                    Truth.assertThat(subElement.getAttribute("testAtr2").getValue()).isAnyOf("test1", "test2");
                }
                elem.delete();
            });
        });
    }

    @Test
    public void testPersistDelete() throws ParserConfigurationException {
        Document document = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument();
        Element rootElem = document.createElement("tests");
        rootElem.setAttribute("xmlns", "testSpace");
        document.appendChild(rootElem);
        Context context = jxp.createContext(document);

        TestElem elem = new TestElem("test", "test");
        context.invoke(() -> {
            elem.persist(context);
            elem.delete();
            elem.persist(context);
            elem.delete();
        });

        assertEquals(context.getElements().size(), 0);

        TestElem parent = new TestElem("test", "test");
        TestElem child = new TestElem("test", "test");
        context.invoke(() -> {
            parent.persist(context);
            parent.addSubElement(child);
            parent.delete();
            parent.persist(context);
            parent.addSubElement(child);
            parent.delete();
            parent.addSubElement(child);
            parent.persist(context);
        });

        List<XmlElement> collect = context.query(attribute("testAtr1").is("test")).collect();
        assertEquals(collect.size(), 2);

        XmlElement foundParent;
        XmlElement foundChild;
        if (collect.get(0).isSubElement()) {
            foundParent = collect.get(1);
            foundChild = collect.get(0);
        } else {
            foundParent = collect.get(0);
            foundChild = collect.get(1);
        }

        assertNotNull(foundParent);
        assertNotNull(foundChild);
        assertEquals(foundChild.getParent(), foundParent);

        context.invoke(() -> {
            parent.delete();
            parent.persist(context);
            parent.addSubElement(child);
            parent.delete();
            parent.persist(context);
            parent.addSubElement(child);
            parent.delete();
            parent.addSubElement(child);
            parent.persist(context);
            parent.delete();
        });

        assertEquals(context.getElements().size(), 0);
    }

    @Test
    public void testNewAttribute() {
        doWithCopiedContext("/countries.xml", context -> {
            City zurich = context.query(and(
                attribute("name").is("Zurich"),
                instanceOf(City.class)
            ), City.class).requireOnlyResult();

            XmlAttribute newArg1i1 = zurich.getAttribute("newArg1");
            XmlAttribute newArg1i2 = zurich.getAttribute("newArg1");
            assertEquals(newArg1i1.getValue(), "");
            assertEquals(newArg1i2.getValue(), "");

            context.invoke(() -> {
                newArg1i1.setValue("newVal1");
                assertEquals(zurich.getAttribute("newArg1").getValue(), "newVal1");
                assertEquals(newArg1i2.getValue(), "newVal1");
                zurich.setAttribute("newArg1", "newVal2");
                assertEquals(newArg1i2.getValue(), "newVal2");
                newArg1i2.setValue("newVal1");
                assertEquals(zurich.getAttribute("newArg1").getValue(), "newVal1");
            });

            XmlAttribute newArg2i1 = zurich.getAttribute("newArg2");
            XmlAttribute newArg2i2 = zurich.getAttribute("newArg2");

            context.invoke(true, false, () -> {
                assertFalse(zurich.hasAttribute("newArg2"));
                newArg2i2.setValue("newVal2");
            });

            assertTrue(zurich.hasAttribute("newArg2"));
            assertEquals(zurich.getAttribute("newArg2").getValue(), "newVal2");
            assertEquals(newArg2i1.getValue(), "newVal2");
        });
    }

    @Test(expectedExceptions = PersistException.class)
    public void testPersistSubElementWithoutParent() {
        doWithCopiedContext("/countries.xml", context -> context.invoke(() -> {
            City city = new City("testY", 0);
            new Country("TestC", "testC", true, Lists.newArrayList(city));
            city.persist(context);
        }));
    }

    @Test(expectedExceptions = PersistException.class)
    public void testPersistSubElementAndParent() {
        doWithCopiedContext("/countries.xml", context -> context.invoke(() -> {
            City city = new City("testY", 0);
            Country country = new Country("TestC", "testC", true, Lists.newArrayList(city));
            country.persist(context);
            city.persist(context);
        }));
    }

    @Test
    public void testCreateFromDocument() throws ParserConfigurationException {
        Document document = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument();
        Element rootElem = document.createElement("tests");
        rootElem.setAttribute("xmlns", "testSpace");
        document.appendChild(rootElem);
        Context context = jxp.getContext(document);

        XmlElement element0 = new BaseXmlElement("test0");

        Map<String, String> map = new HashMap<>();
        map.put("atr", "val");
        XmlElement element1 = new BaseXmlElement("test1", map);
        XmlElement element2 = new BaseXmlElement("test2", Lists.newArrayList(element1));
        XmlElement element3 = new BaseXmlElement("test3", "text content");
        XmlElement element4 = new BaseXmlElement("test4", map, Lists.newArrayList(element2));
        XmlElement element5 = new BaseXmlElement("test5", map, "text content");
        XmlElement element6 = new BaseXmlElement("test6", Lists.newArrayList(element3), "text content");
        XmlElement element7 = new BaseXmlElement("test7", map, Lists.newArrayList(element4), "text content");

        context.invoke(() -> {
            element0.persist(context);
            element5.persist(context);
            element6.persist(context);
            element7.persist(context);
        });

        context.persist(String.format("src/test/resources/output/%s%s%s.xml", getClass().getSimpleName(), "@testCreateFromDocument", System.currentTimeMillis()));

        context.invoke(() -> element6.setTextContent("text content 6"));
    }

    @Test
    public void testProhibitDuplicateCreation() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));

        expectException(PersistException.class, () -> context.invoke(() -> {
            TestElem elem = new TestElem("test", "test");
            elem.persist(context);
            elem.persist(context);
        }));

        expectException(PersistException.class, () -> context.invoke(() -> {
            TestElem elem1 = new TestElem("test", "test");
            TestElem elem2 = new TestElem("test", "test");

            elem1.persist(context);
            elem1.addSubElement(elem2);
            elem1.addSubElement(elem2);
        }));
    }

    @Test
    public void testRelativePositioning() {
        doWithCopiedContext("/countries.xml", context -> {
            XmlElement documentElement = context.getDocumentElement();
            XmlElement unitedKingdom = context.requireElement("United Kingdom");
            XmlElement england = context.requireElement("England");

            Country unitedStates = new Country("United States", "United States", true);
            City newYork = new City("New York", 8400000);
            State newYorkState = new State("New York", 19450000, Lists.newArrayList(newYork));
            unitedStates.addSubElement(newYorkState);
            City chicago = new City("Chicago", 2700000);
            State illinois = new State("Illinois", 12600000, Lists.newArrayList(chicago));
            unitedStates.insertSubElementBefore(newYorkState, illinois);

            Country ireland = new Country("Ireland", "Ireland", true);
            City dublin = new City("Dublin", 1300000);
            State leinster = new State("Leinster", 2600000, Lists.newArrayList(dublin));
            ireland.addSubElement(leinster);
            context.invoke(() -> {
                documentElement.insertSubElementsAfter(unitedKingdom, unitedStates);
                documentElement.insertSubElementsBefore(england, ireland);
            });

            assertEquals(unitedKingdom.getNextSibling(), unitedStates);
            assertEquals(unitedStates.getPreviousSibling(), unitedKingdom);

            Node<?> nextSibling = unitedStates.getNextSibling();
            while (nextSibling != null && !(nextSibling instanceof XmlElement)) {
                nextSibling = nextSibling.getNextSibling();
            }
            assertEquals(nextSibling, ireland);
        });
    }

    @Test
    public void testInsertSeveral() {
        doWithCopiedContext("/countries.xml", context -> {
            XmlElement documentElement = context.getDocumentElement();
            XmlElement firstSub = documentElement.getSubElements().get(0);

            TestElem elem1 = new TestElem("t", "t");
            TestElem elem11 = new TestElem("tt", "tt");
            elem1.addSubElement(elem11);
            TestElem elem15 = new TestElem("t15", "t15");
            TestElem elem2 = new TestElem("t2", "t2");
            TestElem elem3 = new TestElem("t3", "t3");

            context.invoke(() ->
                documentElement.insertSubElementsBefore(firstSub, elem1, elem15, elem2, elem3)
            );

            assertEquals(firstSub.getPreviousSibling(), elem3);
            assertEquals(elem1.getNextSibling(), elem15);
            assertEquals(elem15.getPreviousSibling(), elem1);
            assertEquals(elem15.getNextSibling(), elem2);
            assertEquals(elem2.getPreviousSibling(), elem15);
            assertEquals(elem2.getNextSibling(), elem3);
            assertEquals(elem3.getPreviousSibling(), elem2);

            TestElem elem12 = new TestElem("t12", "t12");
            TestElem elem13 = new TestElem("t13", "t13");
            TestElem elem14 = new TestElem("t14", "t14");
            TestElem elem16 = new TestElem("t16", "t16");
            TestElem elem17 = new TestElem("t17", "t17");
            TestElem elem18 = new TestElem("t18", "t18");

            context.invoke(() -> {
                documentElement.insertSubElementsBefore(elem15, elem12, elem13, elem14);
                documentElement.insertSubElementsAfter(elem15, elem16, elem17, elem18);
            });

            assertEquals(elem12.getPreviousSibling(), elem1);
            assertEquals(elem12.getNextSibling(), elem13);
            assertEquals(elem13.getPreviousSibling(), elem12);
            assertEquals(elem13.getNextSibling(), elem14);
            assertEquals(elem14.getPreviousSibling(), elem13);
            assertEquals(elem14.getNextSibling(), elem15);
            assertEquals(elem15.getPreviousSibling(), elem14);
            assertEquals(elem15.getNextSibling(), elem16);
            assertEquals(elem16.getPreviousSibling(), elem15);
            assertEquals(elem16.getNextSibling(), elem17);
            assertEquals(elem17.getPreviousSibling(), elem16);
            assertEquals(elem17.getNextSibling(), elem18);
            assertEquals(elem18.getPreviousSibling(), elem17);
            assertEquals(elem18.getNextSibling(), elem2);
        });
    }

    @Test
    public void testSetMixedContent() {
        doWithCopiedContext("/countries.xml", context -> {
            XmlElement england = context.requireElement("England");
            context.invoke(() -> england.setTextContent("test"));
        });
    }

}
