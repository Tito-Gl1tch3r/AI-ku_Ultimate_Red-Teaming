package com.nccgroup.web3decoder;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.Http;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.logging.Logging;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class Web3RequestContextDecoderTest {

    // Single eth_call with both `to` and `data`, so it reaches the decoder-init branch.
    private static final String ETH_CALL_BODY =
            "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{"
                    + "\"to\":\"0x1111111111111111111111111111111111111111\","
                    + "\"data\":\"0x70a08231000000000000000000000000000000000000000000000000000000000000dead\"}],"
                    + "\"id\":1}";

    // eth_sendRawTransaction carrying the EIP-1559 sample (embedded chainId 1337).
    private static final String SEND_RAW_TX_BODY =
            "{\"id\":4700418092893,\"jsonrpc\":\"2.0\",\"method\":\"eth_sendRawTransaction\",\"params\":[\""
                    + "0x02f9015b820539808459682f00850df8475800830493e0947a250d5630b4cf539739df2c5dacb4c659f2488d880de0b6b3a7640000b8e47ff36ab500000000000000000000000000000000000000000000009e0950598867d8000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000002105eaa660ff62b14a5e093fc348e13ab63af2e600000000000000000000000000000000000000000000000000000000623b16570000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000006b175474e89094c44da98b954eedeac495271d0fc001a005cfdf9ff11dea2d3e8781cb6ba140ae6e86a0922bfa75938b6f2456f513e24ca057f02b3f7125edb59e22651d503bc296153860e3843f9d495ad21d898c8e20c3"
                    + "\"]}";

    @Test
    void reportsUnconfiguredChainWithActionableMessage() {
        MontoyaApi api = mock(MontoyaApi.class);
        Http http = mock(Http.class);
        Logging logging = mock(Logging.class);
        ExtensionConfig config = mock(ExtensionConfig.class);

        HttpRequest request = mock(HttpRequest.class);
        when(request.bodyToString()).thenReturn(ETH_CALL_BODY);
        when(request.url()).thenReturn("https://rpc.test/unconfigured");
        when(request.withBody(anyString())).thenReturn(mock(HttpRequest.class));

        // eth_chainId probe resolves to 0x2105 = 8453 (Base).
        HttpResponse chainResponse = mock(HttpResponse.class);
        when(chainResponse.bodyToString()).thenReturn("{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":\"0x2105\"}");
        HttpRequestResponse chainRR = mock(HttpRequestResponse.class);
        when(chainRR.response()).thenReturn(chainResponse);

        when(api.http()).thenReturn(http);
        when(http.sendRequest(any(HttpRequest.class))).thenReturn(chainRR);

        // Chain resolves, but the user hasn't configured it.
        when(config.getChain(8453)).thenReturn(null);

        HttpRequestResponse requestResponse = mock(HttpRequestResponse.class);
        when(requestResponse.request()).thenReturn(request);

        Web3RequestContextDecoder decoder = new Web3RequestContextDecoder(api, config, logging);
        List<Map<String, Object>> rows = decoder.decodeAndStore(requestResponse, "key-unconfigured");

        assertEquals(1, rows.size());
        Map<String, Object> row = rows.get(0);
        assertEquals("error", row.get("status"));
        assertEquals(
                "Chain ID 8453 is not in your configured chains. Add it under the \"Web3\" tab → "
                        + "\"Chains Management\" to enable ABI-based decoding.",
                row.get("reason"));
    }

    @Test
    void attemptsChainAgnosticFallbacksWhenChainIdUnresolved() {
        // When eth_chainId fails we no longer refuse to decode — we still try the
        // chain-agnostic paths (detected ABI pool, then 4byte). With no detected
        // entries and 4byte unreachable in this test, decode falls through to the
        // standard "ABI lookup failed" error rather than the legacy "Could not
        // determine chain ID" early-return.
        MontoyaApi api = mock(MontoyaApi.class);
        Http http = mock(Http.class);
        Logging logging = mock(Logging.class);
        ExtensionConfig config = mock(ExtensionConfig.class);

        HttpRequest request = mock(HttpRequest.class);
        when(request.bodyToString()).thenReturn(ETH_CALL_BODY);
        when(request.url()).thenReturn("https://rpc.test/unreachable");
        when(request.withBody(anyString())).thenReturn(mock(HttpRequest.class));

        // Every outbound HTTP call fails — eth_chainId probe, proxy storage slot
        // probes, and the 4byte lookup all throw.
        when(api.http()).thenReturn(http);
        when(api.logging()).thenReturn(logging);
        when(http.sendRequest(any(HttpRequest.class))).thenThrow(new RuntimeException("connection refused"));
        // External lookups gated on by default — match real config defaults so we
        // exercise the 4byte fallback path the test was written for.
        when(config.isFourByteLookupEnabled()).thenReturn(true);
        when(config.isBlockExplorerLookupEnabled()).thenReturn(true);

        HttpRequestResponse requestResponse = mock(HttpRequestResponse.class);
        when(requestResponse.request()).thenReturn(request);

        Web3RequestContextDecoder decoder = new Web3RequestContextDecoder(api, config, logging);
        List<Map<String, Object>> rows = decoder.decodeAndStore(requestResponse, "key-unreachable");

        assertEquals(1, rows.size());
        Map<String, Object> row = rows.get(0);
        assertEquals("error", row.get("status"));
        String reason = String.valueOf(row.get("reason"));
        assertTrue(reason.contains("ABI lookup failed"),
                "expected decode-attempt failure rather than chain-ID refusal, got: " + reason);
    }

    @Test
    void decodesRawTransactionEnvelopeAndUsesEmbeddedChainId() {
        MontoyaApi api = mock(MontoyaApi.class);
        Http http = mock(Http.class);
        Logging logging = mock(Logging.class);
        ExtensionConfig config = mock(ExtensionConfig.class);

        HttpRequest request = mock(HttpRequest.class);
        when(request.bodyToString()).thenReturn(SEND_RAW_TX_BODY);
        when(request.url()).thenReturn("https://rpc.test/raw");

        // The chain id (1337) is embedded in the signed tx and not configured.
        when(config.getChain(1337)).thenReturn(null);

        HttpRequestResponse requestResponse = mock(HttpRequestResponse.class);
        when(requestResponse.request()).thenReturn(request);

        Web3RequestContextDecoder decoder = new Web3RequestContextDecoder(api, config, logging);
        List<Map<String, Object>> rows = decoder.decodeAndStore(requestResponse, "key-raw");

        assertEquals(1, rows.size());
        Map<String, Object> row = rows.get(0);

        @SuppressWarnings("unchecked")
        Map<String, Object> tx = (Map<String, Object>) row.get("transaction");
        assertEquals("eip1559", tx.get("txType"));
        assertEquals(1337L, tx.get("chainId"));
        assertEquals("0x2105eaa660ff62b14a5e093fc348e13ab63af2e6", tx.get("from"));
        assertEquals("0x7a250d5630b4cf539739df2c5dacb4c659f2488d", tx.get("to"));

        // The envelope is shown even though the inner decode can't proceed.
        assertEquals("error", row.get("status"));
        assertEquals(
                "Chain ID 1337 is not in your configured chains. Add it under the \"Web3\" tab → "
                        + "\"Chains Management\" to enable ABI-based decoding.",
                row.get("reason"));

        // Embedded chain id is authoritative: no eth_chainId probe is sent.
        verify(http, never()).sendRequest(any(HttpRequest.class));
    }
}
