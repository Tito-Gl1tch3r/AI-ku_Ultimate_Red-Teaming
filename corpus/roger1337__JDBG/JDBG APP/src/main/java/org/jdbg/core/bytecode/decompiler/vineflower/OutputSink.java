package org.jdbg.core.bytecode.decompiler.vineflower;

import org.jetbrains.java.decompiler.main.extern.IContextSource;

import java.io.IOException;

public class OutputSink implements IContextSource.IOutputSink {

    String name;
    int[] mapping;
    protected final ThreadLocal<String> out = new ThreadLocal<>();

    protected OutputSink(String name) {
        this.name = name;
    }
    protected ThreadLocal<String> getDecompiledOutput() {
        return out;
    }

    public int[] getMapping() {
        return mapping;
    }

    @Override
    public void begin() {
        // no-op
    }

    @Override
    public void acceptClass(String qualifiedName, String fileName, String content, int[] mapping) {
        if (name.equals(qualifiedName))
            out.set(content);
        this.mapping = mapping;
    }

    @Override
    public void acceptDirectory(String directory) {
        // no-op
    }

    @Override
    public void acceptOther(String path) {
        // no-op
    }

    @Override
    public void close() throws IOException {
        // no-op
    }
}