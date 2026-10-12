package com.six2dez.burp.aiagent.mcp

import com.six2dez.burp.aiagent.BuildFlags
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * SEC-05 5a: the MCP server used to advertise a hardcoded `Implementation("burp-ai-agent", "0.6.0")`
 * while the project moved on to a newer release. `BuildFlags.VERSION` is now generated from
 * `build.gradle.kts`'s single `version = "..."` declaration, so this test guards the seam rather
 * than the literal value.
 *
 * Naming note: the class name contains `BuildFlags` on purpose — the phase gate runs it via
 * `--tests '*BuildFlags*'`. It deliberately does NOT end in `IntegrationTest` (or any other suffix
 * listed in the `excludeHeavyTests` filter block inside `tasks.test` in `build.gradle.kts`), because
 * `-PexcludeHeavyTests=true` would silently skip it. Anchored on the symbol rather than a line
 * range: the previous `build.gradle.kts:145-157` citation went stale and cost real time twice.
 */
class McpBuildFlagsVersionTest {
    @Test
    fun version_isARealSemverAndNotTheHardcodedPlaceholder() {
        val semver = Regex("""^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$""")
        assertTrue(
            semver.matches(BuildFlags.VERSION),
            "BuildFlags.VERSION must be a semver string, was '${BuildFlags.VERSION}'",
        )
        // Deliberately not asserting a literal release number: that would couple every version bump
        // to a test edit. Only the stale hardcoded value is forbidden.
        assertNotEquals(
            "0.6.0",
            BuildFlags.VERSION,
            "BuildFlags.VERSION is still the stale hardcoded MCP placeholder",
        )
    }

    @Test
    fun storeBuild_flagStillGenerated() {
        // Proves the added version Property did not disturb the pre-existing store-build flag, by
        // asserting the SEAM rather than a fixed value: the generated constant must agree with the
        // -PstoreBuild value the build actually resolved. `build.gradle.kts`'s `tasks.test` block
        // carries that resolved Boolean in as `storeBuild.expected`, because the generated
        // `BuildFlags.STORE_BUILD` offers no other seam a test can compare against. Asserting a
        // literal `false` made `./gradlew test -PstoreBuild=true` fail — and that is the BApp Store
        // artifact build path, so the store artifact could not be validated before submission.
        //
        // An absent property (running this class outside Gradle, e.g. from an IDE) maps to false,
        // which matches the no-flag build. That default is deliberate, not an oversight.
        val expected = System.getProperty("storeBuild.expected")?.toBooleanStrictOrNull() == true
        assertEquals(
            expected,
            BuildFlags.STORE_BUILD,
            "generated BuildFlags.STORE_BUILD must track the -PstoreBuild Gradle property " +
                "(storeBuild.expected=$expected): flipping one without the other is the regression guarded here",
        )
    }
}
