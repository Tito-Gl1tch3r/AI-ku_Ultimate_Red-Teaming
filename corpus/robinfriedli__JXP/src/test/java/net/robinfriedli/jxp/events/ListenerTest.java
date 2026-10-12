package net.robinfriedli.jxp.events;

import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.stream.Collectors;

import org.testng.annotations.*;

import com.google.common.collect.Lists;
import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.JxpBuilder;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;
import net.robinfriedli.jxp.exec.QueuedTask;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.Transaction;

import static net.robinfriedli.jxp.queries.Conditions.*;
import static org.testng.Assert.*;

public class ListenerTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder()
            .mapClass("city", City.class)
            .mapClass("state", State.class)
            .mapClass("country", Country.class)
            .build();
    }

    @Test
    public void testInvokeWithoutListeners() {
        TestTrigger testTrigger = new TestTrigger();
        jxp.addListener(testTrigger);
        Context context = jxp.createContext(getTestResource("/countries.xml"));

        context.invokeWithoutListeners(() -> {
            context.requireElement("Switzerland").delete();
            XmlElement unitedKingdom = context.requireElement("United Kingdom");
            XmlElement london = unitedKingdom.query(attribute("name").is("London")).requireOnlyResult();
            london.setAttribute("population", 32);
            Country newCountry = new Country();
            newCountry.persist(context);
        });

        QueuedTask<Void> queuedTask = context.futureInvoke(true, true, false, false, false, () -> {
            XmlElement greaterManchester = context.requireElement("Greater Manchester");
            greaterManchester.setAttribute("population", 3);
            greaterManchester.requireSubElement("Manchester").delete();

            return null;
        });

        Thread t = new Thread(queuedTask);
        t.start();

        try {
            t.join();
        } catch (InterruptedException ignored) {
        }

        jxp.removeListener(testTrigger);
        assertFalse(testTrigger.isTriggered());
    }

    @Test
    public void testListenerModifications() {
        TestListener listener = new TestListener();
        jxp.addListener(listener);
        try {
            doWithCopiedContext("/countries.xml", context -> {
                XmlElement england = context.requireElement("England");
                XmlElement france = context.requireElement("France");

                context.invoke(() -> {
                    france.delete();
                    england.delete();
                });

                XmlElement london = england.requireSubElement("London");
                assertEquals(london.getAttribute("population").getInt(), 8900001);
                XmlElement retrievedFrance = context.getElement("France");
                assertNotNull(retrievedFrance);

                QueuedTask<City> futureEdinburgh = context.invoke(() -> {
                    Country scotland = new Country("Scotland", "Scotland", false, Lists.newArrayList());
                    return context.futureInvoke(() -> {
                        scotland.persist(context);
                        City edinburgh = new City("Edinburgh", 500000);
                        scotland.addSubElement(edinburgh);
                        return edinburgh;
                    });
                });

                try {
                    City edinburgh = futureEdinburgh.get();
                    assertEquals(edinburgh.getAttribute("name").getValue(), "Edinburgh");
                } catch (InterruptedException ignored) {
                } catch (ExecutionException e) {
                    throw new RuntimeException(e);
                }
            });
        } finally {
            jxp.removeListener(listener);
        }
    }

    @Test
    public void testCityManagementListener() {
        CountryManagementListener countryManagementListener = new CountryManagementListener();
        jxp.addListener(countryManagementListener);
        try {
            doWithCopiedContext("/countries.xml", context -> {
                context.invokeWithoutListeners(() -> context.requireElement("United Kingdom").delete());

                context.invoke(() -> new Country("United Kingdom", "United Kingdom", true, Lists.newArrayList()).persist(context));
                XmlElement unitedKingdom = context.requireElement("United Kingdom");
                List<XmlElement> subElements = unitedKingdom.getSubElements();
                assertEquals(subElements.size(), 3);
                XmlElement london = unitedKingdom.getSubElement("London");
                XmlElement edinburgh = unitedKingdom.getSubElement("Edinburgh");
                assertNotNull(london);
                assertNotNull(edinburgh);

                XmlElement england = context.requireElement("England");
                context.invoke(() -> {
                    City birmingham = new City("Birmingham", 1000000);
                    england.addSubElement(birmingham);
                });

                List<XmlElement> subElements1 = unitedKingdom.getSubElements();
                assertEquals(subElements1.size(), 4);
                XmlElement birmingham = unitedKingdom.getSubElement("Birmingham");
                assertNotNull(birmingham);
                assertEquals(birmingham.getAttribute("population").getInt(), 1000000);
                assertEquals(unitedKingdom.getAttribute("cityCount").getInt(), 4);
                assertEquals(england.getAttribute("cityCount").getInt(), 3);
            });
        } finally {
            jxp.removeListener(countryManagementListener);
        }
    }

    private static class TestListener extends JxpEventListener {

        @Override
        public void transactionApplied(Transaction transaction) {
            List<XmlElement> deleted = transaction
                .getDeletedElements()
                .stream()
                .filter(event -> event.getSource() instanceof Country)
                .filter(event -> !event.getSource().getAttribute("sovereign").getBool())
                .map(Event::getSource)
                .collect(Collectors.toList());

            if (!deleted.isEmpty()) {
                XmlElement england = deleted.get(0);
                City london = new City("London", 8900001);
                City manchester = new City("Manchester", 510000);
                england.addSubElements(london, manchester);
                england.persist(transaction.getContext());
            }
        }

        @Override
        public void onBeforeFlush(Transaction transaction) {
            List<XmlElement> deleted = transaction
                .getDeletedElements()
                .stream()
                .filter(event -> event.getSource() instanceof Country)
                .filter(event -> event.getSource().getAttribute("sovereign").getBool())
                .map(Event::getSource)
                .collect(Collectors.toList());

            if (!deleted.isEmpty()) {
                transaction.getContext().futureInvoke(() -> {
                    XmlElement france = deleted.get(0);
                    City paris = new City("Paris", 2000000);
                    france.addSubElement(paris);
                    france.persist(transaction.getContext());
                    return null;
                });
            }
        }

    }

    private static class CountryManagementListener extends JxpEventListener {

        @Override
        public void elementCreating(ElementCreatedEvent event) {
            XmlElement source = event.getSource();
            Context context = source.getContext();

            if (source instanceof Country && source.getAttribute("englishName").getValue().equals("United Kingdom")) {
                for (XmlElement englandCity : context.requireElement("England").getSubElements()) {
                    source.addSubElement(englandCity.copy(true, true));
                }

                for (XmlElement scotlandCity : context.requireElement("Scotland").getSubElements()) {
                    source.addSubElement(scotlandCity.copy(true, true));
                }

                source.setAttribute("cityCount", source.getSubElements().size());
            }

            if (source instanceof City) {
                XmlElement country = source.getParent();
                if (country.hasAttribute("cityCount")) {
                    int cityCount = country.getAttribute("cityCount").getInt() + 1;
                    country.setAttribute("cityCount", cityCount);
                } else {
                    country.setAttribute("cityCount", country.getSubElements().size());
                }
            }
        }

        @Override
        public void onBeforeFlush(Transaction transaction) {
            Context context = transaction.getContext();
            List<XmlElement> createdCities = transaction
                .getCreatedElements()
                .stream()
                .map(Event::getSource)
                .filter(e -> e instanceof City)
                .collect(Collectors.toList());

            if (!createdCities.isEmpty()) {
                context.futureInvoke(() -> {
                    for (XmlElement city : createdCities) {
                        String countryName = city.getParent().getAttribute("englishName").getValue();
                        if (countryName.equals("England") || countryName.equals("Scotland")) {
                            XmlElement unitedKingdom = context.requireElement("United Kingdom");
                            unitedKingdom.addSubElement(city.copy(true, true));
                        }
                    }

                    return null;
                });
            }
        }

    }

    private static class TestTrigger extends JxpEventListener {

        private boolean triggered;

        @Override
        public void elementCreating(ElementCreatedEvent event) {
            triggered = true;
        }

        @Override
        public void elementDeleting(ElementDeletingEvent event) {
            triggered = true;
        }

        @Override
        public void elementChanging(ElementChangingEvent event) {
            triggered = true;
        }

        @Override
        public void transactionApplied(Transaction transaction) {
            triggered = true;
        }

        @Override
        public void transactionCommitted(Transaction transaction) {
            triggered = true;
        }

        @Override
        public void onBeforeFlush(Transaction transaction) {
            triggered = true;
        }

        boolean isTriggered() {
            return triggered;
        }
    }

}
