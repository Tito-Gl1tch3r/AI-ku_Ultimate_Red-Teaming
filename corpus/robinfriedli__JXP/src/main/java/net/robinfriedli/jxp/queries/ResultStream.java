package net.robinfriedli.jxp.queries;

import java.util.Collection;
import java.util.List;
import java.util.function.Supplier;
import java.util.stream.Collector;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.exceptions.QueryException;

/**
 * The filtered and sorted stream a query returns. All of these methods, except {@link #getResultStream()}, are terminal
 * operations, meaning only one of these methods can get called on the same stream instance once. If you need to call
 * several of these methods, see {@link QueryResult} and {@link #getResult()} which collects the results to a collection
 * and offers similar methods.
 *
 * @param <E> the type of XmlElements this stream holds
 */
public class ResultStream<E extends XmlElement> {

    private Stream<E> resultStream;
    private boolean terminated;

    public ResultStream(Stream<E> resultStream) {
        this.resultStream = resultStream;
    }

    // terminating operations

    @Nullable
    public E getFirstResult() {
        checkTerminated();
        terminated = true;
        return tryCollect(() -> resultStream.findFirst().orElse(null));
    }

    public E requireFirstResult() {
        E firstResult = getFirstResult();

        if (firstResult == null) {
            throw new IllegalStateException("No results found.");
        }

        return firstResult;
    }

    @Nullable
    public E getOnlyResult() {
        checkTerminated();
        terminated = true;
        Collector<E, ?, E> onlyResultCollector = Collectors.collectingAndThen(
            Collectors.toList(),
            list -> {
                if (list.size() > 1) {
                    throw new IllegalStateException("Expected at most 1 results but found " + list.size());
                } else if (list.size() == 1) {
                    return list.get(0);
                } else {
                    return null;
                }
            }
        );

        return tryCollect(() -> resultStream.collect(onlyResultCollector));
    }

    public E requireOnlyResult() {
        E onlyResult = getOnlyResult();

        if (onlyResult == null) {
            throw new IllegalStateException("No results found.");
        }

        return onlyResult;
    }

    public List<E> collect() {
        return collect(Collectors.toList());
    }

    public <C extends Collection<E>> C collect(Collector<E, ?, C> collector) {
        checkTerminated();
        terminated = true;
        return tryCollect(() -> resultStream.collect(collector));
    }

    public QueryResult<E, List<E>> getResult() {
        return getResult(Collectors.toList());
    }

    public <C extends Collection<E>> QueryResult<E, C> getResult(Collector<E, ?, C> collector) {
        checkTerminated();
        terminated = true;
        return tryCollect(() -> new QueryResult<>(resultStream.collect(collector)));
    }

    public long count() {
        checkTerminated();
        terminated = true;
        return tryCollect(() -> resultStream.count());
    }

    // non terminating operations

    public ResultStream<E> order(Order<?> order) {
        resultStream = order.applyOrder(resultStream);
        return this;
    }

    public Stream<E> getResultStream() {
        return resultStream;
    }

    private void checkTerminated() {
        if (terminated) {
            throw new QueryException("Stream has been terminated because it has already been operated upon. Use #getResult to collect a QueryResult.");
        }
    }

    private <R> R tryCollect(Supplier<R> supplier) {
        try {
            return supplier.get();
        } catch (ClassCastException e) {
            throw new QueryException("Some found elements could not be converted to the target type. " +
                "Consider expanding your query with the Conditions#instanceOf condition.", e);
        }
    }

}
