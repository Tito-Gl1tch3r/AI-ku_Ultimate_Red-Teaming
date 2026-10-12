package com.nccgroup.web3decoder.persistence;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.logging.Logging;
import burp.api.montoya.persistence.PersistedObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Manages cached ABIs using Burp's PersistedObject.
 * ABIs are cached based on a combination of chainId and contractAddress.
 */
public class CachedAbis {
    private static final String CACHED_ABIS_KEY = "cached_ABIs";

    private final MontoyaApi api;
    private final PersistedObject cachedAbisPO;

    /**
     * Constructs the CachedABIs manager.
     *
     * @param api The Montoya API instance.
     */
    public CachedAbis(MontoyaApi api) {
        this.api = api;
        this.cachedAbisPO = initializeCachedAbisPersistedObject();
    }

    /**
     * Initializes the "cached_ABIs" PersistedObject.
     * Creates it if it doesn't exist.
     *
     * @return The initialized PersistedObject for cached ABIs.
     */
    private PersistedObject initializeCachedAbisPersistedObject() {
        PersistedObject persistedObject = api.persistence().extensionData().getChildObject(CACHED_ABIS_KEY);
        if (persistedObject == null) {
            persistedObject = PersistedObject.persistedObject();
            api.persistence().extensionData().setChildObject(CACHED_ABIS_KEY, persistedObject);
            safeLogToOutput("Initialized cached_ABIs PersistedObject.");
        }
        return persistedObject;
    }

    /**
     * Retrieves the ABI from the cache for the given chainId and contractAddress.
     *
     * @param chainId         The chain ID.
     * @param contractAddress The contract address.
     * @return An Optional containing the ABI if present, otherwise empty.
     */
    public String getAbi(int chainId, String contractAddress) {
        String key = generateCacheKey(chainId, contractAddress);
        PersistedObject abiObject = cachedAbisPO.getChildObject(key);
        if (abiObject != null) {
            String abi = abiObject.getString("abi");
            if (abi != null && !abi.isEmpty()) {
                return abi;
            }
        }
        return null;
    }

    /**
     * Saves the ABI to the cache for the given chainId and contractAddress.
     *
     * @param chainId         The chain ID.
     * @param contractAddress The contract address.
     * @param abi             The ABI string.
     */
    public void saveAbi(int chainId, String contractAddress, String abi) {
        String key = generateCacheKey(chainId, contractAddress);
        PersistedObject abiObject = PersistedObject.persistedObject();
        abiObject.setString("abi", abi);
        cachedAbisPO.setChildObject(key, abiObject);
    }

    /**
     * Removes the ABI from the cache for the given chainId and contractAddress.
     *
     * @param chainId         The chain ID.
     * @param contractAddress The contract address.
     */
    public void removeAbi(int chainId, String contractAddress) {
        String key = generateCacheKey(chainId, contractAddress);
        PersistedObject abiObject = cachedAbisPO.getChildObject(key);
        if (abiObject != null) {
            cachedAbisPO.deleteChildObject(key);
        }
    }

    /**
     * Retrieves a list of all cached ABIs with their corresponding chainId and contractAddress.
     *
     * @return A list of ABIEntry objects containing chainId and contractAddress.
     */
    public List<ABIEntry> getAllCachedABIs() {
        List<ABIEntry> cachedABIsList = new ArrayList<>();
        Set<String> keys = cachedAbisPO.childObjectKeys();

        for (String key : keys) {
            String[] parts = key.split("_", 2);
            if (parts.length == 2) {
                try {
                    int chainId = Integer.parseInt(parts[0]);
                    String contractAddress = parts[1];
                    cachedABIsList.add(new ABIEntry(chainId, contractAddress));
                } catch (NumberFormatException e) {
                    safeLogToError("Invalid cache key format: " + key);
                }
            } else {
                safeLogToError("Invalid cache key structure: " + key);
            }
        }

        return cachedABIsList;
    }

    /**
     * Generates a unique cache key based on chainId and contractAddress.
     *
     * @param chainId         The chain ID.
     * @param contractAddress The contract address.
     * @return The generated cache key.
     */
    private String generateCacheKey(int chainId, String contractAddress) {
        return chainId + "_" + contractAddress.toLowerCase();
    }

    private void safeLogToOutput(String message) {
        try {
            Logging logger = api.logging();
            if (logger != null) {
                logger.logToOutput(message);
            }
        } catch (NullPointerException ignored) {
            // Burp logging backend may be temporarily unavailable in some UI lifecycle paths.
        } catch (Throwable ignored) {
            // Logging must never break cache/UI flows.
        }
    }

    private void safeLogToError(String message) {
        try {
            Logging logger = api.logging();
            if (logger != null) {
                logger.logToError(message);
            }
        } catch (NullPointerException ignored) {
            // Burp logging backend may be temporarily unavailable in some UI lifecycle paths.
        } catch (Throwable ignored) {
            // Logging must never break cache/UI flows.
        }
    }

    /**
     * Represents a cached ABI entry with chainId and contractAddress.
     */
    public static class ABIEntry {
        private final int chainId;
        private final String contractAddress;

        public ABIEntry(int chainId, String contractAddress) {
            this.chainId = chainId;
            this.contractAddress = contractAddress;
        }

        public int getChainId() {
            return chainId;
        }

        public String getContractAddress() {
            return contractAddress;
        }

        @Override
        public String toString() {
            return "ABIEntry{" +
                    "chainId=" + chainId +
                    ", contractAddress='" + contractAddress + '\'' +
                    '}';
        }
    }
}
