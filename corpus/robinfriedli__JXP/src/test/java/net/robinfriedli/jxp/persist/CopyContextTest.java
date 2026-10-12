package net.robinfriedli.jxp.persist;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.testng.annotations.*;

import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.JxpBuilder;
import net.robinfriedli.jxp.api.XmlAttribute;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Continent;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;

public class CopyContextTest extends AbstractTest {

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
    public void testCopyAndMutateFullCountryFile() {
        Context sourceContext = jxp.getContext("src/test/resources/fullcountries-raw.xml");
        Context context = sourceContext.copy();
        List<Country> countries = context.getInstancesOf(Country.class);
        context.invoke(() -> {
            Map<String, Continent> continentMap = new HashMap<>();
            for (Country country : countries) {
                // add "name" attribute and set it the value of the text content, then drop the text content
                country.setAttribute("name", country.getTextContent());
                country.setTextContent("");

                // create or get the continent element matching the continent attribute then add the country as its sub element
                XmlAttribute continentAttr = country.getAttribute("continent");
                Continent continent = getOrCreateContinent(continentMap, continentAttr.getValue(), context);
                continentAttr.remove();
                country.delete();
                continent.addSubElement(country);
            }
        });

        context.persist("src/test/resources/output/fullcountries-dest-" + System.currentTimeMillis() + ".xml");
    }

    private Continent getOrCreateContinent(Map<String, Continent> continentMap, String name, Context context) {
        Continent continent = continentMap.get(name);

        if (continent != null) {
            return continent;
        } else {
            Continent newContinent = new Continent(name);
            continentMap.put(name, newContinent);
            newContinent.persist(context);
            return newContinent;
        }
    }

}
