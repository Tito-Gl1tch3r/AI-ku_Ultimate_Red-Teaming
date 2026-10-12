package com.nccgroup.web3decoder.persistence;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.logging.Logging;
import burp.api.montoya.persistence.Persistence;
import burp.api.montoya.persistence.Preferences;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ExtensionConfigDefaultsTest {

    private MontoyaApi api;
    private Preferences preferences;

    @BeforeEach
    void setUp() {
        api = mock(MontoyaApi.class);
        preferences = mock(Preferences.class);
        Persistence persistence = mock(Persistence.class);
        Logging logging = mock(Logging.class);

        when(api.persistence()).thenReturn(persistence);
        when(api.logging()).thenReturn(logging);
        when(persistence.preferences()).thenReturn(preferences);
        // Empty preferences -> all getBoolean / getString return null
        when(preferences.getBoolean(anyString())).thenReturn(null);
        when(preferences.getString(anyString())).thenReturn(null);
    }

    @Test
    void blockExplorerLookupDefaultsToTrue() {
        ExtensionConfig config = new ExtensionConfig(api);
        assertTrue(config.isBlockExplorerLookupEnabled());
    }

    @Test
    void fourByteLookupDefaultsToTrue() {
        ExtensionConfig config = new ExtensionConfig(api);
        assertTrue(config.isFourByteLookupEnabled());
    }

    @Test
    void historyAnnotationDefaultsToTrue() {
        ExtensionConfig config = new ExtensionConfig(api);
        assertTrue(config.isHistoryAnnotationEnabled());
    }

    @Test
    void disablingBlockExplorerLookupPersists() {
        ExtensionConfig config = new ExtensionConfig(api);
        config.setBlockExplorerLookupEnabled(false);
        assertFalse(config.isBlockExplorerLookupEnabled());
        verify(preferences).setBoolean("lookup.blockExplorer.enabled", false);
    }

    @Test
    void disablingFourByteLookupPersists() {
        ExtensionConfig config = new ExtensionConfig(api);
        config.setFourByteLookupEnabled(false);
        assertFalse(config.isFourByteLookupEnabled());
        verify(preferences).setBoolean("lookup.fourbyte.enabled", false);
    }
}
