package net.robinfriedli.jxp.persist;

import java.io.File;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.function.Predicate;

import javax.annotation.Nullable;

import net.robinfriedli.exec.Mode;
import net.robinfriedli.exec.MutexSync;
import net.robinfriedli.exec.modes.MutexSyncMode;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.Node;
import net.robinfriedli.jxp.api.StaticXmlElementFactory;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.exec.AbstractTransactionalMode;
import net.robinfriedli.jxp.exec.QueuedTask;
import net.robinfriedli.jxp.queries.Conditions;
import net.robinfriedli.jxp.queries.Query;
import net.robinfriedli.jxp.queries.QueryResult;
import net.robinfriedli.jxp.queries.ResultStream;
import net.robinfriedli.jxp.queries.xpath.XQueryBuilder;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

/**
 * Interface for classes that represent and manage an XML file and provide access to its {@link XmlElement} instances.
 * The {@link #invoke(Runnable)} methods enable an easy way to run a write transaction that may make changes to the
 * XML file.
 */
public interface Context extends AutoCloseable {

    MutexSync<String> GLOBAL_CONTEXT_SYNC = new MutexSync<>();

    /**
     * AutoCloseable#close override that does not throw an exception since this implementation never does so no
     * catch block is required
     */
    @Override
    void close();

    /**
     * @return the {@link JxpBackend} instance that created this Context
     */
    JxpBackend getBackend();

    /**
     * @return the {@link Document dom Document} represented by this Context. Changes made to this document are not
     * reflected by JXP.
     */
    Document getDocument();

    /**
     * @return the XML file this Context is persisted to.
     */
    @Nullable
    File getFile();

    /**
     * @return true if this Context is persisted to a file. This also requires the persistent target to be writable, so
     * this returns false for a Context created from an InputStream
     */
    boolean isPersistent();

    /**
     * Delete this Context's XML file
     *
     * @throws IllegalStateException if this Context is not persisted to a file or it's file does not exist.
     * @throws PersistException      if deleting the file fails
     */
    void deleteFile();

    /**
     * Persist this context to an XML file, if based on a {@link Document} instance.
     *
     * @param path the path to save the Context to.
     * @throws PersistException         if persisting to the file fails
     * @throws IllegalStateException    if this context already is persistent
     * @throws IllegalArgumentException if the path is invalid or points to an already existing file
     */
    void persist(String path);

    /**
     * Creates a new Context based on the DOM document of this context. Instantiates a new document and creates a deep
     * copy of the root element of this document. The resulting Context is not yet stored to a file.
     *
     * @return the newly create Context
     * @throws PersistException if an exception occurs while copying the DOM document
     */
    Context copy();

    /**
     * Copies this Context to create a new BoundContext. Depending on whether this is a {@link CachedContext} or
     * {@link LazyContext} this creates a {@link BindableCachedContext} or {@link BindableLazyContext}.
     *
     * @param objectToBind the object to bind the new Context to
     * @return the newly created BindableContext
     * @throws PersistException if an exception occurs while copying the DOM document
     */
    <E> BindableContext<E> copy(E objectToBind);

    /**
     * Reloads the elements stored in this Context. This means all current XmlElement instances will be cleared and
     * phantomized and re-instantiated based on the current state of the physical Document and the dom document will be
     * re-parsed. In case of a LazyContext this only does the second part. This action in only possible for persistent
     * contexts. This renders all {@link XmlElement} instances previously associated with this context pointless as
     * the DOM elements they are backed by belong to the old document.
     *
     * @throws UnsupportedOperationException if this context is not persistent
     */
    void reload();

    /**
     * @return the path of the XML file of this Context or null if not persistent
     */
    String getPath();

    /**
     * @return the tag name of the root element this Context represents
     */
    String getRootTag();

