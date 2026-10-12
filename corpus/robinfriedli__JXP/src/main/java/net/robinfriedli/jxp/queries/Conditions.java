package net.robinfriedli.jxp.queries;

import java.util.Arrays;
import java.util.Collection;
import java.util.function.Predicate;

import net.robinfriedli.jxp.api.XmlElement;

public final class Conditions {

    @SafeVarargs
    public static Predicate<XmlElement> and(Predicate<XmlElement>... predicates) {
        return element -> Arrays.stream(predicates).allMatch(predicate -> predicate.test(element));
    }

    @SafeVarargs
    public static Predicate<XmlElement> or(Predicate<XmlElement>... predicates) {
        return element -> Arrays.stream(predicates).anyMatch(predicate -> predicate.test(element));
    }

    @SafeVarargs
    public static Predicate<XmlElement> not(Predicate<XmlElement>... predicates) {
        return element -> Arrays.stream(predicates).noneMatch(predicate -> predicate.test(element));
    }

    public static ValueComparator attribute(String name) {
        return new ValueComparator(ValueComparator.Source.ATTRIBUTE, name);
    }

    public static ValueComparator textContent() {
        return new ValueComparator(ValueComparator.Source.TEXT_CONTENT);
    }

    public static Predicate<XmlElement> subElementOf(XmlElement element) {
        return elem -> elem.getParent() == element;
    }

    public static Predicate<XmlElement> parentOf(XmlElement element) {
        return elem -> element.getParent() == elem;
    }

    public static Predicate<XmlElement> in(XmlElement... elements) {
        return in(Arrays.asList(elements));
    }

    public static Predicate<XmlElement> in(Collection<XmlElement> elements) {
        return elements::contains;
    }

    public static Predicate<XmlElement> instanceOf(Class<? extends XmlElement> c) {
        return c::isInstance;
    }

    public static Predicate<XmlElement> tagName(String tagName) {
        return elem -> elem.getTagName().equals(tagName);
    }

    public static Predicate<XmlElement> existsSubElement(Predicate<XmlElement> subPredicate) {
        return and(XmlElement::hasSubElements, xmlElement -> xmlElement.getSubElements().stream().anyMatch(subPredicate));
    }

    public static Predicate<XmlElement> allSubElementsMatch(Predicate<XmlElement> subPredicate) {
        return and(XmlElement::hasSubElements, xmlElement -> xmlElement.getSubElements().stream().allMatch(subPredicate));
    }

    public static Predicate<XmlElement> parentMatches(Predicate<XmlElement> parentPredicate) {
        return xmlElement -> xmlElement.getParent() != null && parentPredicate.test(xmlElement.getParent());
    }

}
