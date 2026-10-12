package net.robinfriedli.jxp.queries;

import java.util.Collection;
import java.util.function.Predicate;
import java.util.stream.Stream;

import net.robinfriedli.jxp.api.XmlElement;

public class Query {

    private final Predicate<XmlElement> expression;
    private Order<?> order;

    public Query(Predicate<XmlElement> expression) {
        this.expression = expression;
    }

    public static Query evaluate(Predicate<XmlElement> expression) {
        return new Query(expression);
    }

    public ResultStream<XmlElement> execute(Collection<XmlElement> elements) {
        return execute(elements, XmlElement.class);
    }

    public <E extends XmlElement> ResultStream<E> execute(Collection<XmlElement> elements, Class<E> type) {
        Stream<E> found = elements.stream().filter(expression).map(type::cast);

        if (order != null) {
            found = order.applyOrder(found);
        }

        return new ResultStream<>(found);
    }

    public Query order(Order<?> order) {
        this.order = order;
        return this;
    }

}