    /**
     * Returns the {@link XmlElement} instance representing the root element in the document, see {@link Document#getDocumentElement()}.
     * <p>
     * In case of a {@link LazyContext} this does not initialize the document element's children until they are queried
     * (or the list containing the children is accessed in any way). The same thing applies to all child elements, all
     * of their children are only initialized once queried. Furthermore this guarantees that each element is only instantiated
     * once, so, for instance, when calling {@link XmlElement#getSubElementsRecursive()} on this element the first time
     * all XmlElements are instantiated and each subsequent call to that method returns the same instances, which makes
     * the element returned by this method a great fit for temporarily storing and managing all XmlElement instances when
     * working with a {@link LazyContext}.
     *
     * @return the {@link XmlElement} representation of the document element
     */
    XmlElement getDocumentElement();

    /**
     * @return an immutable collection of all XmlElements in this Context. In case of a {@link LazyContext} this
     * causes all elements to be instantiated. This includes all XmlElements that were created in the current transaction
     * and excludes all XmlElements that were deleted in the current transaction, if the respective event has already been
     * applied; in case of an {@link InstantApplyTx} (which is default) this is the case immediately when adding the event
     * to the transaction, thus immediately when performing the action, else this happens when applying the transaction
     * before commit at the end of the task.
     * <p>
     * In case of a {@link CachedContext} this simply returns an Immutable wrapper around the internal XmlElement storage
     * (via {@link Collections#unmodifiableList(List)}).
     * For a {@link LazyContext} this operation is more complex and much more expensive, which is why you should limit
     * the usage of this method (or any method that calls this method, such as {@link #getElementsRecursive()},
     * any of the {@link #getElement(String, Class)} methods or {@link #query(Predicate)}) as much as possible and store
     * the output somewhere locally when used more than once (e.g. when executing more than one query). In case of a
     * {@link LazyContext} this gathers all {@link XmlElement} instances from the current transaction and all uncommitted
     * transactions (see {@link #getUncommittedTransactions()}) by collecting all events and taking the source XmlElement
     * of those events that have been applied, finding the root (top level, meaning right below the document element)
     * parent for all those XmlElements and adding all new root elements / removing all deleted root elements to make sure
     * the output matches the current state and then instantiating the remaining XmlElements by calling
     * {@link StaticXmlElementFactory#instantiatePersistentXmlElement(Element, Context, Set)} while providing
     * the XmlElement instances it has already collected.
     */
    List<XmlElement> getElements();

    /**
     * @return an immutable collection of all elements in this Context. Unlike {@link #getElements()} this flattens the
     * elements to return a list that contains all sub elements directly.
     */
    List<XmlElement> getElementsRecursive();

    /**
     * @return all XmlElements (including their sub elements) in this Context that match {@param predicate}
     */
    List<XmlElement> getElements(Predicate<XmlElement> predicate);

    /**
     * @return all Ids that are used by XmlElements in this Context
     */
    Set<String> getUsedIds();

    /**
     * Return an {@link XmlElement} saved in this Context where {@link XmlElement#getId()} matches the provided id
     *
     * @param id to find the {@link XmlElement} with
     * @return found {@link XmlElement}
     */
    @Nullable
    XmlElement getElement(String id);

    /**
     * Return an {@link XmlElement} saved in this Context where {@link XmlElement#getId()} matches the provided id and
     * is an instance of the provided class.
     *
     * @param id   to find the {@link XmlElement} with
     * @param type target Class
     * @param <E>  Class extending {@link XmlElement}
     * @return found {@link XmlElement} cast to target Class
     */
    @Nullable
    <E extends XmlElement> E getElement(String id, Class<E> type);

    /**
     * Same as {@link #getElement(String)} but throws Exception when null
     *
     * @param id to find the {@link XmlElement} with
     * @return found {@link XmlElement}
     */
    XmlElement requireElement(String id) throws IllegalStateException;

    /**
     * same as {@link #requireElement(String)} but checks if the element matches the passed type and casts it to it
     */
    <E extends XmlElement> E requireElement(String id, Class<E> type) throws IllegalStateException;

