package net.robinfriedli.jxp.api;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Vector;
import java.util.function.Consumer;
import java.util.stream.Collectors;

import javax.annotation.Nullable;

import org.slf4j.Logger;

import com.google.common.collect.Lists;
import net.robinfriedli.exec.MutexSync;
import net.robinfriedli.jxp.events.ElementChangingEvent;
import net.robinfriedli.jxp.events.ElementCreatedEvent;
import net.robinfriedli.jxp.events.ElementDeletingEvent;
import net.robinfriedli.jxp.events.JxpEventListener;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.logging.LoggerSupplier;
import net.robinfriedli.jxp.persist.BindableCachedContext;
import net.robinfriedli.jxp.persist.BindableLazyContext;
import net.robinfriedli.jxp.persist.CachedContext;
import net.robinfriedli.jxp.persist.Context;
import net.robinfriedli.jxp.persist.LazyContext;
import net.robinfriedli.jxp.persist.StaticXmlParser;
import net.robinfriedli.jxp.persist.Transaction;
import org.w3c.dom.Document;

public class JxpBackend {

    private static final MutexSync<String> MUTEX_SYNC = new MutexSync<>();

    private final List<Context> contexts;
    private final List<Context.BindableContext<?>> boundContexts;
    private final Vector<JxpEventListener> listeners;
    private final Logger logger;
    private final DefaultContextType defaultContextType;
    private final ThreadLocal<Boolean> listenersMuted = ThreadLocal.withInitial(() -> false);

    public JxpBackend(Vector<JxpEventListener> listeners,
                      DefaultContextType defaultContextType) {
        this(Lists.newArrayList(), Lists.newArrayList(), listeners, defaultContextType);
    }

    public JxpBackend(List<Context> contexts,
                      List<Context.BindableContext<?>> boundContexts,
                      Vector<JxpEventListener> listeners,
                      DefaultContextType defaultContextType) {
        this.contexts = contexts;
        this.boundContexts = boundContexts;
        this.listeners = listeners;
        this.defaultContextType = defaultContextType;
        logger = LoggerSupplier.getLogger();
    }

    public List<Context> getContexts() {
        return contexts;
    }

    public List<Context.BindableContext<?>> getBoundContexts() {
        return boundContexts;
    }

    public Context getContext(String path) {
        return getContext(new File(path));
    }

    /**
     * @param file the XML file
     * @return either the existing Context for this file that is attached to this JxpBackend instance or a new Context
     * that will be attached to this JxpBackend
     */
    public Context getContext(File file) {
        String canonicalPath = getCanonicalPath(file);

        return MUTEX_SYNC.evaluate(canonicalPath, () -> {
            Context existingContext = getExistingContext(file);

            if (existingContext != null) {
                return existingContext;
            } else {
                Context context = defaultContextType.getContext(this, file, logger);
                contexts.add(context);
                return context;
            }
        });
    }

    /**
     * @param document the DOM document
     * @return either the existing Context for this document that is attached to this JxpBackend instance or a new
     * Context that will be attached to this JxpBackend
     */
    public Context getContext(Document document) {
        String mutexKey = String.valueOf(document.hashCode());

        return MUTEX_SYNC.evaluate(mutexKey, () -> {
            Context existingContext = getExistingContext(document);

            if (existingContext != null) {
                return existingContext;
            } else {
                Context context = defaultContextType.getContext(this, document, logger);
                contexts.add(context);
                return context;
            }
        });
    }

    @Nullable
    public Context getExistingContext(String path) {
        return getExistingContext(new File(path));
    }

    /**
     * Find an existing Context for the canonical path of the provided file. This method operates on a copy of the current
     * state of the contexts list.
     *
     * @param file the XML file
     * @return the existing Context for this XML file that is attached to this JxpBackend
     */
    @Nullable
    public Context getExistingContext(File file) {
        List<Context> found = Lists.newArrayList(contexts)
            .stream()
            .filter(c -> {
                try {
                    return c.getFile() != null && c.getFile().getCanonicalPath().equals(file.getCanonicalPath());
                } catch (IOException e) {
                    throw new PersistException("could not get canonical path for file", e);
                }
            })
            .collect(Collectors.toList());

        if (found.size() == 1) {
            return found.get(0);
        } else if (found.size() > 1) {
            throw new IllegalStateException("More than one Context for file " + file);
        }

        return null;
    }

