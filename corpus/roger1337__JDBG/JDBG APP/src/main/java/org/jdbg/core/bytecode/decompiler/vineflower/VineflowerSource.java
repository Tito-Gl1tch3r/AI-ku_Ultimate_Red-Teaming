package org.jdbg.core.bytecode.decompiler.vineflower;

import org.jetbrains.java.decompiler.main.extern.IContextSource;
import org.jetbrains.java.decompiler.main.extern.IResultSaver;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class VineflowerSource implements IContextSource {

    byte[] bytes;
    OutputSink sink;
    String name;
    public VineflowerSource(byte[] bytes, String name) {
        this.bytes = bytes;
        this.sink = new OutputSink(name);
        this.name = name;
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public Entries getEntries() {

        List<Entry> entries = new ArrayList<>();
        entries.add(new Entry(name, Entry.BASE_VERSION));
        return new Entries(entries, Collections.emptyList(), Collections.emptyList());
    }

    @Override
    public InputStream getInputStream(String s) throws IOException {
        return new ByteArrayInputStream(bytes);
    }

    @Override
    public IOutputSink createOutputSink(IResultSaver saver) {
        return sink;
    }

    public OutputSink getSink() {
        return sink;
    }
}
