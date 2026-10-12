package com.six2dez.burp.aiagent.config

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class McpSettingsTest {
    @Test
    fun roundTripToolToggles() {
        val input =
            mapOf(
                "http1_request" to false,
                "url_encode" to true,
            )
        val serialized = McpSettings.serializeToolToggles(input)
        val parsed = McpSettings.parseToolToggles(serialized)
        assertEquals(input, parsed)
    }

    @Test
    fun tokenGenerationProducesNonEmptyValue() {
        val token = McpSettings.generateToken()
        assertTrue(token.isNotBlank())
        assertTrue(token.length >= 32)
    }

    @Test
    fun roundTripAllowedOrigins() {
        val input =
            listOf(
                "https://app.example.com",
                "https://app.example.com",
                "http://localhost:3000",
            )
        val serialized = McpSettings.serializeAllowedOrigins(input)
        val parsed = McpSettings.parseAllowedOrigins(serialized)
        assertEquals(listOf("https://app.example.com", "http://localhost:3000"), parsed)
    }

    // ---- parseToolToggles: every payload shape a corrupted or hand-edited preference can hold ----
    //
    // These all reach the same production call site the MCP tab reads its per-tool enablement from.
    // A throw here would abort settings load, so "returns the documented shape and never throws" is
    // the contract, and each shape is asserted separately so a failure names which one broke.

    @Test
    fun parseToolToggles_nullOrBlankPayload_yieldsEmptyMap() {
        assertEquals(emptyMap(), McpSettings.parseToolToggles(null))
        assertEquals(emptyMap(), McpSettings.parseToolToggles(""))
        assertEquals(emptyMap(), McpSettings.parseToolToggles("   \n\t "))
    }

    @Test
    fun parseToolToggles_malformedJson_yieldsEmptyMapWithoutThrowing() {
        assertEquals(emptyMap(), McpSettings.parseToolToggles("{not json at all"))
        assertEquals(emptyMap(), McpSettings.parseToolToggles("}{"))
    }

    @Test
    fun parseToolToggles_jsonThatIsNotAnObject_yieldsEmptyMapWithoutThrowing() {
        assertEquals(emptyMap(), McpSettings.parseToolToggles("""["http1_request","url_encode"]"""))
        assertEquals(emptyMap(), McpSettings.parseToolToggles(""""a bare string""""))
    }

    @Test
    fun parseToolToggles_stringValuesAreReadAsBooleansCaseInsensitively() {
        val parsed =
            McpSettings.parseToolToggles(
                """{"a":"true","b":"false","c":"TRUE","d":"yes"}""",
            )
        // "yes" is not "true", so it reads as false — this documents the actual rule rather than an
        // assumed one: only the literal word "true" (any case) enables a tool.
        assertEquals(mapOf("a" to true, "b" to false, "c" to true, "d" to false), parsed)
    }

    @Test
    fun parseToolToggles_nonBooleanNonStringValuesAreDropped() {
        val parsed =
            McpSettings.parseToolToggles(
                """{"kept":true,"numeric":1,"nested":{"x":true},"nulled":null}""",
            )
        assertEquals(mapOf("kept" to true), parsed, "only Boolean and String values survive")
    }

    @Test
    fun parseToolToggles_blankKeysAreDroppedAndSurvivingKeysAreTrimmed() {
        val parsed = McpSettings.parseToolToggles("""{"  ":true,"  padded  ":true}""")
        assertEquals(mapOf("padded" to true), parsed)
    }

    @Test
    fun serializeToolToggles_failureYieldsTheEmptyObjectLiteral() {
        // Jackson refuses a null map key. The unchecked cast reproduces what a corrupted or
        // Java-interop-sourced map can actually hand this function, so the documented fail-soft
        // return is asserted as an observable outcome rather than read off the implementation.
        @Suppress("UNCHECKED_CAST")
        val hostile = mapOf<String?, Boolean>(null to true) as Map<String, Boolean>
        assertEquals("{}", McpSettings.serializeToolToggles(hostile))
    }

    // ---- unsafe tool set ----

    @Test
    fun parseUnsafeToolSet_nullOrBlankPayload_yieldsEmptySet() {
        assertEquals(emptySet(), McpSettings.parseUnsafeToolSet(null))
        assertEquals(emptySet(), McpSettings.parseUnsafeToolSet("  "))
    }

    @Test
    fun parseUnsafeToolSet_acceptsAllThreeSeparatorsAndTrimsAndDeduplicates() {
        val parsed = McpSettings.parseUnsafeToolSet("  send_request ,\n repeater_send ; send_request \n\n")
        assertEquals(setOf("send_request", "repeater_send"), parsed)
    }

    @Test
    fun serializeUnsafeToolSet_emptySetYieldsEmptyString() {
        assertEquals("", McpSettings.serializeUnsafeToolSet(emptySet()))
    }

    @Test
    fun serializeUnsafeToolSet_dropsBlanksAndEmitsSortedCommaSeparatedIds() {
        val serialized = McpSettings.serializeUnsafeToolSet(setOf(" zeta ", "alpha", "   ", "mid"))
        assertEquals("alpha,mid,zeta", serialized, "output must be trimmed, blank-free and sorted")
    }

    @Test
    fun roundTripUnsafeToolSet() {
        val input = setOf("repeater_send", "send_request")
        assertEquals(input, McpSettings.parseUnsafeToolSet(McpSettings.serializeUnsafeToolSet(input)))
    }

    // ---- allowed origins: the blank-entry and distinct filters on BOTH directions ----

    @Test
    fun parseAllowedOrigins_dropsBlankEntriesAndDuplicates() {
        val parsed = McpSettings.parseAllowedOrigins("https://a.example, ,,\n  \nhttps://a.example;https://b.example")
        assertEquals(listOf("https://a.example", "https://b.example"), parsed)
    }

    @Test
    fun serializeAllowedOrigins_emptyListYieldsEmptyString() {
        assertEquals("", McpSettings.serializeAllowedOrigins(emptyList()))
    }

    @Test
    fun serializeAllowedOrigins_dropsBlankEntriesAndDuplicates() {
        val serialized =
            McpSettings.serializeAllowedOrigins(
                listOf("  https://a.example  ", "", "   ", "https://a.example", "https://b.example"),
            )
        assertEquals("https://a.example\nhttps://b.example", serialized)
    }
}
