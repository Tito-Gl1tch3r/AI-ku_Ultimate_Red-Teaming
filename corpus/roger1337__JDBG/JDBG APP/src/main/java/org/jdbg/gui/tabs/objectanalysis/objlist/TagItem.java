package org.jdbg.gui.tabs.objectanalysis.objlist;

import javax.swing.*;

public class TagItem extends JPanel {

    Integer tag;

    String klass;

    String name;

    boolean includeDir;

    public TagItem(TagItem item) {
        this.tag = item.tag;
        this.klass = item.klass;
        this.name = item.name;
    }

    public TagItem(Integer tag, String klass, String name) {
        this.tag = tag;
        this.klass = klass;
        this.name = name;
        this.includeDir = false;
    }

    public void setIncludeDir(boolean includeDir) {
        this.includeDir = includeDir;
    }


    @Override
    public String getName() {
        return name;
    }

    public String getKlass() {
        return klass;
    }

    public Integer getTag() {
        return tag;
    }

    @Override
    public String toString() {
        return (includeDir?("(" + klass + ") "): "")  + name + "." + tag;
    }
}
