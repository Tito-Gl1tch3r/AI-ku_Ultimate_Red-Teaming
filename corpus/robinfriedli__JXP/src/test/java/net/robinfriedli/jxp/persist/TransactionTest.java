package net.robinfriedli.jxp.persist;

import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.atomic.AtomicInteger;

import org.testng.annotations.*;

import com.google.common.collect.Lists;
import net.robinfriedli.exec.Mode;
import net.robinfriedli.exec.modes.MutexSyncMode;
import net.robinfriedli.jxp.AbstractTest;
import net.robinfriedli.jxp.api.JxpBackend;
import net.robinfriedli.jxp.api.JxpBuilder;
import net.robinfriedli.jxp.api.XmlElement;
import net.robinfriedli.jxp.entities.City;
import net.robinfriedli.jxp.entities.Country;
import net.robinfriedli.jxp.entities.State;
import net.robinfriedli.jxp.events.Event;
import net.robinfriedli.jxp.events.JxpEventListener;
import net.robinfriedli.jxp.exceptions.PersistException;
import net.robinfriedli.jxp.exec.AbstractTransactionalMode;
import net.robinfriedli.jxp.exec.QueuedTask;
import net.robinfriedli.jxp.queries.Query;

import static net.robinfriedli.jxp.queries.Conditions.*;
import static org.testng.Assert.*;

public class TransactionTest extends AbstractTest {

    @Override
    protected JxpBackend setupJxp() {
        return new JxpBuilder()
            .mapClass("city", City.class)
            .mapClass("state", State.class)
            .mapClass("country", Country.class)
            .build();
    }

    @Test
    public void testSequentialInvoke() {
        FlushListener flushListener = new FlushListener();
        jxp.addListener(flushListener);
        doWithCopiedContext("/countries.xml", context -> {
            context.invokeSequential(1, () -> {
                XmlElement switzerland = context.requireElement("Switzerland");
                switzerland.setAttribute("population", 32);
                XmlElement zurich = switzerland.requireSubElement("Zurich");
                zurich.setAttribute("population", 3443);
                XmlElement unitedKingdom = context.requireElement("United Kingdom");
                unitedKingdom.setAttribute("name", "test");
            });

            assertEquals(flushListener.getFlushCount(), 3);
            jxp.removeListener(flushListener);
            FlushListener flushListener1 = new FlushListener();
            jxp.addListener(flushListener1);

            context.invokeSequential(3, () -> {
                int modCount = 0;
                for (XmlElement element : context.getElementsRecursive()) {
                    if (modCount > 5) {
                        break;
                    }

                    if (element.hasAttribute("population")) {
                        element.setAttribute("population", 0);
                        modCount++;
                    }
                }
            });

            assertEquals(flushListener1.getFlushCount(), 2);
            jxp.removeListener(flushListener1);
        });
    }

    @DataProvider
    public Object[] boolProvider() {
        return new Object[]{false, true};
    }

