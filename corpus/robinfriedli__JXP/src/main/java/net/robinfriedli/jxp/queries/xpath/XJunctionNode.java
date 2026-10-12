package net.robinfriedli.jxp.queries.xpath;

import java.util.List;

import com.google.common.base.Joiner;
import com.google.common.collect.Lists;

public class XJunctionNode implements XNode {

    private final XNode[] nodes;
    private final Type type;

    public XJunctionNode(Type type, XNode... nodes) {
        this.type = type;
        this.nodes = nodes;
    }

    @Override
    public String asString() {
        Joiner selectorJoiner = Joiner.on(" " + type.name().toLowerCase() + " ");
        List<String> nodes = Lists.newArrayList();
        for (XNode node : this.nodes) {
            if (node instanceof XJunctionNode) {
                // put sub junction in brackets
                nodes.add("(" + node.asString() + ")");
            } else {
                nodes.add(node.asString());
            }
        }
        return selectorJoiner.join(nodes);
    }

    public enum Type {
        AND, OR
    }

}
