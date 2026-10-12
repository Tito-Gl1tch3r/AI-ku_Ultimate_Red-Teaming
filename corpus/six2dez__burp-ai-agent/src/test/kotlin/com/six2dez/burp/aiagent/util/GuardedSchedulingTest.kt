package com.six2dez.burp.aiagent.util

import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertDoesNotThrow
import org.junit.jupiter.api.assertTimeoutPreemptively
import java.time.Duration
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * REL-06 / SC1 — the behavioural acceptance suite for [runGuarded] and [scheduleGuarded].
 *
 * **Naming constraint (hard).** `build.gradle.kts` excludes `*IntegrationTest`, `*ConcurrencyTest`,
 * `*BackpressureTest`, `*RestartPolicyTest` and `*SupervisionTest` under `-PexcludeHeavyTests=true`,
 * which is exactly what `.github/workflows/build.yml` passes. `GuardedSchedulingTest` is the approved
 * name; `SchedulerConcurrencyTest` would have been the natural one and would have made this suite
 * silently stop running on the PR gate.
 *
 * **No test here compares an elapsed duration to a threshold.** Survival of a recurring schedule is
 * proved by a [CountDownLatch] that only later ticks can release, wrapped in
 * [assertTimeoutPreemptively] so the failure mode of a cancelled schedule is a categorical timeout
 * rather than a wall-clock comparison. Nothing here constructs a Swing component or a Burp API.
 *
 * The two survival tests run against a REAL [java.util.concurrent.ScheduledExecutorService] with a
 * REAL throw and a REAL next tick, because the defect being closed is the JDK's own documented
 * behaviour: a recurring task whose run throws is suppressed for the life of the executor. A mock
 * scheduler could not reproduce it.
 */
class GuardedSchedulingTest {
    /** Lines recorded through the injected `logError` lambda, in the order the guard emitted them. */
    private val logged = CopyOnWriteArrayList<String>()

    /** Every executor a test started, shut down in [stopExecutors] whether the test passed or not. */
    private val executors = CopyOnWriteArrayList<ScheduledExecutorService>()

    @BeforeEach
    fun resetRecorders() {
        logged.clear()
        executors.clear()
    }

    @AfterEach
    fun stopExecutors() {
        executors.forEach { it.shutdownNow() }
        executors.clear()
    }

    /**
     * REL-06-A — the whole point of the phase: a recurring schedule whose body throws on its first
     * tick still fires on the ticks after it.
     *
     * Without the guard the JDK suppresses every subsequent execution and the subsystem is dead for
     * the rest of the Burp session with nothing in the error log.
     */
    @Test
    fun aThrowOnTheFirstTickDoesNotCancelTheRecurringSchedule() {
        val executor = newScheduler()
        val invocations = AtomicInteger(0)
        val laterTicks = CountDownLatch(2)

        assertTimeoutPreemptively(Duration.ofSeconds(TIMEOUT_SECONDS)) {
            executor.scheduleGuarded(
                "TestComponent",
                "recurring tick",
                { logged.add(it) },
                0,
                TICK_DELAY_MILLIS,
                TimeUnit.MILLISECONDS,
            ) {
                if (invocations.incrementAndGet() == 1) {
                    error("first tick blew up")
                }
                laterTicks.countDown()
            }

            assertTrue(
                laterTicks.await(AWAIT_SECONDS, TimeUnit.SECONDS),
                "Ticks 2 and 3 never ran after tick 1 threw. The recurring schedule was cancelled by the " +
                    "uncaught throw, which is exactly the REL-06 defect: scheduleGuarded must absorb the " +
                    "throw so the next tick still fires.",
            )
        }
    }

    /**
     * REL-06-B — the guard catches [Throwable], not only [Exception].
     *
     * The JDK suppresses subsequent executions on ANY throwable reaching the task, an `Error`
     * included, so a guard narrowed to `Exception` would leave the defect open for the exact cases
     * that are hardest to reproduce.
     */
    @Test
    fun anErrorOnTheFirstTickDoesNotCancelTheRecurringScheduleEither() {
        val executor = newScheduler()
        val invocations = AtomicInteger(0)
        val laterTick = CountDownLatch(1)

        assertTimeoutPreemptively(Duration.ofSeconds(TIMEOUT_SECONDS)) {
            executor.scheduleGuarded(
                "TestComponent",
                "recurring tick",
                { logged.add(it) },
                0,
                TICK_DELAY_MILLIS,
                TimeUnit.MILLISECONDS,
            ) {
                if (invocations.incrementAndGet() == 1) {
                    throw StackOverflowError("first tick hit an Error, not an Exception")
                }
                laterTick.countDown()
            }

            assertTrue(
                laterTick.await(AWAIT_SECONDS, TimeUnit.SECONDS),
                "Tick 2 never ran after tick 1 threw an Error. The guard is catching Exception rather " +
                    "than Throwable, so an Error still cancels the schedule permanently.",
            )
        }
    }