    /**
     * Find an existing Context for the provided Document instance. This method operates on a copy of the current state
     * of the contexts list.
     *
     * @param document the DOM document
     * @return the existing Context for this document that is attached to this JxpBackend
     */
    @Nullable
    public Context getExistingContext(Document document) {
        List<Context> found = Lists.newArrayList(contexts).stream().filter(c -> c.getDocument().equals(document)).collect(Collectors.toList());

        if (found.size() == 1) {
            return found.get(0);
        } else if (found.size() > 1) {
            throw new IllegalStateException("More than one Context for document " + document);
        }

        return null;
    }

    public Context requireExistingContext(String path) {
        return requireExistingContext(new File(path));
    }

    public Context requireExistingContext(File file) {
        Context context = getExistingContext(file);

        if (context != null) {
            return context;
        } else {
            throw new IllegalStateException("No Context for file " + file);
        }
    }

    public Context requireExistingContext(Document document) {
        Context context = getExistingContext(document);

        if (context != null) {
            return context;
        } else {
            throw new IllegalStateException("No Context for document " + document);
        }
    }

    public boolean hasContext(String path) {
        return hasContext(new File(path));
    }

    /**
     * @param file the XML file
     * @return true if this JxpBackend has an attached Context for this XML file
     */
    public boolean hasContext(File file) {
        return Lists.newArrayList(contexts).stream().anyMatch(c -> {
            try {
                return c.getFile() != null && c.getFile().getCanonicalPath().equals(file.getCanonicalPath());
            } catch (IOException e) {
                throw new PersistException(e);
            }
        });
    }

    /**
     * @param document the DOM document
     * @return true if this JxpBackend has an attached Context for this DOM document
     */
    public boolean hasContext(Document document) {
        return Lists.newArrayList(contexts).stream().anyMatch(c -> c.getDocument().equals(document));
    }

    /**
     * @param boundObject the mapped object
     * @return true if this JxpBackend has a Context mapped to this object
     */
    public boolean hasBoundContext(Object boundObject) {
        return Lists.newArrayList(boundContexts).stream().anyMatch(ctx -> ctx.getBindingObject().equals(boundObject));
    }

    public <E> Context.BindableContext<E> requireBoundContext(E boundObject) {
        Context.BindableContext<E> boundContext = getBoundContext(boundObject);

        if (boundContext != null) {
            return boundContext;
        } else {
            throw new IllegalStateException("No Context bound to object equal to " + boundObject);
        }
    }

    /**
     * @param boundObject the mapped object
     * @param <E>         the type of the object
     * @return the Context mapped to the provided object
     */
    @SuppressWarnings("unchecked")
    @Nullable
    public <E> Context.BindableContext<E> getBoundContext(E boundObject) {
        List<Context.BindableContext> found = Lists.newArrayList(boundContexts)
            .stream()
            .filter(c -> c.getBindingObject().equals(boundObject))
            .collect(Collectors.toList());

        if (found.size() == 1) {
            // cast is safe since the type parameter is the class of the object the context is bound to
            return found.get(0);
        } else if (found.size() > 1) {
            throw new IllegalStateException("More than one Context bound to object equal to " + boundObject);
        }

        return null;
    }

    public CachedContext createCachedContext(String path) {
        return createCachedContext(new File(path));
    }

    /**
     * Create a new CachedContext without attaching it to this JxpBackend.
     *
     * @param file the file to create a context for
     * @return the created cached context
     */
    public CachedContext createCachedContext(File file) {
        return new CachedContext(this, file, logger);
    }

    /**
     * Create a new CachedContext without attaching it to this JxpBackend.
     *
     * @param document the document to create a context for
     * @return the created cached context
     */
    public CachedContext createCachedContext(Document document) {
        return new CachedContext(this, document, logger);
    }

