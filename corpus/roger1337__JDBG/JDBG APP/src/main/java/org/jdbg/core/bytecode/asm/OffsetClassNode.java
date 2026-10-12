package org.jdbg.core.bytecode.asm;

import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodNode;

public class OffsetClassNode extends ClassNode {

    OffsetClassReader reader;
    public OffsetClassNode(OffsetClassReader reader) {
        super(Opcodes.ASM9);
        this.reader = reader;
    }
    @Override
    public MethodVisitor visitMethod(int access, String name, String descriptor, String signature, String[] exceptions) {
        OffsetMethodNode method = new OffsetMethodNode(access, name, descriptor, signature, exceptions, reader);
        methods.add(method);
        return method;
    }
}
