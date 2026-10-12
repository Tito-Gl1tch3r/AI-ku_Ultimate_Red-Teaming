package net.robinfriedli.jxp;

import java.io.InputStream;
import java.util.function.Consumer;

import org.testng.annotations.*;

import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.persist.Context;

public abstract class AbstractTest {

    protected JxpBackend jxp;

    @BeforeClass
    public void initializeJxp() {
        jxp = setupJxp();
    }

    protected InputStream getTestResource(String resourceName) {
        InputStream inputStream = getClass().getResourceAsStream(resourceName);

        if (inputStream == null) {
            throw new IllegalArgumentException("No such resource " + resourceName);
        }

        return inputStream;
    }

    protected void expectException(Class<? extends Throwable> exceptionType, Runnable runnable) {
        Throwable caught = null;
        try {
            runnable.run();
        } catch (Throwable e) {
            caught = e;
        }

        if (caught == null) {
            throw new IllegalStateException("Expected a Throwable of type " + exceptionType + " to be thrown");
        } else if (!exceptionType.isAssignableFrom(caught.getClass())) {
            throw new IllegalStateException(String.format("Expected exception of type: %s; got: %s", exceptionType, caught.getClass()));
        }
    }

    /**
     * Opens a Context for the provided XML file, creates a copy, performs the given action with the copied context and
     * optionally persists the copied context to an XmlFile in the resources/output directory
     *
     * @param persistAfter whether or not to write the new document to a file
     * @param resourceName the name of the source xml file
     * @param action       the task to perform
     */
    protected void doWithCopiedContext(boolean persistAfter, String resourceName, Consumer<Context> action) {
        doWithCopiedContextInternal(persistAfter, resourceName, action);
    }

    protected void doWithCopiedContext(String resourceName, Consumer<Context> action) {
        doWithCopiedContextInternal(true, resourceName, action);
    }

    /**
     * This private third method exists instead of one overload calling the other so that the stack trace is equally
     * deep for both cases, which is needed when getting the method name of the test for the output file.
     */
    private void doWithCopiedContextInternal(boolean persistAfter, String resourceName, Consumer<Context> action) {
        Context existingContext = jxp.createContext(getTestResource(resourceName));
        Context context = existingContext.copy();
        action.accept(context);

        if (persistAfter) {
            int index = 3;
            StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
            String methodName;
            if (stackTrace.length > index) {
                methodName = "@" + stackTrace[index].getMethodName();
            } else {
                methodName = "";
            }
            context.persist(String.format("src/test/resources/output/%s%s%s.xml", getClass().getSimpleName(), methodName, System.currentTimeMillis()));
        }
    }

    protected abstract JxpBackend setupJxp();

    protected static class ErrorReportingExceptionHandler implements Thread.UncaughtExceptionHandler {

        private Throwable error;

        public ErrorReportingExceptionHandler() {
        }

        @Override
        public void uncaughtException(Thread t, Throwable e) {
            error = e;
        }

        public Throwable getError() {
            return error;
        }
    }

}