    /**
     * Create a new CachedContext without attaching it to this JxpBackend. This implementation constructs a {@link Document} for the provided {@link InputStream}
     * and then calls {@link #createCachedContext(Document)}. This is useful as a shorthand for classpath resources.
     *
     * @param inputStream the InputStream to create a context for
     * @return the created cached context
     */
    public CachedContext createCachedContext(InputStream inputStream) {
        return createCachedContext(StaticXmlParser.parseDocument(inputStream));
    }

    public LazyContext createLazyContext(String path) {
        return createLazyContext(new File(path));
    }

    /**
     * Create a new LazyContext without attaching it to this JxpBackend.
     *
     * @param file the file to create a context for
     * @return the created lazy context
     */
    public LazyContext createLazyContext(File file) {
        return new LazyContext(this, file, logger);
    }

    /**
     * Create a new LazyContext without attaching it to this JxpBackend.
     *
     * @param document the document to create a context for
     * @return the created lazy context
     */
    public LazyContext createLazyContext(Document document) {
        return new LazyContext(this, document, logger);
    }

    /**
     * Create a new LazyContext without attaching it to this JxpBackend. This implementation constructs a {@link Document} for the provided {@link InputStream}
     * and then calls {@link #createCachedContext(Document)}. This is useful as a shorthand for classpath resources.
     *
     * @param inputStream the InputStream to create a context for
     * @return the created cached context
     */
    public LazyContext createLazyContext(InputStream inputStream) {
        return createLazyContext(StaticXmlParser.parseDocument(inputStream));
    }

    public Context createContext(String path) {
        return createContext(new File(path));
    }

    public Context createContext(File file) {
        return defaultContextType.getContext(this, file, logger);
    }

    public Context createContext(Document document) {
        return defaultContextType.getContext(this, document, logger);
    }

    public Context createContext(InputStream inputStream) {
        return createContext(StaticXmlParser.parseDocument(inputStream));
    }

    public <E> Context.BindableContext<E> createBoundCachedContext(String path, E objectToBind) {
        return createBoundCachedContext(new File(path), objectToBind);
    }

    /**
     * Create a {@link CachedContext} that is "bound" to the provided object. Meaning, once added to the JxpBackend, it
     * can be retrieved via {@link #getBoundContext(Object)} with any Object that matches the bound object according to
     * {@link Object#equals(Object)}.
     *
     * @param file         the persistent file to create the Context for
     * @param objectToBind the object to bind
     * @param <E>          the type of the object
     * @return the created BindableContext (not attached to this JxpBackend yet)
     */
    public <E> Context.BindableContext<E> createBoundCachedContext(File file, E objectToBind) {
        return new BindableCachedContext<>(this, file, objectToBind, logger);
    }

    /**
     * Create a {@link CachedContext} that is "bound" to the provided object. Meaning, once added to the JxpBackend, it
     * can be retrieved via {@link #getBoundContext(Object)} with any Object that matches the bound object according to
     * {@link Object#equals(Object)}.
     *
     * @param document     the dom document to create the Context for
     * @param objectToBind the object to bind
     * @param <E>          the type of the object
     * @return the created BindableContext (not attached to this JxpBackend yet)
     */
    public <E> Context.BindableContext<E> createBoundCachedContext(Document document, E objectToBind) {
        return new BindableCachedContext<>(this, document, objectToBind, logger);
    }

    public <E> Context.BindableContext<E> createBoundCachedContext(InputStream inputStream, E objectToBind) {
        return createBoundCachedContext(StaticXmlParser.parseDocument(inputStream), objectToBind);
    }

    public <E> Context.BindableContext<E> createBoundLazyContext(String path, E objectToBind) {
        return createBoundLazyContext(new File(path), objectToBind);
    }

    /**
     * Create a {@link LazyContext} that is "bound" to the provided object. Meaning, once added to the JxpBackend, it
     * can be retrieved via {@link #getBoundContext(Object)} with any Object that matches the bound object according to
     * {@link Object#equals(Object)}.
     *
     * @param file         the persistent file to create the Context for
     * @param objectToBind the object to bind
     * @param <E>          the type of the object
     * @return the created BindableContext (not attached to this JxpBackend yet)
     */
    public <E> Context.BindableContext<E> createBoundLazyContext(File file, E objectToBind) {
        return new BindableLazyContext<>(this, file, objectToBind, logger);
    }

