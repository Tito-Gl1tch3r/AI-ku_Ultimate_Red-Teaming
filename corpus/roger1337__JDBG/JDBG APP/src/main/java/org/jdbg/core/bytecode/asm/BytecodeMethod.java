package org.jdbg.core.bytecode.asm;

import org.jdbg.MiscUtil;
import org.objectweb.asm.tree.InsnList;

import java.util.List;

public class BytecodeMethod {


    protected InsnList instructions;
    protected List<String> textFormat;
    protected List<Integer> offsets;

    protected String name;

    protected String signature;

    protected int modifiers;

    private String parentClass;

    private int index;

    public BytecodeMethod(String parentClass, InsnList instructions, List<String> textFormat, List<Integer> offsets, String name, String signature, int modifiers, int index) {
        this.parentClass = parentClass;
        this.instructions = instructions;
        this.textFormat = textFormat;
        this.offsets = offsets;
        this.name = name;
        this.signature = signature;
        this.modifiers = modifiers;
        this.index = index;
    }

    public String getIdentifier() {
        String s = MiscUtil.buildModifiers(modifiers);
        s += " " + name + " : " + signature;
        return s;
    }

    public String getText() {
        StringBuilder text = new StringBuilder();

        String s = getIdentifier();
        text.append(s);
        text.append("\n");

        for(String line : textFormat) {
            text.append("   ");
            text.append(line);
            text.append('\n');
        }

        return text.toString();
    }

    public InsnList getInstructions() {
        return instructions;
    }

    public List<String> getTextFormat() {
        return textFormat;
    }

    public List<Integer> getOffsets() {
        return offsets;
    }

    public String getName() {
        return name;
    }

    public String getSignature() {
        return signature;
    }

    public int getModifiers() {
        return modifiers;
    }

    public int getIndex() {
        return index;
    }

    public String getParentClass() {
        return parentClass;
    }
}
