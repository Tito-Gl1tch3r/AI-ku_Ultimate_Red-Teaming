package com.six2dez.burp.aiagent.util

import java.net.InetAddress
import java.net.spi.InetAddressResolver
import java.net.spi.InetAddressResolverProvider
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicLong
import java.util.stream.Stream

/**
 * A JVM-wide name-resolution counter (JEP 418, Java 18+), installed for the whole test JVM so that
 * `SsrfGuardNoResolutionTest` can assert SEC-07's SC4 BEHAVIOURALLY rather than by structural grep.
 *
 * ### It counts. It never decides.
 *
 * The delegation below is non-negotiable and it is the whole safety argument. This provider is
 * installed for every suite in the repo — including the Netty MCP servers and OkHttp clients under
 * `mcp/` — via `src/test/resources/META-INF/services/java.net.spi.InetAddressResolverProvider`. It
 * must never filter, cache, reorder or substitute a result: every call is forwarded verbatim to
 * `configuration.builtinResolver()` and the counter is a pure side effect. Anything else and a
 * failure in an unrelated suite becomes this file's fault.
 *
 * Literal IP addresses never reach a resolver, so servers bound to `127.0.0.1` are unaffected by
 * construction; only genuine name lookups move the counter.
 *
 * ### Registration is the single point of failure
 *
 * That one-line service file is the ONLY thing that installs this provider. Delete it, misname it or
 * misspell the class and the counter simply never moves — at which point a "no resolution happened"
 * assertion passes vacuously. That is why `SsrfGuardNoResolutionTest` asserts a CONTROL lookup does
 * increment the counter before it asserts the SsrfGuard corpus does not.
 */
class CountingInetAddressResolverProvider : InetAddressResolverProvider() {
    override fun name(): String = "gsd-counting-inet-address-resolver"

    override fun get(configuration: Configuration): InetAddressResolver =
        object : InetAddressResolver {
            // Both overrides name configuration.builtinResolver() at their own delegation site rather
            // than sharing a hoisted field. The accessor is a plain field read on the JDK's
            // Configuration, and spelling it out here is what makes "counts, never decides" visible
            // per method instead of inferable from a variable four lines above.
            override fun lookupByName(
                host: String,
                lookupPolicy: InetAddressResolver.LookupPolicy,
            ): Stream<InetAddress> {
                noteLookup(host)
                return configuration.builtinResolver().lookupByName(host, lookupPolicy)
            }

            override fun lookupByAddress(addr: ByteArray): String {
                noteLookup(addr.joinToString(".") { (it.toInt() and 0xFF).toString() })
                return configuration.builtinResolver().lookupByAddress(addr)
            }
        }

    companion object {
        /** Bound on the recorded-name buffer, so a long-running suite cannot grow it without limit. */
        private const val MAX_RECORDED_NAMES = 32

        private val lookupCount = AtomicLong()
        private val recorded = CopyOnWriteArrayList<String>()

        /** Number of name resolutions that have reached the resolver since the last [reset]. */
        fun count(): Long = lookupCount.get()

        /** The most recently looked-up names, for naming the offender in a failure message. */
        fun recentNames(): List<String> = recorded.toList()

        fun reset() {
            lookupCount.set(0)
            recorded.clear()
        }

        private fun noteLookup(name: String) {
            lookupCount.incrementAndGet()
            if (recorded.size < MAX_RECORDED_NAMES) {
                recorded.add(name)
            }
        }
    }
}
