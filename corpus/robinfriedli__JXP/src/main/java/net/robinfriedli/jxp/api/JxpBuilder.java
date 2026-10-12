package net.robinfriedli.jxp.api;

import java.io.File;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.Vector;

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import net.robinfriedli.jxp.events.JxpEventListener;
import org.w3c.dom.Document;

public class JxpBuilder {

    private final List<JxpEventListener> listeners = Lists.newArrayList();
    private final Set<File> contextFiles = Sets.newHashSet();
    private final Set<Document> contextDocuments = Sets.newHashSet();
    private JxpBackend.DefaultContextType defaultContextType = JxpBackend.DefaultContextType.CACHED;

    public JxpBuilder addListeners(JxpEventListener... listeners) {
        this.listeners.addAll(Arrays.asList(listeners));
        return this;
    }

    public JxpBuilder addListeners(Collection<JxpEventListener> listeners) {
        this.listeners.addAll(listeners);
        return this;
    }

    public JxpBuilder mapClass(String tagName, Class<? extends XmlElement> classToInstantiate) {
        StaticXmlElementFactory.mapClass(tagName, classToInstantiate);
        return this;
    }

    public JxpBuilder createContext(String xmlPath) {
        contextFiles.add(new File(xmlPath));
        return this;
    }

    public JxpBuilder createContext(File file) {
        contextFiles.add(file);
        return this;
    }

    public JxpBuilder createContext(Document document) {
        contextDocuments.add(document);
        return this;
    }

    public JxpBuilder setDefaultContextType(JxpBackend.DefaultContextType contextType) {
        defaultContextType = contextType;
        return this;
    }

    public JxpBackend build() {
        JxpBackend jxpBackend = new JxpBackend(new Vector<>(listeners), defaultContextType);
        contextFiles.forEach(jxpBackend::getContext);
        contextDocuments.forEach(jxpBackend::getContext);

        return jxpBackend;
    }

}
