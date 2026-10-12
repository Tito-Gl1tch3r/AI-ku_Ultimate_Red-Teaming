package net.robinfriedli.jxp.queries.xpath;

import java.util.Arrays;

import net.robinfriedli.jxp.api.StringConverter;
import org.openqa.selenium.support.ui.Quotes;

public final class XNodeBuilder {

    private final String left;

    public XNodeBuilder(String left) {
        this.left = left;
    }

    public <E> XNode is(E value) {
        String stringValue = getValueString(value);

        return new XComparingNode(left, stringValue, "=");
    }

    @SafeVarargs
    public final <E> XNode in(E... values) {
        XNode[] nodes = Arrays.stream(values).map(this::is).toArray(XNode[]::new);
        return new XJunctionNode(XJunctionNode.Type.OR, nodes);
    }

    public XNode greaterThan(Comparable<? extends Number> number) {
        return new XComparingNode(left, String.valueOf(number), ">");
    }

    public XNode greaterEquals(Comparable<? extends Number> number) {
        return new XComparingNode(left, String.valueOf(number), ">=");
    }

    public XNode lowerThan(Comparable<? extends Number> number) {
        return new XComparingNode(left, String.valueOf(number), "<");
    }

    public XNode lowerEquals(Comparable<? extends Number> number) {
        return new XComparingNode(left, String.valueOf(number), "<=");
    }

    public XNode startsWith(String s) {
        return new XFunctionNode("starts-with", left, Quotes.escape(s));
    }

    public XNode endsWith(String s) {
        String substringLeft = "string-length(" + left + ")";
        String substringRight = "string-length(" + Quotes.escape(s) + ")";
        XConditionNode greaterThanNode = new XConditionNode(substringLeft + ">=" + substringRight);
        XFunctionNode substringFunc = new XFunctionNode("substring", left, substringLeft + " - " + substringRight + " + 1");
        XComparingNode compareFunc = new XComparingNode(Quotes.escape(s), substringFunc.asString(), "=");
        return new XJunctionNode(XJunctionNode.Type.AND, greaterThanNode, compareFunc);
    }

    public XNode contains(String s) {
        return new XFunctionNode("contains", left, Quotes.escape(s));
    }

    private <E> String getValueString(E value) {
        if (value instanceof String) {
            return Quotes.escape((String) value);
        } else {
            return StringConverter.reverse(value);
        }
    }


}
