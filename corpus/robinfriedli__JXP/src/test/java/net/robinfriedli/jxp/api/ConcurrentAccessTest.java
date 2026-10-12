package net.robinfriedli.jxp.api;

import org.testng.annotations.*;

import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.persist.Context;

public class ConcurrentAccessTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder().build();
    }

    @AfterMethod
    public void cleanup() {
        jxp.clearContexts();
    }

    @Test
    public void testConcurrentCheckForContext() throws Throwable {
        Context context = jxp.getContext("src/test/resources/countries.xml");

        for (int i = 0; i < 5000; i++) {
            Context copy = context.copy();
            jxp.attachContext(copy);
        }

        Context.BindableContext<String> c2 = jxp.createBoundContext("src/test/resources/fullcountries.xml", "c2");
        Context.BindableContext<String> c3 = jxp.createBoundContext("src/test/resources/fullcountries-raw.xml", "c3");

        jxp.attachContext(c2);
        jxp.attachContext(c3);

        Runnable runnable = () -> {
            for (int i = 0; i < 5000; i++) {
                jxp.getContext("src/test/resources/countries.xml");
                jxp.getContext("src/test/resources/fullcountries.xml");
                jxp.getContext("src/test/resources/fullcountries-raw.xml");

                jxp.getExistingContext("src/test/resources/countries.xml");
                jxp.getExistingContext("src/test/resources/fullcountries.xml");
                jxp.getExistingContext("src/test/resources/fullcountries-raw.xml");

                jxp.getBoundContext("c1");
                jxp.getBoundContext("c2");
                jxp.getBoundContext("c3");

                jxp.hasBoundContext("c4");
                jxp.hasBoundContext("c1");
                jxp.hasContext("foo");
                jxp.hasContext(context.getDocument());
            }
        };

        Thread t1 = new Thread(runnable);
        Thread t2 = new Thread(runnable);
        Thread t3 = new Thread(runnable);
        Thread t4 = new Thread(() -> {
            for (int i = 0; i < 5000; i++) {
                Context copy = context.copy();
                jxp.attachContext(copy);
            }
        });

        ErrorReportingExceptionHandler exceptionHandler = new ErrorReportingExceptionHandler();

        t1.setUncaughtExceptionHandler(exceptionHandler);
        t2.setUncaughtExceptionHandler(exceptionHandler);
        t3.setUncaughtExceptionHandler(exceptionHandler);
        t4.setUncaughtExceptionHandler(exceptionHandler);

        t1.start();
        t2.start();
        t3.start();
        t4.start();

        t1.join();
        t2.join();
        t3.join();
        t4.join();

        Throwable error = exceptionHandler.getError();
        if (error != null) {
            throw error;
        }
    }

    @Test
    public void testConcurrentContextCreation() throws Throwable {
        Runnable runnable = () -> {
            for (int i = 0; i < 5000; i++) {
                jxp.getContext("src/test/resources/countries.xml");
                jxp.getContext("src/test/resources/fullcountries.xml");
                if (i < 20) {
                    Context context = jxp.createContext(getTestResource("/fullcountries-raw.xml"));
                    jxp.attachContext(context);
                }
            }
        };

        Thread t1 = new Thread(runnable);
        Thread t2 = new Thread(runnable);
        Thread t3 = new Thread(runnable);

        ErrorReportingExceptionHandler exceptionHandler = new ErrorReportingExceptionHandler();
        t1.setUncaughtExceptionHandler(exceptionHandler);
        t2.setUncaughtExceptionHandler(exceptionHandler);
        t3.setUncaughtExceptionHandler(exceptionHandler);

        t1.start();
        t2.start();
        t3.start();

        t1.join();
        t2.join();
        t3.join();

        Throwable error = exceptionHandler.getError();
        if (error != null) {
            throw error;
        }

        jxp.requireExistingContext("src/test/resources/countries.xml");
        jxp.requireExistingContext("src/test/resources/fullcountries.xml");
    }

}