    /**
     * Get all XmlElements saved in this Context that are instance of {@link E}
     *
     * @param c   Class to check
     * @param <E> Type of Class to check
     * @return All Elements that are an instance of specified Class
     */
    <E extends XmlElement> List<E> getInstancesOf(Class<E> c);

    /**
     * Get all XmlElements saved in this Context that are instance of {@link E}, ignoring elements that are instance of
     * any of the ignored subClasses. Used to exclude subclasses.
     *
     * @param c                 Class to check
     * @param ignoredSubClasses subclasses to exclude
     * @param <E>               Type to return
     * @return All Elements that are an instance of specified Class but not specified subclasses
     */
    <E extends XmlElement> List<E> getInstancesOf(Class<E> c, Class... ignoredSubClasses);

    /**
     * Checks all XmlElements for provided {@link Predicate}s and returns {@link QueryResult} with matching elements.
     * See {@link Conditions} for useful predicates. The performance of this method strongly depends on the performance
     * of {@link #getElements()} for this Context implementation. For a {@link LazyContext} you should generally use an
     * {@link #xPathQuery(String)} instead (see {@link XQueryBuilder}) as it only instantiates the XmlElements that were
     * found, else you should make sure to use {@link Query#evaluate(Predicate)} directly instead of calling this method
     * several times; e.g. for a {@link LazyContext} it's important that you do
     * <pre>{@code
     * List<XmlElement> elements = context.getElementsRecursive();
     * List<XmlElement> result1 = Query.evaluate(attribute("name").is("value")).execute(elements).collect();
     * List<XmlElement> result2 = Query.evaluate(attribute("name2").is("value2")).execute(elements).collect();
     * }</pre>
     * <p>
     * instead of
     *
     * <pre>{@code
     * List<XmlElement> result1 = context.query(attribute("name").is("value")).collect();
     * List<XmlElement> result2 = context.query(attribute("name2").is("value2")).collect();
     * }</pre>
     * <p>
     * because the {@link #getElements()} operation is expensive for {@link LazyContext} instances.
     *
     * @param condition Predicate to filter elements with, see {@link Conditions}
     * @return a stream of found elements
     */
    ResultStream<XmlElement> query(Predicate<XmlElement> condition);

    /**
     * Like {@link #query(Predicate)} but casts the found elements to the given class, make sure all results are instances
     * of the provided class by using the {@link Conditions#instanceOf(Class)} check.
     */
    <E extends XmlElement> ResultStream<E> query(Predicate<XmlElement> condition, Class<E> type);

    /**
     * Executes the provided XPath query and returns the {@link XmlElement}s in this Context that are based on the
     * resulting DOM elements or, if this is a {@link LazyContext}, instantiates {@link XmlElement}s based on the results, making it
     * a neat way to deal with a {@link LazyContext} that might contain many elements. However it is important to note
     * that these queries are based on the state of the DOM document, thus uncommitted changes are not yet available.
     * Also, in case of a {@link LazyContext} this always creates a new XmlElement instance for each result, leading to several
     * XmlElement instances for the same DOM element when executing several queries that return common results or when also
     * using {@link #getElements()}. This becomes a problem when modifying one of the duplicate XmlElements leading to
     * inconsistencies as the change will not be applied to the other XmlElement; when modifying both instances (thus
     * adding both to the transaction) {@link LazyContext#getElements()} might even throw an exception when encountering
     * a DOM element that is represented by two XmlElement instances.
     * While for a {@link CachedContext} this might return XmlElements instances where the current state might not match
     * a query condition anymore due to uncommitted changes.
     * For those reasons this method is best used outside of a transaction or at the start of one.
     * One good use case for this method might look like this:
     * <pre>{@code
     * LazyContext context = jxp.createLazyContext("large_file.xml");
     * List<XmlElement> relevantElements = context.xPathQuery(XQueryBuilder.find("country/city").where(XCondition.attribute("name").startsWith("A")).getXPath(context));
     * XmlElement atlanta = Query.evaluate(attribute("name").is("Atlanta")).execute(relevantElements).requireOnlyResult();
     * XmlElement athens = Query.evaluate(attribute("name").is("Athens")).execute(relevantElements).requireOnlyResult();
     * List<XmlElement> results = Query.evaluate(attribute("name").endsWith("z")).execute(relevantElements).collect();
     * context.invoke(() -> {
     *     atlanta.setAttribute("population", 500000);
     *     athens.setAttribute("population", 700000);
     *     for (XmlElement result : results) {
     *         result.delete();
     *     }
     * });
     * }</pre>
     *
     * @param xPathQuery the XPath query
     * @return XmlElements instances based on results
     */
    List<XmlElement> xPathQuery(String xPathQuery);

