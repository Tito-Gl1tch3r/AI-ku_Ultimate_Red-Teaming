package org.jdbg.gui.tabs.objectanalysis.objinfo.graph;

import org.jgrapht.graph.DefaultEdge;

public class HeapEdge extends DefaultEdge {

    private String label;

     enum EdgeType {
        CLASS,
        INSTANCE_FIELD,
        ARRAY_ELEMENT,
        CLASS_LOADER,
        SIGNERS,
        PROTECTION_DOMAIN,
        INTERFACE,
        STATIC_FIELD,
        CONSTANT_POOL,
        SUPERCLASS,
        JNI_GLOBAL,
        SYSTEM_CLASS,
        MONITOR,
        STACK_LOCAL,
        JNI_LOCAL,
        THREAD,
        OTHER
    }

    static EdgeType[] values = EdgeType.values();
    public HeapEdge(Byte adjType) {
        this.label = values[adjType-1].toString();
    }

    /**
     * Gets the label associated with this edge.
     *
     * @return edge label
     */
    public String getLabel()  {
        return label;
    }

    @Override
    public String toString()
    {
        return label;
    }
}
