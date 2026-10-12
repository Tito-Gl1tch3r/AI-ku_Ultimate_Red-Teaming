package net.robinfriedli.jxp.queries;

import java.util.Arrays;
import java.util.function.Function;
import java.util.function.Predicate;

import javax.annotation.Nullable;

import com.google.common.base.Strings;
import net.robinfriedli.jxp.api.StringConverter;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.exceptions.ConversionException;

public final class ValueComparator {

    private final Source source;
    private String attributeName;

    public ValueComparator(Source source) {
        this(source, null);
    }

    public ValueComparator(Source source, @Nullable String attributeName) {
        this.source = source;
        if (source == Source.ATTRIBUTE) {
            if (attributeName != null) {
                this.attributeName = attributeName;
            } else {
                throw new IllegalArgumentException("Source is ATTRIBUTE but no attribute name provided");
            }
        } else if (attributeName != null) {
            throw new IllegalArgumentException("Attribute name provided but Source is not ATTRIBUTE");
        }
    }

    public <E> Predicate<XmlElement> is(E value) {
        if (value instanceof String) {
            return predicate(value::equals);
        } else {
            return predicate(val -> StringConverter.convert(val, value.getClass()).equals(value));
        }
    }

    public Predicate<XmlElement> fuzzyIs(String s) {
        return predicate(s::equalsIgnoreCase);
    }

    @SuppressWarnings("SuspiciousMethodCalls")
    @SafeVarargs
    public final <E> Predicate<XmlElement> in(E... values) {
        if (values instanceof String[]) {
            return predicate(value -> Arrays.asList((String[]) values).contains(value));
        } else {
            return predicate(value -> Arrays.asList(values).contains(StringConverter.convert(value, values.getClass().getComponentType())));
        }
    }

    public Predicate<XmlElement> isEmpty() {
        return predicate(Strings::isNullOrEmpty);
    }

    @SuppressWarnings("unchecked")
    public Predicate<XmlElement> greaterThan(Comparable<? extends Number> i) {
        return predicate(value -> StringConverter.convert(value, i.getClass()).compareTo(i) > 0);
    }

    @SuppressWarnings("unchecked")
    public Predicate<XmlElement> greaterEquals(Comparable<? extends Number> i) {
        return predicate(value -> StringConverter.convert(value, i.getClass()).compareTo(i) >= 0);
    }

    @SuppressWarnings("unchecked")
    public Predicate<XmlElement> lowerThan(Comparable<? extends Number> i) {
        return predicate(value -> StringConverter.convert(value, i.getClass()).compareTo(i) < 0);
    }

    @SuppressWarnings("unchecked")
    public Predicate<XmlElement> lowerEquals(Comparable<? extends Number> i) {
        return predicate(value -> StringConverter.convert(value, i.getClass()).compareTo(i) <= 0);
    }

    public Predicate<XmlElement> startsWith(String s) {
        return predicate(value -> value.startsWith(s));
    }

    public Predicate<XmlElement> endsWith(String s) {
        return predicate(value -> value.endsWith(s));
    }

    public Predicate<XmlElement> contains(String s) {
        return predicate(value -> value.contains(s));
    }

    public Predicate<XmlElement> matches(Function<String, Boolean> expressionToCheck) {
        return predicate(expressionToCheck);
    }

    private Predicate<XmlElement> predicate(Function<String, Boolean> matchFunc) {
        switch (source) {
            case ATTRIBUTE:
                return element -> element.hasAttribute(attributeName)
                    && getMatch(element.getAttribute(attributeName).getValue(), matchFunc);
            case TEXT_CONTENT:
                return element -> getMatch(element.getTextContent(), matchFunc);
        }

        throw new IllegalStateException("Illegal source " + source);
    }

    private boolean getMatch(String toCheck, Function<String, Boolean> matchFunc) {
        try {
            return matchFunc.apply(toCheck);
        } catch (ConversionException e) {
            return false;
        }
    }

    enum Source {

        ATTRIBUTE,
        TEXT_CONTENT

    }

}
