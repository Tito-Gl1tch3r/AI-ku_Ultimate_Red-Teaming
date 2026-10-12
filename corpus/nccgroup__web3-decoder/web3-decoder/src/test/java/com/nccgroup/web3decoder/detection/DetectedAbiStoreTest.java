package com.nccgroup.web3decoder.detection;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.logging.Logging;
import burp.api.montoya.persistence.Persistence;
import burp.api.montoya.persistence.PersistedObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DetectedAbiStoreTest {

    private MontoyaApi api;
    private PersistedObject extData;

    @BeforeEach
    void setUp() {
        api = mock(MontoyaApi.class);
        Persistence persistence = mock(Persistence.class);
        extData = new InMemoryPersistedObject();
        when(api.persistence()).thenReturn(persistence);
        when(persistence.extensionData()).thenReturn(extData);
        when(api.logging()).thenReturn(mock(Logging.class));
    }

    private DetectedAbiStore newStore(int capacity) {
        // The real Montoya PersistedObject.persistedObject() factory uses an
        // internal ObjectFactoryLocator that is not initialised outside a
        // running Burp. Inject InMemoryPersistedObject::new so tests can run
        // headless.
        return new DetectedAbiStore(api, capacity, InMemoryPersistedObject::new);
    }

    @Test
    void emptyStoreReturnsNoMatches() {
        DetectedAbiStore store = newStore(1024);
        assertEquals(List.of(), store.findBySelector("0x70a08231"));
    }

    @Test
    void savesAndFindsBySelector() {
        DetectedAbiStore store = newStore(1024);
        DetectedAbi abi = new DetectedAbi(
                "fp1", "[{...canonical...}]", List.of("0x70a08231"));
        boolean added = store.saveIfNew(abi, "https://example.com/bundle.js");
        assertTrue(added);
        List<DetectedAbi> found = store.findBySelector("0x70a08231");
        assertEquals(1, found.size());
        assertEquals("fp1", found.get(0).fingerprint());
    }

    @Test
    void duplicateFingerprintNotAddedTwice() {
        DetectedAbiStore store = newStore(1024);
        DetectedAbi abi = new DetectedAbi("fp1", "[]", List.of("0x70a08231"));
        assertTrue(store.saveIfNew(abi, "url1"));
        assertEquals(false, store.saveIfNew(abi, "url2"));
        assertEquals(1, store.findBySelector("0x70a08231").size());
    }

    @Test
    void reloadsFromPersistedObjectOnRestart() {
        DetectedAbiStore first = newStore(1024);
        first.saveIfNew(new DetectedAbi("fp1", "[]", List.of("0xaaaaaaaa")), "url");

        // Simulate restart: new store instance over same persistence.
        DetectedAbiStore second = newStore(1024);
        assertEquals(1, second.findBySelector("0xaaaaaaaa").size());
    }

    @Test
    void evictsOldestWhenAtCapacity() {
        DetectedAbiStore store = newStore(2);
        store.saveIfNew(new DetectedAbi("a", "[]", List.of("0x11111111")), "u");
        store.saveIfNew(new DetectedAbi("b", "[]", List.of("0x22222222")), "u");
        store.saveIfNew(new DetectedAbi("c", "[]", List.of("0x33333333")), "u");
        assertEquals(0, store.findBySelector("0x11111111").size()); // evicted
        assertEquals(1, store.findBySelector("0x22222222").size());
        assertEquals(1, store.findBySelector("0x33333333").size());
    }
}