    /**
     * Commit all previously uncommitted {@link Transaction}s on this Context, i.e. all transactions of tasks that were
     * executed with commit = false that haven't been committed via commitAll() or reverted via revertAll() yet.
     * Atomicity is only guaranteed per transaction, not across all transactions; meaning if one transaction fails
     * it rolls back and the error message is logged but the remaining transactions are still going to be committed.
     */
    void commitAll();

    /**
     * remove and rollback all uncommitted {@link Transaction}s on this Context, i.e. all transactions of tasks that were
     * executed with commit = false that haven't been committed via commitAll() or reverted via revertAll() yet.
     */
    void revertAll();

    /**
     * @return true if field uncommittedTransactions is not empty
     */
    boolean hasUncommittedTransactions();

    /**
     * @return all saved uncommitted {@link Transaction} in this Context. This exposes the internal list to enable to only
     * commit / revert selected transactions, this case the implementor is responsible to remove those transactions from
     * the list
     */
    List<Transaction> getUncommittedTransactions();

    /**
     * Run a Callable in a {@link Transaction}. For any actions that create, change or delete an {@link XmlElement},
     * i.e anything that requires a transaction.
     * <p>
     * This is the core invoke implementation above {@link #invoke(Mode, Callable)} used for any invoke implementation
     * without a custom execution {@link Mode}. Calls {@link #invoke(Mode, Callable)} with a Mode that
     * combines {@link MutexSyncMode} and {@link AbstractTransactionalMode} to run a transaction that is synchronised
     * across all threads based on the canonical file path or {@link Document instance} managed by this context.
     * JXP does not support running several transactions targeting the same file / document concurrently.
     *
     * @param commit       defines if the transaction will be committed to XML file immediately after running or remain as
     *                     uncommitted transaction in the Context
     * @param instantApply defines whether the changes will be applied instantly or all at once after the task has run.
     *                     e.g. if false, this code would return the old value of "attribute", not "newValue"
     *                     <pre>{@code
     *                     return context.invoke(true, false, () -> {
     *                         someElement.setAttribute("attribute", "newValue");
     *                         return someElement.geAttribute("attribute").getValue();
     *                     })
     *                     }</pre>
     *                     however, disabling instantApply might slightly improve performance when dealing with a large number of changes.
     *                     If false the transaction will be added to this Context's uncommitted transactions that can be
     *                     committed or reverted using {@link #commitAll()} or {@link #revertAll()} respectively.
     *                     If you never intend to commit the changes use {@link #apply(boolean, Runnable)}.
     * @param task         any Callable
     * @param <E>          return type of Callable
     * @return the return value of the given Callable
     * <p>
     * Notice: when calling this method within an invoked task with different parameters, i.e. a different mode, the
     * context will switch to a new transaction an switch back after.
     */
    <E> E invoke(boolean commit, boolean instantApply, Callable<E> task);

    /**
     * Core invoke implementation that is called by each overloading method that runs the task in any given {@link Mode}
     *
     * @throws PersistException if a checked exception occurs
     */
    <E> E invoke(Mode mode, Callable<E> task);

    /**
     * same as {@link #invoke(boolean, boolean, Callable)} with commit = true and instantApply = true as default values
     */
    <E> E invoke(Callable<E> task);

