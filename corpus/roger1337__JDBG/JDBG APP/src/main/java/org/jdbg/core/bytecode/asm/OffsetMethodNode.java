package org.jdbg.core.bytecode.asm;

import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

import java.util.ArrayList;
import java.util.List;

public class OffsetMethodNode extends MethodNode {


    OffsetClassReader reader;
    public OffsetMethodNode(
            final int access,
            final String name,
            final String descriptor,
            final String signature,
            final String[] exceptions, OffsetClassReader reader) {
        super(Opcodes.ASM9, access, name, descriptor, signature, exceptions);
        this.reader = reader;

    }
    List<Integer> offsets = new ArrayList<>();


    @Override
    public void visitFrame(int type, int numLocal, Object[] local, int numStack, Object[] stack) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitFrame(type, numLocal, local, numStack, stack);
    }

    @Override
    public void visitInsn(int opcode) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitInsn(opcode);
    }

    @Override
    public void visitIntInsn(int opcode, int operand) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitIntInsn(opcode, operand);
    }

    @Override
    public void visitVarInsn(int opcode, int varIndex) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitVarInsn(opcode, varIndex);
    }

    @Override
    public void visitTypeInsn(int opcode, String type) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitTypeInsn(opcode, type);
    }

    @Override
    public void visitFieldInsn(int opcode, String owner, String name, String descriptor) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitFieldInsn(opcode, owner, name, descriptor);
    }

    @Override
    public void visitMethodInsn(int opcodeAndSource, String owner, String name, String descriptor, boolean isInterface) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitMethodInsn(opcodeAndSource, owner, name, descriptor, isInterface);
    }

    @Override
    public void visitInvokeDynamicInsn(String name, String descriptor, Handle bootstrapMethodHandle, Object... bootstrapMethodArguments) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitInvokeDynamicInsn(name, descriptor, bootstrapMethodHandle, bootstrapMethodArguments);
    }

    @Override
    public void visitJumpInsn(int opcode, Label label) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitJumpInsn(opcode, label);
    }

    @Override
    public void visitLabel(Label label) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitLabel(label);
    }

    @Override
    public void visitLdcInsn(Object value) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitLdcInsn(value);
    }

    @Override
    public void visitIincInsn(int varIndex, int increment) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitIincInsn(varIndex, increment);
    }

    @Override
    public void visitTableSwitchInsn(int min, int max, Label dflt, Label... labels) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitTableSwitchInsn(min, max, dflt, labels);
    }

    @Override
    public void visitLookupSwitchInsn(Label dflt, int[] keys, Label[] labels) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitLookupSwitchInsn(dflt, keys, labels);
    }

    @Override
    public void visitMultiANewArrayInsn(String descriptor, int numDimensions) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitMultiANewArrayInsn(descriptor, numDimensions);
    }

    @Override
    public AnnotationVisitor visitInsnAnnotation(int typeRef, TypePath typePath, String descriptor, boolean visible) {
        return super.visitInsnAnnotation(typeRef, typePath, descriptor, visible);
    }

    @Override
    public void visitTryCatchBlock(Label start, Label end, Label handler, String type) {
        super.visitTryCatchBlock(start, end, handler, type);
    }

    @Override
    public AnnotationVisitor visitTryCatchAnnotation(int typeRef, TypePath typePath, String descriptor, boolean visible) {
        return super.visitTryCatchAnnotation(typeRef, typePath, descriptor, visible);
    }

    @Override
    public void visitLocalVariable(String name, String descriptor, String signature, Label start, Label end, int index) {
        super.visitLocalVariable(name, descriptor, signature, start, end, index);
    }

    @Override
    public AnnotationVisitor visitLocalVariableAnnotation(int typeRef, TypePath typePath, Label[] start, Label[] end, int[] index, String descriptor, boolean visible) {
        return super.visitLocalVariableAnnotation(typeRef, typePath, start, end, index, descriptor, visible);
    }

    @Override
    public void visitLineNumber(int line, Label start) {
        offsets.add(reader.getCurrentBytecodeOffset());
        super.visitLineNumber(line, start);
    }

    @Override
    public void visitMaxs(int maxStack, int maxLocals) {
        super.visitMaxs(maxStack, maxLocals);
    }

    public List<Integer> getOffsets() {
        return offsets;
    }
}
