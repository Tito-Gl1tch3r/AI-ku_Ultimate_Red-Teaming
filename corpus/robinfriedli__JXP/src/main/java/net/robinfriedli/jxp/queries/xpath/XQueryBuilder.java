package net.robinfriedli.jxp.queries.xpath;

import net.robinfriedli.jxp.persist.Context;

/**
 * Utility class to build XPath query Strings in a fluent API style
 * e.g.
 * <pre>
 *     {@code
 *     XQueryBuilder query2 = XQueryBuilder.find("country/city").where(or(
 *         and(
 *                 not(
 *                         and(
 *                                 attribute("population").in(200000, 400000, 1000000, 8900000),
 *                                 attribute("name").in("Birmingham", "New York")
 *                         )
 *                 ),
 *                 attribute("population").greaterThan(200000),
 *                 attribute("population").lowerThan(1000000)
 *         ),
 *         and(
 *                 or(
 *                         attribute("population").greaterThan(8000000),
 *                         attribute("population").lowerThan(1000000)
 *                 ),
 *                 attribute("name").in("London", "Manchester", "Birmingham"),
 *                 not(
 *                         or(
 *                                 attribute("name").in("New York"),
 *                                 attribute("name").contains("ches"),
 *                                 attribute("name").endsWith("ham")
 *                         )
 *                 )
 *         )
 *     ));
 *     String xPath2 = query2.getXPath(context);
 *     List<XmlElement> foundInstances = context.xPathQuery(xPath2);
 * }
 * </pre>
 */
public class XQueryBuilder {

    private final String pathAfterRoot;

    private XNode rootConditionNode;

    public XQueryBuilder(String pathAfterRoot) {
        this.pathAfterRoot = pathAfterRoot;
    }

    /**
     * Create a new XQueryBuilder that searches for XML elements with the given hierarchy path.
     *
     * @param elementPath that path (excluding the root document element) to the hierarchy level of the target XML elements,
     *                    for example, if you are searching for "city" elements that are children of "country" elements
     *                    the path would be "country/city"
     * @return the created XQueryBuilder
     */
    public static XQueryBuilder find(String elementPath) {
        return new XQueryBuilder(elementPath);
    }

    /**
     * Add a condition to this XQueryBuilder. If there already is a condition the existing condition will be combined
     * with the new condition in an AND condition.
     *
     * @param rootNode the new condition to add
     * @return this XQueryBuilder
     */
    public XQueryBuilder where(XNode rootNode) {
        if (rootConditionNode == null) {
            rootConditionNode = rootNode;
        } else {
            rootConditionNode = XConditions.and(rootConditionNode, rootNode);
        }

        return this;
    }

    public String getXPath(Context context) {
        StringBuilder xPathBuilder = new StringBuilder();
        xPathBuilder.append("/").append(context.getRootTag()).append("/").append(pathAfterRoot);
        if (rootConditionNode != null) {
            xPathBuilder.append("[").append(rootConditionNode.asString()).append("]");
        }

        return xPathBuilder.toString();
    }

}