    /**
     * Convenience overload for {@link #invoke(boolean, boolean, Callable)} that creates a Callable that executes the
     * given runnable. Used for any task where a return value is not required and no checked exception is thrown.
     * <p>
     * Useful for short transactions like:
     * {@code context.invoke(() -> bla.setAttribute("name", "value"));}
     * <p>
     * or tasks that do not return anything and do not throw a checked exception:
     * <pre>{@code
     * context.invoke(() -> {
     *    TestXmlElement elem = new TestXmlElement("test", context);
     *    elem.setAttribute("test", "test");
     *    elem.setTextContent("test");
     * });
     * }</pre>
     * <p>
     * A {@link Transaction} is required by any action that creates, changes or deletes an {@link XmlElement}
     *
     * @param commit       defines if the changes will be committed to the underlying DOM structure or are only applied to
     *                     the representative {@link XmlElement} or other {@link Node} instances. If false the transaction
     *                     will be added to this Context's uncommitted transactions that can be committed or reverted using
     *                     {@link #commitAll()} or {@link #revertAll()} respectively. If you never intend to commit the changes
     *                     use {@link #apply(boolean, Runnable)}.
     * @param instantApply controls whether the created transaction is a {@link InstantApplyTx} (which is default), else
     *                     changes are not applied to {@link Node} instances until the end of the transaction and thus
     *                     not visible until all changes are applied after the task has been executed
     * @param task         the task to run that contains actions that require a transaction
     */
    void invoke(boolean commit, boolean instantApply, Runnable task);

    /**
     * Like {@link #invoke(Mode, Callable)} but accepts a Runnable
     */
    void invoke(Mode mode, Runnable task);

    /**
     * same as {@link #invoke(boolean, boolean, Runnable)} with commit = true and instantApply = true as default values
     */
    void invoke(Runnable task);

    /**
     * Like {@link #invoke(boolean, boolean, Runnable)} but runs in a {@link SequentialTx}, meaning all changes will
     * get committed / flushed each time the amount of changes recorded by the transaction reaches the provided number
     */
    <E> E invokeSequential(int sequence, Callable<E> task);

    /**
     * Like {@link #invokeSequential(int, Callable)} but accepts a runnable instead of a callable
     */
    void invokeSequential(int sequence, Runnable task);

    /**
     * A {@link #invoke(boolean, boolean, Callable)} implementation that will be executed in the future. This is
     * applicable, although as of v1.2 no longer required, for tasks invoked after the Transaction has stopped recording
     * but before the Transaction has been committed and closed. When this happens depends on whether it is an
     * InstantApplyTx or not; if it is an InstantApplyTx the Transaction will keep recording and applying changes until
     * {@link Transaction.Internals#commit()} is called, if it is not it's until {@link Transaction.Internals#apply()} is called.
     * <p>
     * This is typically used in listeners (for InstantApplyTxs this is only required for the transaction committed
     * event) in which case the returned {@link QueuedTask} will be added to current Transaction and executed
     * after the Transaction is done. This method can also be used freely in which case the implementor decides when to
     * execute it.
     * <p>
     * If this is called within a transaction this task will added as a queued task to the transaction and run after
     * the transaction finished. Else the implementor needs to start the task manually.
     * <p>
     * This is commonly used to run a task after the current transaction has finished in the same thread, if you want to
     * run the task in a separate thread you should use {@link #futureInvoke(boolean, boolean, Mode, Callable)}
     * and apply the {@link MutexSyncMode} to enable synchronisation of the task.
     *
     * @param callable         the callable to call in the future
     * @param cancelOnFailure  if the task has been queued to a transaction cancel it when the transaction fails
     * @param triggerListeners trigger or mute listeners for the invoked task
     * @param enqueue          whether to enqueue this task to run after the current transaction (if available) in the same thread.
     * @param <E>              the type the callable returns
     * @return the {@link QueuedTask} that will be executed after the current Transaction is done automatically,
     * if called within Transaction (e.g EventListeners)
     */
    <E> QueuedTask<E> futureInvoke(boolean commit, boolean instantApply, boolean cancelOnFailure, boolean triggerListeners, boolean enqueue, Callable<E> callable);

