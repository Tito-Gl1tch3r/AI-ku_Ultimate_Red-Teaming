package org.jdbg.core.bytecode.decompiler.vineflower;

import org.jetbrains.java.decompiler.main.Fernflower;
import org.jetbrains.java.decompiler.main.extern.IFernflowerPreferences;
import org.jdbg.core.bytecode.decompiler.ClassDecompiler;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

public class VineflowerDecompiler extends ClassDecompiler {

    Fernflower f;
    byte[] bytes;
    String className;
    public VineflowerDecompiler(byte[] bytes, String className) {
        super(bytes);
        Map<String, Object> properties = new HashMap<>(IFernflowerPreferences.DEFAULTS);
        properties.put(IFernflowerPreferences.BYTECODE_SOURCE_MAPPING, "1");
        f = new Fernflower(new NoResultSaver(), properties, new VineflowerLogger());
        this.bytes = bytes;
        this.className = className;
    }

    @Override
    public String decompile() {
        VineflowerSource source = new VineflowerSource(bytes, className);
        f.addSource(source);
        f.decompileContext();

        String s = source.getSink().getDecompiledOutput().get();

        System.out.println(Arrays.toString(source.getSink().getMapping()));

        return s;
    }


}
