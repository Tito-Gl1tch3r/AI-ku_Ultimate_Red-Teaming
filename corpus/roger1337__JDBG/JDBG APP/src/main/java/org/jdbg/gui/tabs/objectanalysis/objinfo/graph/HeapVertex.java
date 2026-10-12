package org.jdbg.gui.tabs.objectanalysis.objinfo.graph;

import java.io.Serializable;

public class HeapVertex implements Serializable {


    Integer tag;
    String origin;

    boolean isRoot;
    public HeapVertex(Integer tag) {
        this(tag, "N/A", false);
    }

    public HeapVertex(Integer tag, String origin, boolean isRoot) {
        this.tag = tag;
        this.origin = origin;
        this.isRoot = isRoot;
    }


    @Override
    public boolean equals(Object obj) {
        if(obj instanceof HeapVertex) {
            return tag.equals(((HeapVertex) obj).tag);
        }

        if(obj instanceof Integer) {
            return tag.equals(obj);
        }

        return false;
    }

    public boolean isRoot() {
        return isRoot;
    }

    @Override
    public int hashCode() {
        return tag;
    }

    @Override
    public String toString() {
        return origin + " (" + tag + ")";
    }
}