    /**
     * REL-06-C — a suppressed failure is visible. Swallowing without logging would trade a silent
     * dead subsystem for a silent broken one.
     */
    @Test
    fun aSuppressedFailureIsLoggedOnceWithTheComponentPrefixAndTheTaskLabel() {
        runGuarded("TestComponent", "expiry cleanup", { logged.add(it) }) {
            throw IllegalStateException("cleanup exploded")
        }

        assertEquals(
            1,
            logged.size,
            "runGuarded must record exactly one line for one suppressed failure; recorded: $logged",
        )
        val line = logged.first()
        assertTrue(
            line.startsWith("[TestComponent] "),
            "CONVENTIONS.md §Error Handling mandates the `[Component] ...` prefix; got: $line",
        )
        assertTrue(
            line.contains("expiry cleanup"),
            "The line must name the failing task so an operator can tell WHICH schedule tripped; got: $line",
        )
        assertTrue(
            line.contains("cleanup exploded"),
            "The line must carry the throwable's message or the operator has nothing to diagnose; got: $line",
        )
    }

    /**
     * A-EDGE-2 (empty case) — a no-op tick logs nothing.
     *
     * Both registry cleaners tick over an empty map, and `processQueue()` ticks over an empty queue,
     * every few hundred milliseconds. A guard that logged on the success path would flood the Burp
     * error log at 2 Hz.
     */
    @Test
    fun aSuccessfulOrNoOpTickRecordsNothing() {
        runGuarded("TestComponent", "no-op tick", { logged.add(it) }) {
            // INTENTIONAL: an empty body is the empty-input case — nothing to clean, nothing to log.
        }

        assertEquals(
            0,
            logged.size,
            "A body that did not throw must produce zero log lines; recorded: $logged",
        )
    }

    /**
     * A-EDGE-2 (empty case, second form) — a throwable whose `message` is `null`.
     *
     * `NullPointerException` and most `Error` subclasses arrive with a null message. The guard must
     * still emit exactly one line and must not itself throw while building it.
     *
     * The neighbouring half of that property — a `logError` that throws rather than a message that is
     * null — is asserted by [runGuardedDoesNotRethrowWhenTheLogSinkItselfThrows] and
     * [aThrowingLogSinkDoesNotCancelTheRecurringSchedule].
     */
    @Test
    fun aThrowableWithANullMessageStillRecordsExactlyOneLine() {
        runGuarded("TestComponent", "null-message tick", { logged.add(it) }) {
            throw IllegalStateException()
        }

        assertEquals(
            1,
            logged.size,
            "A throwable with a null message must still record exactly one line; recorded: $logged",
        )
        assertTrue(
            logged.first().startsWith("[TestComponent] null-message tick failed:"),
            "The prefix must survive a null message; got: ${logged.first()}",
        )
    }

    /**
     * REL-06-D — the guard's own reporting cannot escape it.
     *
     * `logError` is caller-supplied and is not required to be self-guarding: `ActiveAiScanner` passes a
     * raw `{ api.logging().logToError(it) }`, and a `MontoyaApi` torn down mid-unload is exactly the
     * condition under which the guarded body is also most likely to throw. A `logError` that throws
     * from inside the catch reaches the JDK scheduler and cancels the recurring task permanently — the
     * REL-06 defect this helper exists to close, re-opened at the one chokepoint every migrated call
     * site now depends on.
     */
    @Test
    fun runGuardedDoesNotRethrowWhenTheLogSinkItselfThrows() {
        assertDoesNotThrow(
            "runGuarded must never rethrow. A throw from logError escapes the guard, reaches the JDK " +
                "scheduler and cancels the recurring task for the rest of the session with nothing in any " +
                "log — the exact REL-06 defect the guard exists to close.",
        ) {
            runGuarded("TestComponent", "reporting tick", { throw IllegalStateException("log sink is gone") }) {
                error("body blew up")
            }
        }
    }

    /**
     * REL-06-D, end to end — the scheduled form of the property above, proved against a REAL
     * [java.util.concurrent.ScheduledExecutorService] and a REAL next tick, because the failure being
     * closed is the JDK's own suppression behaviour and a mock scheduler could not reproduce it.
     */
    @Test
    fun aThrowingLogSinkDoesNotCancelTheRecurringSchedule() {
        val executor = newScheduler()
        val invocations = AtomicInteger(0)
        val laterTicks = CountDownLatch(2)

        assertTimeoutPreemptively(Duration.ofSeconds(TIMEOUT_SECONDS)) {
            executor.scheduleGuarded(
                "TestComponent",
                "recurring tick",
                { throw IllegalStateException("log sink is gone") },
                0,
                TICK_DELAY_MILLIS,
                TimeUnit.MILLISECONDS,
            ) {
                if (invocations.incrementAndGet() == 1) {
                    error("first tick blew up")
                }
                laterTicks.countDown()
            }

            assertTrue(
                laterTicks.await(AWAIT_SECONDS, TimeUnit.SECONDS),
                "Ticks 2 and 3 never ran after the guard's own logError threw. The schedule was " +
                    "cancelled by a throw the guard let escape from inside its own catch, which is the " +
                    "REL-06 defect (SC1) in its most damaging form: the fault containment mechanism " +
                    "itself is the thing that kills the schedule.",
            )
        }
    }

    private fun newScheduler(): ScheduledExecutorService {
        val executor = Executors.newSingleThreadScheduledExecutor()
        executors.add(executor)
        return executor
    }

    private companion object {
        const val TIMEOUT_SECONDS = 5L
        const val AWAIT_SECONDS = 4L
        const val TICK_DELAY_MILLIS = 10L
    }
}
