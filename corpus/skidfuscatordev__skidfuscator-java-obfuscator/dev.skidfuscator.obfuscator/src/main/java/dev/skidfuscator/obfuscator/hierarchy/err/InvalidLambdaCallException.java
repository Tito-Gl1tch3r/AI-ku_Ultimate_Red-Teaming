package dev.skidfuscator.obfuscator.hierarchy.err;

import org.mapleir.asm.ClassNode;
import org.mapleir.asm.MethodNode;
import org.objectweb.asm.Handle;

public class InvalidLambdaCallException extends RuntimeException {
    public InvalidLambdaCallException(Handle boundFunc, ClassNode node) {
        super(String.format(
                """
                -----------------------------------------------------
                /!\\ Skidfuscator failed to verify a lambda call! 
                Please report this to the developer...
                -----------------------------------------------------
                Bound: %s
                Target: %s
                Target Methods: %s
                -----------------------------------------------------
                """,
                boundFunc,
                node.getDisplayName(),
                node.getMethods().stream()
                        .map(MethodNode::toString)
                        .reduce("\n- ", (s, s2) -> s + "\n- " + s2)

        ));
    }
}