    @Test(dataProvider = "boolProvider")
    public void testSynchronisedTransactions(boolean runAsQueuedTask) {
        AtomicInteger checkpoint = new AtomicInteger(0);
        doWithCopiedContext("/countries.xml", context -> {
            Callable<Void> task1 = () -> {
                assertEquals(checkpoint.getAndIncrement(), 0);
                try {
                    XmlElement switzerland = context.getElement("Switzerland");
                    assertNotNull(switzerland);
                    switzerland.setAttribute("population", 10000);
                    State zurich = switzerland.getSubElement("Zurich", State.class);
                    assertNotNull(zurich);

                    Thread.sleep(1000);

                    XmlElement greaterManchester = context.query(and(
                        attribute("name").is("Greater Manchester"),
                        parentMatches(attribute("name").is("United Kingdom"))
                    )).requireOnlyResult();
                    greaterManchester.setAttribute("name", "test rename");
                    greaterManchester.requireSubElement("Manchester").delete();

                    XmlElement greaterLondon = greaterManchester.getParent().requireSubElement("Greater London");
                    greaterLondon.setAttribute("newarg", "val");

                    XmlElement unitedKingdom = greaterLondon.getParent();
                    assertEquals(unitedKingdom.getAttribute("name").getValue(), "United Kingdom");
                    assertFalse(unitedKingdom.hasAttribute("newarg"));

                    Thread.sleep(1000);
                } finally {
                    assertEquals(checkpoint.getAndIncrement(), 1);
                }

                return null;
            };

            Callable<Void> task2 = () -> {
                assertEquals(checkpoint.getAndIncrement(), 2);
                try {
                    XmlElement switzerland = context.requireElement("Switzerland");
                    XmlElement unitedKingdom = context.requireElement("United Kingdom");
                    XmlElement greaterManchester = unitedKingdom.getSubElement("test rename");
                    XmlElement greaterLondon = unitedKingdom.requireSubElement("Greater London");

                    Thread.sleep(1000);

                    assertEquals(switzerland.getAttribute("population").getInt(), 10000);
                    assertNotNull(greaterManchester);
                    XmlElement manchester = greaterManchester.getSubElement("Manchester");
                    assertNull(manchester);

                    switzerland.setAttribute("englishName", "britzerland");

                    assertEquals(greaterLondon.getAttribute("newarg").getValue(), "val");

                    unitedKingdom.setAttribute("newarg", "val");
                    unitedKingdom.setAttribute("name", "renamed");
                } finally {
                    assertEquals(checkpoint.getAndIncrement(), 3);
                }
                return null;
            };

            Callable<Void> task3 = () -> {
                assertEquals(checkpoint.getAndIncrement(), 4);
                try {
                    XmlElement switzerland = context.getElement("britzerland");
                    assertNotNull(switzerland);
                    switzerland.requireSubElement("Zurich").setAttribute("name", "Greater Zurich");

                    List<XmlElement> xmlElements = context.query(attribute("newarg").is("val")).collect();
                    assertEquals(xmlElements.size(), 2);
                    XmlElement greaterLondon = Query.evaluate(attribute("name").is("Greater London")).execute(xmlElements).requireOnlyResult();
                    greaterLondon.setAttribute("newarg", "newval");
                } finally {
                    assertEquals(checkpoint.get(), 5);
                }
                return null;
            };

            Thread t1;
            Thread t2;
            Thread t3;
            QueuedTask<Void> queuedTask1 = null;
            QueuedTask<Void> queuedTask2 = null;
            QueuedTask<Void> queuedTask3 = null;


            if (runAsQueuedTask) {
                Mode mode = Mode.create()
                    .with(new MutexSyncMode<>(context.getMutexKey(), Context.GLOBAL_CONTEXT_SYNC))
                    .with(AbstractTransactionalMode.Builder.create().build(context));
                queuedTask1 = context.futureInvoke(false, false, mode, task1);
                queuedTask2 = context.futureInvoke(false, false, mode, task2);
                queuedTask3 = context.futureInvoke(false, false, mode, task3);
                t1 = new Thread(queuedTask1);
                t2 = new Thread(queuedTask2);
                t3 = new Thread(queuedTask3);
            } else {
                t1 = new Thread(() -> context.invoke(task1));
                t2 = new Thread(() -> context.invoke(task2));
                t3 = new Thread(() -> context.invoke(task3));
            }

            ErrorReportingExceptionHandler exceptionHandler = new ErrorReportingExceptionHandler();

            t1.setUncaughtExceptionHandler(exceptionHandler);
            t2.setUncaughtExceptionHandler(exceptionHandler);
            t3.setUncaughtExceptionHandler(exceptionHandler);

            t1.start();
            try {
                // make sure thread 2 actually starts second
                Thread.sleep(20);
            } catch (InterruptedException ignored) {
            }
            t2.start();
            try {
                // run thread 3 after thread 1 finished but before thread 2 exits; if we do not wait for thread 1 to finish
                // and thread 2 and 3 are waiting for the lock at the same time there is no guarantee which one comes first.
                t1.join();
            } catch (InterruptedException ignored) {
            }
            t3.start();

            try {
                t1.join();
                t2.join();
                t3.join();
            } catch (InterruptedException ignored) {
            }

            Throwable error = exceptionHandler.getError();
            if (error instanceof RuntimeException) {
                throw (RuntimeException) error;
            } else if (error != null) {
                throw new RuntimeException(error);
            }

            if (runAsQueuedTask) {
                try {
                    queuedTask1.get();
                    queuedTask2.get();
                    queuedTask3.get();
                } catch (ExecutionException e) {
                    throw new RuntimeException(e);
                } catch (InterruptedException ignored) {
                }
            }
        });
    }

