package net.robinfriedli.jxp.persist;

import org.testng.annotations.*;

import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.JxpBuilder;
import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;
import net.robinfriedli.jxp.events.JxpEventListener;
import net.robinfriedli.jxp.exceptions.PersistException;

import static org.testng.Assert.*;

public class RollbackTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder()
            .mapClass("city", City.class)
            .mapClass("state", State.class)
            .mapClass("country", Country.class)
            .build();
    }

    @Test
    public void testSimpleRollback() {
        RollbackListener rollbackListener = new RollbackListener();
        jxp.addListener(rollbackListener);
        try {
            doWithCopiedContext("/countries.xml", context -> {
                State zurich = context.requireElement("Zurich", State.class);
                expectException(PersistException.class, () -> context.invoke(() -> {
                    zurich.removeAttribute("population");
                    zurich.setAttribute("name", "test");
                    zurich.delete();
                }));

                State zurich1 = context.getElement("Zurich", State.class);
                assertNotNull(zurich1);
                assertEquals(zurich.getAttribute("population").getInt(), 1500000);
            });
        } finally {
            jxp.removeListener(rollbackListener);
        }
    }

    @Test
    public void testRollbackInsertDelete() {
        RollbackListener rollbackListener = new RollbackListener();
        jxp.addListener(rollbackListener);
        try {
            doWithCopiedContext("/countries.xml", context -> {
                XmlElement england = context.requireElement("England");
                City london = england.requireSubElement("London", City.class);
                City manchester = england.requireSubElement("Manchester", City.class);

                expectException(PersistException.class, () -> context.invoke(() -> england.removeSubElement(london)));

                assertTrue(england.getSubElements().contains(london));
                assertEquals(london.getParent(), england);

                expectException(PersistException.class, () -> context.invoke(() -> {
                    england.removeSubElement(london);
                    england.addSubElement(london);
                }));

                assertTrue(england.getSubElements().contains(london));
                assertEquals(london.getParent(), england);

                expectException(PersistException.class, () -> context.invoke(england::delete));

                assertEquals(england.getSubElements().size(), 2);
                assertTrue(england.getSubElements().contains(london));

                City birmingham = new City("Birmingham", 1000000);
                expectException(PersistException.class, () -> context.invoke(() -> {
                    england.addSubElement(birmingham);
                    england.delete();
                    england.persist(context);
                    england.addSubElement(birmingham);
                    england.addSubElement(london);
                }));

                assertEquals(england.getSubElements().size(), 2);
                assertTrue(england.getSubElements().contains(london));
                assertTrue(england.getSubElements().contains(manchester));

                expectException(PersistException.class, () -> context.invoke(true, false, () -> {
                    england.delete();
                    england.addSubElement(london);
                    england.removeSubElement(london);
                    england.addSubElement(london);
                    england.addSubElement(birmingham);
                    england.persist(context);
                    england.addSubElement(manchester);
                    birmingham.setAttribute("population", "1086000");
                }));

                assertEquals(england.getSubElements().size(), 2);
                assertTrue(england.getSubElements().contains(london));
                assertTrue(england.getSubElements().contains(manchester));
                assertEquals(birmingham.getAttribute("population").getInt(), 1000000);
            });
        } finally {
            jxp.removeListener(rollbackListener);
        }
    }

    @Test
    public void testRollbackDeletion() {
        RollbackListener listener = new RollbackListener();
        jxp.addListener(listener);
        try {
            doWithCopiedContext("/countries.xml", context -> {
                XmlElement sweden = context.requireElement("Sweden");
                XmlElement france = context.requireElement("France");

                expectException(PersistException.class, () -> context.invoke(() -> {
                    sweden.delete();
                    france.delete();
                }));

                XmlElement england = context.requireElement("England");
                assertEquals(getNextXmlElementSibling(england), sweden);
                assertEquals(getNextXmlElementSibling(sweden), france);
            });
        } finally {
            jxp.removeListener(listener);
        }
    }

    private XmlElement getNextXmlElementSibling(XmlElement element) {
        Node<?> nextSibling = element.getNextSibling();
        while (nextSibling != null && !(nextSibling instanceof XmlElement)) {
            nextSibling = nextSibling.getNextSibling();
        }

        return (XmlElement) nextSibling;
    }

    private static class RollbackListener extends JxpEventListener {

        protected RollbackListener() {
            super(true);
        }

        @Override
        public void onBeforeFlush(Transaction transaction) {
            throw new RuntimeException("Rollback");
        }
    }

}
