package net.robinfriedli.jxp.api;

import java.util.List;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.testng.annotations.*;

import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.entities.TestElem;
import net.robinfriedli.jxp.persist.Context;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import static org.testng.Assert.*;

public class ContextCreationTest extends AbstractTest {

    @Test // creating a context from a file or inputstream is already thoroughly covered by other tests
    public void testCreateContextFromDomDocument() throws ParserConfigurationException {
        Document document = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument();
        Element rootElem = document.createElement("tests");
        rootElem.setAttribute("xmlns", "testSpace");
        document.appendChild(rootElem);

        Context context = jxp.getContext(document);

        TestElem test1 = new TestElem("test1", "test");
        TestElem test11 = new TestElem("test11", "test");
        TestElem test12 = new TestElem("test12", "test");
        TestElem test111 = new TestElem("test111", "test");
        TestElem test112 = new TestElem("test112", "test");
        TestElem test113 = new TestElem("test113", "test");
        TestElem test121 = new TestElem("test121", "test");
        TestElem test122 = new TestElem("test122", "test");
        TestElem test123 = new TestElem("test123", "test");
        TestElem test2 = new TestElem("test2", "test");
        TestElem test21 = new TestElem("test21", "test");
        TestElem test22 = new TestElem("test22", "test");
        TestElem test211 = new TestElem("test211", "test");
        TestElem test212 = new TestElem("test212", "test");
        TestElem test213 = new TestElem("test213", "test");
        TestElem test221 = new TestElem("test221", "test");
        TestElem test222 = new TestElem("test222", "test");
        TestElem test223 = new TestElem("test223", "test");

        context.invoke(() -> {
            test1.addSubElements(test11, test12);
            test11.addSubElements(test111, test112, test113);
            test12.addSubElements(test121, test122, test123);
            test2.addSubElements(test21, test22);
            test21.addSubElements(test211, test212, test213);
            test22.addSubElements(test221, test222, test223);

            test1.persist(context);
            test2.persist(context);
        });

        context.persist("src/test/resources/output/testRecursive" + System.currentTimeMillis() + ".xml");

        context.invoke(() -> {
            test1.delete();
            test2.delete();
        });

        context.invoke(() -> {
            test1.persist(context);
            test1.addSubElements(test11, test12);
            test11.addSubElements(test111, test112, test113);
            test12.addSubElements(test121, test122, test123);

            test2.persist(context);
            test2.addSubElements(test21, test22);
            test21.addSubElements(test211, test212, test213);
            test22.addSubElements(test221, test222, test223);
        });

        List<XmlElement> elements = context.getElements();
        List<XmlElement> elementsRecursive = context.getElementsRecursive();
        assertEquals(elements.size(), 2);
        assertEquals(elementsRecursive.size(), 18);

        List<XmlElement> subElements = test1.getSubElements();
        List<XmlElement> subElementsRecursive = test1.getSubElementsRecursive();
        assertEquals(subElements.size(), 2);
        assertEquals(subElementsRecursive.size(), 8);

        assertEquals(test122.getParent(), test12);
        assertTrue(test22.getSubElements().contains(test222));
    }

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder().build();
    }
}