    @Test
    public void testSimpleTransaction() {
        doWithCopiedContext("/countries.xml", context -> {
            context.invoke(() -> {
                City zurich = new City("Zurich", 400000);
                City london = new City("London", 8000000);

                new Country("Schweiz2", "Switzerland2", true, Lists.newArrayList(zurich)).persist(context);
                new Country("England2", "England2", false, Lists.newArrayList(london)).persist(context);
            });

            context.invoke(() -> {
                City geneva = new City("Geneva", 200000);
                City manchester = new City("Manchester", 500000);

                Country switzerland = context.requireElement("Switzerland2", Country.class);
                Country england = context.requireElement("England2", Country.class);

                switzerland.addSubElement(geneva);
                england.addSubElement(manchester);
            });

            XmlElement switzerland = context.getElement("Switzerland2");
            assertNotNull(switzerland);
            XmlElement zurich = switzerland.getSubElement("Zurich");
            assertNotNull(zurich);
            assertEquals(zurich.getAttribute("population").getInt(), 400000);
            XmlElement england = context.getElement("England2");
            assertNotNull(england);
            XmlElement london = england.getSubElement("London");
            assertNotNull(london);
            assertEquals(london.getAttribute("population").getInt(), 8000000);
        });
    }

    @Test
    public void testRollback() {
        doWithCopiedContext(true, "/countries.xml", context -> {
            XmlElement england = context.requireElement("England");
            XmlElement london = england.requireSubElement("London");
            context.invoke(() -> {
                london.setAttribute("population", "8825000");
                london.delete();
            });

            context.invoke(() -> england.addSubElement(london));

            ForceRollBackListener forceRollBackListener = new ForceRollBackListener();
            jxp.addListener(forceRollBackListener);

            try {
                // expect CommitException
                // test if rolling back a committed ElementDeletingElement works when a change made to the same element fails after
                // that. Normally the next change would not even get committed when the element gets deleted so we need to change the
                // state and then delete the element manually for the commit to fail
                expectException(PersistException.class, () -> context.invoke(() -> {
                    england.delete();
                    england.internal().setState(XmlElement.State.CLEAN);
                    england.setAttribute("englishName", "testRollback");
                }));

                assertEquals(england.getAttribute("englishName").getValue(), "England");

                // test that the value gets rolled back correctly when changing the same attribute twice (rollback in reverse order
                // of added changes)
                expectException(PersistException.class, () -> context.invoke(() -> {
                    england.setAttribute("name", "testRollback");
                    england.setAttribute("name", "testRollback2");
                    england.delete();
                }));

                assertEquals(england.getAttribute("name").getValue(), "England");
            } finally {
                jxp.removeListener(forceRollBackListener);
            }
        });
    }

    @Test
    public void testAsyncTransaction() {
        doWithCopiedContext(false, "/countries.xml", context -> {
            QueuedTask<Void> future = context.futureInvoke(true, true, false, false, false, () -> {
                City englandIsMyCity = new City("England is my City", 60000000);
                context.requireElement("England").addSubElement(englandIsMyCity);
                Thread.sleep(100);
                return null;
            });
            new Thread(future).start();
            long count1 = Query.evaluate(attribute("name").is("England is my City")).execute(context.getElementsRecursive()).count();
            assertEquals(count1, 0);
            try {
                future.get();
            } catch (InterruptedException e) {
                return;
            } catch (ExecutionException e) {
                throw new RuntimeException(e);
            }
            long count2 = Query.evaluate(attribute("name").is("England is my City")).execute(context.getElementsRecursive()).count();
            assertEquals(count2, 1);
        });
    }

    /**
     * Test that when persisting and XmlElement with sub elements the created ElementCreatedEvents are added in proper
     * order (parent first).
     */
    @Test
    public void testCreationOrder() {
        doWithCopiedContext(false, "/countries.xml", context -> context.invoke(() -> {
            City city = new City("city", 1);
            State state = new State("state", 1, Lists.newArrayList(city));
            Country country = new Country("Country", "Country", true, Lists.newArrayList());
            country.addSubElement(state);
            country.persist(context);

            Transaction activeTransaction = context.getActiveTransaction();
            List<Event> changes = activeTransaction.getChanges();
            assertEquals(changes.size(), 3);
            assertTrue(changes.get(0).getSource() instanceof Country);
            assertTrue(changes.get(1).getSource() instanceof State);
            assertTrue(changes.get(2).getSource() instanceof City);
        }));
    }

    private static class FlushListener extends JxpEventListener {

        private int flushCount;

        @Override
        public void onBeforeFlush(Transaction transaction) {
            flushCount++;
        }

        int getFlushCount() {
            return flushCount;
        }

    }

    private static class ForceRollBackListener extends JxpEventListener {

        ForceRollBackListener() {
            super(true);
        }

        @Override
        public void onBeforeFlush(Transaction transaction) {
            throw new RuntimeException("Rolling back");
        }
    }

}