    /**
     * Create a {@link LazyContext} that is "bound" to the provided object. Meaning, once added to the JxpBackend, it
     * can be retrieved via {@link #getBoundContext(Object)} with any Object that matches the bound object according to
     * {@link Object#equals(Object)}.
     *
     * @param document     the dom document to create the Context for
     * @param objectToBind the object to bind
     * @param <E>          the type of the object
     * @return the created BindableContext (not attached to this JxpBackend yet)
     */
    public <E> Context.BindableContext<E> createBoundLazyContext(Document document, E objectToBind) {
        return new BindableLazyContext<>(this, document, objectToBind, logger);
    }

    public <E> Context.BindableContext<E> createBoundLazyContext(InputStream inputStream, E objectToBind) {
        return createBoundLazyContext(StaticXmlParser.parseDocument(inputStream), objectToBind);
    }

    public <E> Context.BindableContext<E> createBoundContext(String path, E objectToBind) {
        return createBoundContext(new File(path), objectToBind);
    }

    public <E> Context.BindableContext<E> createBoundContext(Document document, E objectToBind) {
        return defaultContextType.getBindableContext(this, document, objectToBind, logger);
    }

    public <E> Context.BindableContext<E> createBoundContext(InputStream inputStream, E objectToBind) {
        return createBoundContext(StaticXmlParser.parseDocument(inputStream), objectToBind);
    }

    /**
     * Create a new BoundContext without attaching it to this JxpBackend.
     *
     * @param file the file to create a context for
     * @return the created bound context
     */
    public <E> Context.BindableContext<E> createBoundContext(File file, E objectToBind) {
        return defaultContextType.getBindableContext(this, file, objectToBind, logger);
    }

    /**
     * Attach a Context that was create using one of the createContext methods or manually to this JxpBackend, ensuring
     * only one context exists for the same file / document and enabling it being returned by the getContext method
     *
     * @param context the context to attach
     */
    @SuppressWarnings("rawtypes")
    public void attachContext(Context context) {
        if (context instanceof Context.BindableContext) {
            attachContext((Context.BindableContext) context);
        } else {
            if (context.isPersistent() && hasContext(context.getFile())) {
                throw new PersistException("There already is a Context for file " + context.getFile());
            } else if (hasContext(context.getDocument())) {
                throw new PersistException("There already is a Context for document " + context.getDocument());
            }

            contexts.add(context);
        }
    }

    @SuppressWarnings("rawtypes")
    public void attachContext(Context.BindableContext context) {
        if (hasBoundContext(context.getBindingObject())) {
            throw new PersistException("There already is a Context bound to object equal to " + context.getBindingObject());
        }

        if (context.isPersistent() && hasContext(context.getFile())) {
            throw new PersistException("There already is a Context for file " + context.getFile());
        } else if (hasContext(context.getDocument())) {
            throw new PersistException("There already is a Context for document " + context.getDocument());
        }

        boundContexts.add(context);
    }

    public void removeContext(String path) {
        Context context = requireExistingContext(path);
        contexts.remove(context);
    }

    public void removeContext(Document document) {
        Context context = requireExistingContext(document);
        contexts.remove(context);
    }

    public void removeContext(File file) {
        Context context = requireExistingContext(file);
        contexts.remove(context);
    }

    public void removeContext(Context context) {
        if (context instanceof Context.BindableContext) {
            boundContexts.remove(context);
        } else {
            contexts.remove(context);
        }
    }

    public void removeContext(Context.BindableContext context) {
        boundContexts.remove(context);
    }

    /**
     * Clear all "regular" unbound contexts
     */
    public void clearContexts() {
        contexts.clear();
    }

    /**
     * Clear all bound contexts
     */
    public void clearBoundContexts() {
        boundContexts.clear();
    }

    /**
     * Clear all contexts attached to this JxpBackend, bound and unbound.
     */
    public void clearAllContexts() {
        clearContexts();
        clearBoundContexts();
    }

    public <E> void removeBoundContext(E boundObject) {
        Context.BindableContext<E> context = requireBoundContext(boundObject);
        boundContexts.remove(context);
    }

