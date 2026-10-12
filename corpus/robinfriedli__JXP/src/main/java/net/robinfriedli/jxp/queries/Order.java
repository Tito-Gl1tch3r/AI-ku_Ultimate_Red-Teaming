package net.robinfriedli.jxp.queries;

import java.util.Comparator;
import java.util.stream.Stream;

import javax.annotation.Nullable;

import net.robinfriedli.jxp.api.StringConverter;
import net.robinfriedli.jxp.api.XmlElement;


public class Order<E extends Comparable<E>> {

    @Nullable
    private final String attribute;
    private final Direction direction;
    private final Source source;
    private final Class<E> attributeType;

    public Order(Direction direction, Source source, Class<E> attributeType) {
        this(null, direction, source, attributeType);
    }

    public Order(@Nullable String attribute, Direction direction, Source source, Class<E> attributeType) {
        this.source = source;
        this.direction = direction;
        this.attributeType = attributeType;
        if (source == Source.ATTRIBUTE) {
            if (attribute != null) {
                this.attribute = attribute;
            } else {
                throw new IllegalArgumentException("Source is ATTRIBUTE but no attribute name provided");
            }
        } else if (attribute != null) {
            throw new IllegalArgumentException("Attribute name provided but Source is not ATTRIBUTE");
        } else {
            this.attribute = null;
        }
    }

    public static Order<String> attribute(String name, Direction direction) {
        return new Order<>(name, direction, Source.ATTRIBUTE, String.class);
    }

    public static Order<String> attribute(String name) {
        return new Order<>(name, Direction.ASCENDING, Source.ATTRIBUTE, String.class);
    }

    public static Order<String> textContent(Direction direction) {
        return new Order<>(direction, Source.TEXT_CONTENT, String.class);
    }

    public static Order<String> textContent() {
        return new Order<>(Direction.ASCENDING, Source.TEXT_CONTENT, String.class);
    }

    public static <E extends Comparable<E>> Order<E> attribute(String name, Direction direction, Class<E> attributeType) {
        return new Order<>(name, direction, Source.ATTRIBUTE, attributeType);
    }

    public static <E extends Comparable<E>> Order<E> attribute(String name, Class<E> attributeType) {
        return new Order<>(name, Direction.ASCENDING, Source.ATTRIBUTE, attributeType);
    }

    public static <E extends Comparable<E>> Order<E> textContent(Direction direction, Class<E> attributeType) {
        return new Order<>(direction, Source.TEXT_CONTENT, attributeType);
    }

    public static <E extends Comparable<E>> Order<E> textContent(Class<E> attributeType) {
        return new Order<>(Direction.ASCENDING, Source.TEXT_CONTENT, attributeType);
    }

    public <O extends XmlElement> Stream<O> applyOrder(Stream<O> resultStream) {
        Comparator<XmlElement> comparator = getComparator();
        return resultStream.sorted(comparator);
    }

    public Comparator<XmlElement> getComparator() {
        Comparator<XmlElement> comparator;
        if (source == Source.ATTRIBUTE) {
            comparator = Comparator.comparing(v -> v.getAttribute(attribute).getValue(attributeType));
        } else {
            comparator = Comparator.comparing(v -> StringConverter.convert(v.getTextContent(), attributeType));
        }

        if (direction == Direction.DESCENDING) {
            return comparator.reversed();
        } else {
            return comparator;
        }
    }

    public enum Direction {

        ASCENDING,
        DESCENDING

    }

    enum Source {

        ATTRIBUTE,
        TEXT_CONTENT

    }

}
