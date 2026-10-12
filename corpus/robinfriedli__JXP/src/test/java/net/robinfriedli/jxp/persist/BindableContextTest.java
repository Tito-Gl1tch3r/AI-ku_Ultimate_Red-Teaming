package net.robinfriedli.jxp.persist;

import org.testng.annotations.*;

import com.google.common.collect.Lists;
import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.JxpBuilder;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;

import static net.robinfriedli.jxp.queries.Conditions.*;
import static org.junit.Assert.*;

public class BindableContextTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder()
            .mapClass("city", City.class)
            .mapClass("state", State.class)
            .mapClass("country", Country.class)
            .build();
    }

    @Test
    public void testCreateAndRetrieveBoundContext() {
        Context context = jxp.createContext(getTestResource("/countries.xml"));
        Context.BindableContext<String> c1 = context.copy("c1");
        Context.BindableContext<String> c2 = context.copy("c2");
        jxp.attachContext(c1);
        jxp.attachContext(c2);

        c1.invoke(() -> {
            City rome = new City("Rome", 2800000);
            State state = new State("Lazio", 5800000, Lists.newArrayList(rome));
            Country italy = new Country("Italia", "Italy", true, Lists.newArrayList());
            italy.addSubElement(state);
            italy.setAttribute("population", 60480000);
            italy.persist(c1);
        });

        c2.invoke(() -> {
            City barcelona = new City("Barcelona", 1600000);
            State state = new State("Province of Barcelona", 5600000, Lists.newArrayList(barcelona));
            Country spain = new Country("Espana", "Spain", true, Lists.newArrayList());
            spain.addSubElement(state);
            spain.setAttribute("population", 46700000);
            spain.persist(c2);
        });

        c1.persist("src/test/resources/output/BindableContextTest@testCreateAndRetrieveBoundContext-C1-" + System.currentTimeMillis() + ".xml");
        c2.persist("src/test/resources/output/BindableContextTest@testCreateAndRetrieveBoundContext-C2-" + System.currentTimeMillis() + ".xml");

        Context.BindableContext<String> context1 = jxp.getBoundContext("c1");
        Context.BindableContext<String> context2 = jxp.getBoundContext("c2");
        assertNotNull(context1);
        assertNotNull(context2);

        XmlElement italy = context1.query(attribute("englishName").is("Italy")).getOnlyResult();
        XmlElement italy1 = context2.query(attribute("englishName").is("Italy")).getOnlyResult();
        XmlElement italy2 = context.query(attribute("englishName").is("Italy")).getOnlyResult();
        assertNotNull(italy);
        assertNull(italy1);
        assertNull(italy2);
        assertEquals(italy.getAttribute("population").getInt(), 60480000);
        XmlElement lazio = italy.getSubElement("Lazio");
        assertNotNull(lazio);

        XmlElement provinceOfBarcelona = c2.query(attribute("name").is("Province of Barcelona")).getOnlyResult();
        assertNotNull(provinceOfBarcelona);
        assertEquals(provinceOfBarcelona.getAttribute("population").getInt(), 5600000);
    }

}
