package com.nccgroup.web3decoder.detection;

import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.scanner.AuditResult;
import burp.api.montoya.scanner.audit.issues.AuditIssue;
import burp.api.montoya.scanner.audit.issues.AuditIssueConfidence;
import burp.api.montoya.scanner.audit.issues.AuditIssueSeverity;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.function.BiFunction;
import java.util.function.Function;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AbiDetectionScanCheckTest {

    private DetectedAbiStore store;
    private AbiDetectionScanCheck check;
    // Capture the inputs the production code passes to the audit-issue factory so
    // tests can assert on detail/severity without depending on the real Montoya
    // AuditIssue.auditIssue(...) factory (which crashes outside a running Burp,
    // mirroring the PersistedObject.persistedObject() issue handled in Task 6).
    private String capturedDetail;
    private AuditIssueSeverity capturedSeverity;
    private AuditIssueConfidence capturedConfidence;
    private HttpRequestResponse capturedRequestResponse;
    private String capturedBaseUrl;

    @BeforeEach
    void setUp() {
        store = mock(DetectedAbiStore.class);
        capturedDetail = null;
        capturedSeverity = null;
        capturedConfidence = null;
        capturedRequestResponse = null;
        capturedBaseUrl = null;
        BiFunction<List<DetectedAbi>, AbiDetectionScanCheck.IssueContext, AuditIssue> issueFactory =
                (abis, ctx) -> {
                    capturedDetail = ctx.detail();
                    capturedSeverity = ctx.severity();
                    capturedConfidence = ctx.confidence();
                    capturedRequestResponse = ctx.requestResponse();
                    capturedBaseUrl = ctx.baseUrl();
                    return mock(AuditIssue.class);
                };
        Function<List<AuditIssue>, AuditResult> resultFactory = issues -> {
            AuditResult ar = mock(AuditResult.class);
            when(ar.auditIssues()).thenReturn(new ArrayList<>(issues));
            return ar;
        };
        check = new AbiDetectionScanCheck(store, issueFactory, resultFactory);
    }

    @Test
    void emptyBodyProducesNoIssues() {
        AuditResult result = check.doCheck(mockRequestResponse(""));
        assertEquals(0, result.auditIssues().size());
    }

    @Test
    void newAbiProducesOneInformationalIssue() {
        String body = "[{type:\"function\",name:\"foo\",inputs:[],outputs:[],stateMutability:\"view\"}]";
        when(store.saveIfNew(any(), anyString())).thenReturn(true);
        AuditResult result = check.doCheck(mockRequestResponse(body));
        assertEquals(1, result.auditIssues().size());
        assertEquals(AuditIssueSeverity.INFORMATION, capturedSeverity);
        assertEquals(AuditIssueConfidence.CERTAIN, capturedConfidence);
        assertNotNull(capturedDetail);
        assertTrue(capturedDetail.contains("Fingerprint"),
                "detail should mention fingerprint, got: " + capturedDetail);
        assertEquals("https://example.com/bundle.js", capturedBaseUrl);
        assertNotNull(capturedRequestResponse);
    }

    @Test
    void detailListsFunctionSignaturesAndSelectors() {
        // ERC-20 balanceOf — known selector 0x70a08231
        String body = "[{type:\"function\",name:\"balanceOf\","
                + "inputs:[{name:\"owner\",type:\"address\"}],"
                + "outputs:[{name:\"\",type:\"uint256\"}],"
                + "stateMutability:\"view\"}]";
        when(store.saveIfNew(any(), anyString())).thenReturn(true);
        check.doCheck(mockRequestResponse(body));
        assertNotNull(capturedDetail);
        assertTrue(capturedDetail.contains("balanceOf(address)"),
                "detail should show canonical signature, got: " + capturedDetail);
        assertTrue(capturedDetail.contains("0x70a08231"),
                "detail should show selector, got: " + capturedDetail);
        assertTrue(capturedDetail.contains("Functions"),
                "detail should label the Functions section, got: " + capturedDetail);
    }

    @Test
    void alreadyKnownAbiProducesNoIssue() {
        String body = "[{type:\"function\",name:\"foo\",inputs:[],outputs:[],stateMutability:\"view\"}]";
        when(store.saveIfNew(any(), anyString())).thenReturn(false);
        AuditResult result = check.doCheck(mockRequestResponse(body));
        assertEquals(0, result.auditIssues().size());
    }

    private HttpRequestResponse mockRequestResponse(String body) {
        HttpResponse response = mock(HttpResponse.class);
        HttpRequest request = mock(HttpRequest.class);
        HttpRequestResponse rr = mock(HttpRequestResponse.class);
        when(response.bodyToString()).thenReturn(body);
        when(rr.response()).thenReturn(response);
        when(rr.request()).thenReturn(request);
        when(request.url()).thenReturn("https://example.com/bundle.js");
        return rr;
    }
}
