package net.robinfriedli.jxp.exec.modes;

import java.util.concurrent.Callable;

import net.robinfriedli.exec.AbstractNestedModeWrapper;
import net.robinfriedli.jxp.api.JxpBackend;
import org.jetbrains.annotations.NotNull;

public class ListenersMutedMode extends AbstractNestedModeWrapper {

    private final JxpBackend jxpBackend;

    public ListenersMutedMode(JxpBackend jxpBackend) {
        this.jxpBackend = jxpBackend;
    }

    @NotNull
    @Override
    public <E> Callable<E> wrap(@NotNull Callable<E> callable) {
        return () -> {
            boolean prevState = jxpBackend.isListenersMuted();
            jxpBackend.setListenersMuted(true);
            try {
                return callable.call();
            } finally {
                jxpBackend.setListenersMuted(prevState);
            }
        };
    }

}
