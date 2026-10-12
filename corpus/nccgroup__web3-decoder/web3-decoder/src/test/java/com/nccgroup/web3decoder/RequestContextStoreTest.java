package com.nccgroup.web3decoder;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RequestContextStoreTest {

    @Test
    void storesAndRetrievesContextByIdAndIndex() {
        String requestKey = "req-batch-1";
        RequestContextStore.clearRequestContext(requestKey);

        RequestContextStore.storeContext(requestKey, "id:42", "balanceOf(address)", "abi-1");
        RequestContextStore.storeContext(requestKey, "index:3", "allowance(address,address)", "abi-2");

        RequestContextStore.ContextEntry byId = RequestContextStore.getContext(requestKey, "id:42");
        RequestContextStore.ContextEntry byIndex = RequestContextStore.getContext(requestKey, "index:3");

        assertNotNull(byId);
        assertEquals("balanceOf(address)", byId.functionSignature());
        assertEquals("abi-1", byId.abiJson());

        assertNotNull(byIndex);
        assertEquals("allowance(address,address)", byIndex.functionSignature());
        assertEquals("abi-2", byIndex.abiJson());

        assertTrue(RequestContextStore.hasAnyContext(requestKey));
    }

    @Test
    void preservesLegacySettersCompatibility() {
        String requestKey = "req-legacy-1";
        RequestContextStore.clearRequestContext(requestKey);

        RequestContextStore.storeFunctionSignature(requestKey, "transfer(address,uint256)");
        RequestContextStore.storeAbiJson(requestKey, "abi-legacy");

        assertEquals("transfer(address,uint256)", RequestContextStore.getFunctionSignature(requestKey));
        assertEquals("abi-legacy", RequestContextStore.getAbiJson(requestKey));

        RequestContextStore.ContextEntry legacy = RequestContextStore.getLegacyContext(requestKey);
        assertNotNull(legacy);
        assertEquals("transfer(address,uint256)", legacy.functionSignature());
        assertEquals("abi-legacy", legacy.abiJson());
    }

    @Test
    void clearRequestContextRemovesAllEntries() {
        String requestKey = "req-clear-1";
        RequestContextStore.storeContext(requestKey, "id:1", "foo()", "abi-x");

        RequestContextStore.clearRequestContext(requestKey);

        assertNull(RequestContextStore.getContext(requestKey, "id:1"));
        assertTrue(RequestContextStore.getContexts(requestKey).isEmpty());
        assertTrue(!RequestContextStore.hasAnyContext(requestKey));
    }
}
