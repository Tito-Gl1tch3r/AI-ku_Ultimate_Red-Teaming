package net.robinfriedli.jxp.persist;

import java.io.File;

import org.slf4j.Logger;

import net.robinfriedli.jxp.api.JxpBackend;
import org.w3c.dom.Document;

public class BindableCachedContext<E> extends CachedContext implements Context.BindableContext<E> {

    private final E boundObject;


    public BindableCachedContext(JxpBackend backend, Document document, E boundObject, Logger logger) {
        super(backend, document, logger);
        this.boundObject = boundObject;
    }

    public BindableCachedContext(JxpBackend backend, File file, E boundObject, Logger logger) {
        super(backend, file, logger);
        this.boundObject = boundObject;
    }

    @Override
    public E getBindingObject() {
        return boundObject;
    }
}