    /**
     * Core {@link #futureInvoke(boolean, boolean, boolean, boolean, boolean, Callable)} implementation that allows to set
     * a custom mode. This should be used if the resulting QueuedTask is to be executed in a separated thread with the
     * {@link MutexSyncMode} applied (using the mutex returned by {@link #getMutexKey()}).
     *
     * @throws PersistException if enqueue is true but no active transaction exists in the current thread
     */
    <E> QueuedTask<E> futureInvoke(boolean cancelOnFailure, boolean enqueue, Mode mode, Callable<E> callable);

    /**
     * calls {@link #futureInvoke(boolean, boolean, boolean, boolean, boolean, Callable)} with default values commit = true,
     * instantApply = true, enqueue = true
     */
    <E> QueuedTask<E> futureInvoke(boolean cancelOnFailure, boolean triggerListeners, Callable<E> callable);

    /**
     * {@link #futureInvoke(boolean, boolean, boolean, boolean, boolean, Callable)} with default values commit = true,
     * instantApply = true, cancelOnFailure = true, triggerListeners = true, enqueue = true
     */
    <E> QueuedTask<E> futureInvoke(Callable<E> callable);

    /**
     * calls {@link #invoke(boolean, boolean, Callable)} and temporarily disables listeners
     */
    <E> E invokeWithoutListeners(boolean commit, boolean instantApply, Callable<E> callable);

    /**
     * {@link #invokeWithoutListeners(boolean, boolean, Callable)} with  default values commit = true
     * and instantApply = true
     */
    <E> E invokeWithoutListeners(Callable<E> callable);

    void invokeWithoutListeners(boolean commit, boolean instantApply, Runnable runnable);

    void invokeWithoutListeners(Runnable runnable);

    /**
     * Runs a task in an {@link ApplyOnlyTx} that will never be committed or saved as uncommitted transaction
     * in this Context. Use cautiously when dealing with changes that would break a regular commit one wy or the other.
     * Was used before JXP v0.7 to deal with duplicate Elements because the XmlPersister could not find / uniquely
     * identify the {@link Element} that needed to be changed. But then 0.7 eliminated the need to locate the Element in
     * the first place meaning all obvious use cases for this class vanished. Only use if you know what you are doing.
     *
     * @param task to run
     */
    void apply(boolean instantApply, Runnable task);

    /**
     * same as {@link #apply(boolean, Runnable)} with instantApply = true as default value
     */
    void apply(Runnable task);

    /**
     * @return the current Transaction
     */
    @Nullable
    Transaction getTransaction();

    /**
     * @return the current Transaction, requires an active Transaction
     * @throws PersistException if no active transaction exists
     */
    Transaction getActiveTransaction();

    /**
     * @return the mutex key that may be used to synchronise tasks using {@link MutexSyncMode}. For persistent Contexts
     * this returns the canonical file path, else this uses the hash code of the document instance.
     */
    String getMutexKey();

    Internals internal();

    /**
     * Specialized Context that may be "bound" to any Object of type E, as in it can easy be retrieved from the {@link JxpBackend}
     * via {@link JxpBackend#getBoundContext(Object)} in which case the Context is returned if the Object it is bound to
     * is equal to the provided Object according to {@link Object#equals(Object)}.
     *
     * @param <E> Type the Context may be bound to
     */
    interface BindableContext<E> extends Context {

        /**
         * Get the instance of Type E which the Context is bound to
         *
         * @return object of Type E
         */
        E getBindingObject();

    }

    /**
     * Sub interface for methods intended for internal use to clearly separate them from the regular API while still allowing
     * access.
     */
    interface Internals {

        /**
         * Set this Context's Transaction. Used internally to switch between Transaction e.g. for VirtualEvents
         *
         * @param transaction to set
         */
        void setTransaction(Transaction transaction);

    }

}
