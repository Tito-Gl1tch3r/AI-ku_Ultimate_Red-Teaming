package net.robinfriedli.jxp.persist;

import java.io.File;
import java.util.List;
import java.util.stream.Collectors;

import org.slf4j.Logger;

import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.StaticXmlElementFactory;
import net.robinfriedli.jxp.api.XmlElement;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

/**
 * Context implementation that stores all {@link XmlElement} instances for the entirety of its lifespan and never has
 * to re-instantiate its XmlElements or re-parse its DOM document. This is ideal when performance is the main focus
 * and memory is not too limited.
 */
public class CachedContext extends AbstractContext {

    private XmlElement rootElement;

    public CachedContext(JxpBackend backend, Document document, Logger logger) {
        super(backend, document, logger);
        rootElement = StaticXmlElementFactory.instantiateDocumentElement(this);
    }

    public CachedContext(JxpBackend backend, File file, Logger logger) {
        super(backend, file, logger);
        rootElement = StaticXmlElementFactory.instantiateDocumentElement(this);
    }

    @Override
    public void reload() {
        super.reload();
        rootElement = StaticXmlElementFactory.instantiateDocumentElement(this);
    }

    @Override
    public XmlElement getDocumentElement() {
        return rootElement;
    }

    @Override
    public List<XmlElement> getElements() {
        return rootElement.getSubElements();
    }

    @Override
    protected List<XmlElement> handleXPathResults(List<Element> results) {
        return getElementsRecursive().stream().filter(element -> element.isPersisted() && results.contains(element.getElement())).collect(Collectors.toList());
    }

    @Override
    protected Context instantiate(JxpBackend jxpBackend, Document document, Logger logger) {
        return new CachedContext(jxpBackend, document, logger);
    }

    @Override
    protected Context instantiate(JxpBackend jxpBackend, File document, Logger logger) {
        return new CachedContext(jxpBackend, document, logger);
    }

}