    public void addListener(JxpEventListener listener) {
        listeners.add(listener);
    }

    public void removeListener(JxpEventListener listener) {
        listeners.remove(listener);
    }

    public boolean isListenersMuted() {
        return listenersMuted.get();
    }

    public void setListenersMuted(boolean listenersMuted) {
        this.listenersMuted.set(listenersMuted);
    }

    public void fireElementCreating(ElementCreatedEvent event) {
        listeners.forEach(emit(listener -> listener.elementCreating(event)));
    }

    public void fireElementDeleting(ElementDeletingEvent event) {
        listeners.forEach(emit(listener -> listener.elementDeleting(event)));
    }

    public void fireElementChanging(ElementChangingEvent event) {
        listeners.forEach(emit(listener -> listener.elementChanging(event)));
    }

    public void fireTransactionApplied(Transaction transaction) {
        listeners.forEach(emit(listener -> listener.transactionApplied(transaction)));
    }

    public void fireTransactionCommitted(Transaction transaction) {
        listeners.forEach(emit(listener -> listener.transactionCommitted(transaction)));
    }

    public void fireOnBeforeFlush(Transaction transaction) {
        listeners.forEach(emit(listener -> listener.onBeforeFlush(transaction)));
    }

    public Logger getLogger() {
        return logger;
    }

    private Consumer<JxpEventListener> emit(Consumer<JxpEventListener> consumer) {
        return listener -> {
            if (!listenersMuted.get()) {
                try {
                    consumer.accept(listener);
                } catch (Exception e) {
                    if (listener.mayInterrupt()) {
                        throw e;
                    } else {
                        logger.error("One of the EventListeners had an uncaught exception", e);
                    }
                }
            }
        };
    }

    private String getCanonicalPath(File file) {
        String canonicalPath;
        try {
            canonicalPath = file.getCanonicalPath();
        } catch (IOException e) {
            throw new PersistException("Could not get canonical path of file", e);
        }

        return canonicalPath;
    }

    public enum DefaultContextType {

        CACHED() {
            @Override
            public Context getContext(JxpBackend jxpBackend, File file, Logger logger) {
                return new CachedContext(jxpBackend, file, logger);
            }

            @Override
            public Context getContext(JxpBackend jxpBackend, Document document, Logger logger) {
                return new CachedContext(jxpBackend, document, logger);
            }

            @Override
            public <E> Context.BindableContext<E> getBindableContext(JxpBackend jxpBackend, File file, E bindingObject, Logger logger) {
                return new BindableCachedContext<>(jxpBackend, file, bindingObject, logger);
            }

            @Override
            public <E> Context.BindableContext<E> getBindableContext(JxpBackend jxpBackend, Document document, E bindingObject, Logger logger) {
                return new BindableCachedContext<>(jxpBackend, document, bindingObject, logger);
            }
        },

        LAZY() {
            @Override
            public Context getContext(JxpBackend jxpBackend, File file, Logger logger) {
                return new LazyContext(jxpBackend, file, logger);
            }

            @Override
            public Context getContext(JxpBackend jxpBackend, Document document, Logger logger) {
                return new LazyContext(jxpBackend, document, logger);
            }

            @Override
            public <E> Context.BindableContext<E> getBindableContext(JxpBackend jxpBackend, File file, E bindingObject, Logger logger) {
                return new BindableLazyContext<>(jxpBackend, file, bindingObject, logger);
            }

            @Override
            public <E> Context.BindableContext<E> getBindableContext(JxpBackend jxpBackend, Document document, E bindingObject, Logger logger) {
                return new BindableLazyContext<>(jxpBackend, document, bindingObject, logger);
            }
        };

        public abstract Context getContext(JxpBackend jxpBackend, File file, Logger logger);

        public abstract Context getContext(JxpBackend jxpBackend, Document document, Logger logger);

        public abstract <E> Context.BindableContext<E> getBindableContext(JxpBackend jxpBackend, File file, E bindingObject, Logger logger);

        public abstract <E> Context.BindableContext<E> getBindableContext(JxpBackend jxpBackend, Document document, E bindingObject, Logger logger);

    }
}
