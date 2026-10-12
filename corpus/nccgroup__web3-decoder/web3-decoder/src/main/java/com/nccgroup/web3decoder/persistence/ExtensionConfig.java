package com.nccgroup.web3decoder.persistence;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.persistence.Preferences;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.InputStream;
import java.util.*;

/**
 * Handles the configuration and persistence of chain information within the Burp extension using Preferences and JSON.
 */
public class ExtensionConfig {
    private static final String PREFS_KEY = "chains.all"; // Key under which all chains are stored in Preferences
    private static final String PREFS_SHARED_ETHERSCAN_KEY = "chains.shared.etherscanApiKey";
    private static final String PREFS_ANNOTATION_ENABLED = "annotation.enabled";
    private static final String PREFS_BLOCK_EXPLORER_LOOKUP_ENABLED = "lookup.blockExplorer.enabled";
    private static final String PREFS_FOURBYTE_LOOKUP_ENABLED = "lookup.fourbyte.enabled";

    private final MontoyaApi api;
    private final Preferences preferences;
    private final ObjectMapper objectMapper;
    private Map<Integer, ChainInfo> chains;
    private String sharedEtherscanApiKey;
    private boolean historyAnnotationEnabled;
    private boolean blockExplorerLookupEnabled;
    private boolean fourByteLookupEnabled;

    /**
     * Constructs the ExtensionConfig and initializes the chains from persistence or resources.
     *
     * @param api The Montoya API instance provided by Burp.
     */
    public ExtensionConfig(MontoyaApi api) {
        this.api = api;
        this.preferences = api.persistence().preferences();
        this.objectMapper = new ObjectMapper();
        this.chains = new HashMap<>();
        this.sharedEtherscanApiKey = Optional.ofNullable(preferences.getString(PREFS_SHARED_ETHERSCAN_KEY)).orElse("");
        Boolean storedAnnotation = preferences.getBoolean(PREFS_ANNOTATION_ENABLED);
        this.historyAnnotationEnabled = storedAnnotation == null ? true : storedAnnotation; // default ON
        Boolean storedBlockExplorer = preferences.getBoolean(PREFS_BLOCK_EXPLORER_LOOKUP_ENABLED);
        this.blockExplorerLookupEnabled = storedBlockExplorer == null ? true : storedBlockExplorer; // default ON
        Boolean storedFourByte = preferences.getBoolean(PREFS_FOURBYTE_LOOKUP_ENABLED);
        this.fourByteLookupEnabled = storedFourByte == null ? true : storedFourByte; // default ON

        loadChains();
    }

    /**
     * Loads chains from Preferences and merges them with chains from resources.
     * If a chain exists in resources but not in Preferences, it is added with an empty API key.
     * If a chain exists in both, the API key from Preferences is retained.
     */
    private void loadChains() {
        // Load chains from resources
        Map<Integer, ChainInfo> resourceChains = loadChainsFromResources();
        if (resourceChains == null || resourceChains.isEmpty()) {
            api.logging().logToError("No chains loaded from resources.");
            return;
        }

        // Load chains from Preferences
        Map<Integer, ChainInfo> persistedChains = loadChainsFromPreferences();
        persistedChains = migrateDeprecatedChains(persistedChains, resourceChains);

        // Merge chains: preference data overrides resource data
        for (Map.Entry<Integer, ChainInfo> entry : resourceChains.entrySet()) {
            int chainId = entry.getKey();
            ChainInfo resourceChain = entry.getValue();

            if (persistedChains.containsKey(chainId)) {
                // Merge API keys: retain persisted API key
                ChainInfo persistedChain = persistedChains.get(chainId);
                resourceChain.setExplorerAPIKey(persistedChain.getExplorerAPIKey());
            } else {
                // New chain from resources: set API key as empty string
                resourceChain.setExplorerAPIKey("");
            }

            chains.put(chainId, resourceChain);
        }

        // Add any chains that exist in Preferences but not in resources (optional)
        for (Map.Entry<Integer, ChainInfo> entry : persistedChains.entrySet()) {
            int chainId = entry.getKey();
            if (!resourceChains.containsKey(chainId)) {
                chains.put(chainId, entry.getValue());
            }
        }

        // Persist the merged chains to Preferences
        saveChains();
    }

    private Map<Integer, ChainInfo> migrateDeprecatedChains(Map<Integer, ChainInfo> persistedChains, Map<Integer, ChainInfo> resourceChains) {
        if (persistedChains == null || persistedChains.isEmpty()) {
            return new HashMap<>();
        }

        Map<Integer, Integer> migrationMap = Map.of(
                3, 11155111,
                4, 11155111,
                5, 11155111,
                42, 11155111,
                17000, 560048
        );

        Map<Integer, ChainInfo> migrated = new HashMap<>(persistedChains);
        boolean changed = false;

        for (Map.Entry<Integer, Integer> mapping : migrationMap.entrySet()) {
            Integer deprecatedId = mapping.getKey();
            Integer targetId = mapping.getValue();
            if (!migrated.containsKey(deprecatedId)) {
                continue;
            }

            ChainInfo oldChain = migrated.get(deprecatedId);
            if (migrated.containsKey(targetId)) {
                migrated.remove(deprecatedId);
                changed = true;
                api.logging().logToOutput("Migrated deprecated chain ID " + deprecatedId + " -> " + targetId + " (kept existing target entry).");
                continue;
            }

            ChainInfo targetTemplate = resourceChains.get(targetId);
            ChainInfo migratedChain;
            if (targetTemplate != null) {
                migratedChain = new ChainInfo(
                        targetId,
                        targetTemplate.getName(),
                        targetTemplate.getExplorer(),
                        oldChain.getExplorerAPIKey()
                );
            } else {
                migratedChain = new ChainInfo(
                        targetId,
                        oldChain.getName(),
                        oldChain.getExplorer(),
                        oldChain.getExplorerAPIKey()
                );
            }

            migrated.remove(deprecatedId);
            migrated.put(targetId, migratedChain);
            changed = true;
            api.logging().logToOutput("Migrated deprecated chain ID " + deprecatedId + " -> " + targetId + ".");
        }

        if (changed) {
            api.logging().logToOutput("Deprecated chain migration applied.");
        }

        return migrated;
    }

    /**
     * Loads chains from the Preferences.
     *
     * @return A map of chainId to ChainInfo loaded from Preferences.
     */
    private Map<Integer, ChainInfo> loadChainsFromPreferences() {
        String serializedChains = preferences.getString(PREFS_KEY);
        if (serializedChains == null || serializedChains.isEmpty()) {
            api.logging().logToOutput("No chains found in Preferences.");
            return new HashMap<>();
        }

        try {
            TypeReference<HashMap<Integer, ChainInfo>> typeRef = new TypeReference<>() {};
            Map<Integer, ChainInfo> persistedChains = objectMapper.readValue(serializedChains, typeRef);
            api.logging().logToOutput("Loaded " + persistedChains.size() + " chains from Preferences.");
            return persistedChains;
        } catch (Exception e) {
            api.logging().logToError("Error deserializing chains from Preferences: " + e.getMessage());
            return new HashMap<>();
        }
    }

    /**
     * Loads the chains from the chains.json resource file.
     *
     * @return A map of chainId to ChainInfo loaded from resources.
     */
    private Map<Integer, ChainInfo> loadChainsFromResources() {
        Map<Integer, ChainInfo> resourceChains = new HashMap<>();
        try (InputStream inputStream = getClass().getClassLoader().getResourceAsStream("chains.json")) {
            if (inputStream == null) {
                throw new IllegalArgumentException("chains.json file not found in resources");
            }

            // Parse the JSON using ObjectMapper
            Map<String, Map<String, String>> jsonMap = objectMapper.readValue(inputStream, new TypeReference<>() {});
            for (Map.Entry<String, Map<String, String>> entry : jsonMap.entrySet()) {
                int chainId = Integer.parseInt(entry.getKey());
                Map<String, String> chainData = entry.getValue();
                String name = chainData.getOrDefault("name", "Unknown");
                String explorer = chainData.getOrDefault("explorer", "");
                // Initialize with empty API key; will be updated from Preferences if available
                ChainInfo chainInfo = new ChainInfo(chainId, name, explorer, "");
                resourceChains.put(chainId, chainInfo);
            }
            api.logging().logToOutput("Loaded " + resourceChains.size() + " chains from resources.");
        } catch (Exception e) {
            api.logging().logToError("Error loading chains.json: " + e.getMessage());
        }
        return resourceChains;
    }

    /**
     * Saves all chains to Preferences by serializing the chains map to a JSON string.
     */
    private void saveChains() {
        try {
            String serializedChains = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(chains);
            preferences.setString(PREFS_KEY, serializedChains);
            api.logging().logToOutput("Saved " + chains.size() + " chains to Preferences.");
        } catch (Exception e) {
            api.logging().logToError("Error serializing chains to Preferences: " + e.getMessage());
        }
    }

    /**
     * Adds or updates a ChainInfo in the persisted storage.
     *
     * @param chainId        The unique identifier for the chain.
     * @param name           The name of the chain.
     * @param explorer       The explorer URL.
     * @param explorerAPIKey The API key for the explorer (optional).
     */
    public void addOrUpdateChain(int chainId, String name, String explorer, String explorerAPIKey) {
        ChainInfo existingChain = chains.get(chainId);
        if (existingChain != null) {
            existingChain.setName(name);
            existingChain.setExplorer(explorer);
            if (explorerAPIKey != null && !explorerAPIKey.isEmpty()) {
                existingChain.setExplorerAPIKey(explorerAPIKey);
            }
            api.logging().logToOutput("Updated chain with ID " + chainId + ".");
        } else {
            String apiKeyToSet = explorerAPIKey != null ? explorerAPIKey : "";
            ChainInfo newChain = new ChainInfo(chainId, name, explorer, apiKeyToSet);
            chains.put(chainId, newChain);
            api.logging().logToOutput("Added new chain with ID " + chainId + ".");
        }
        saveChains();
    }

    public void updateChainDetails(int chainId, String name, String explorer) {
        ChainInfo existingChain = chains.get(chainId);
        if (existingChain == null) {
            api.logging().logToError("Failed to update chain details for chain ID " + chainId + ": chain not found.");
            return;
        }
        existingChain.setName(name);
        existingChain.setExplorer(explorer);
        saveChains();
        api.logging().logToOutput("Updated chain details for chain ID " + chainId + ".");
    }

    /**
     * Updates the explorerAPIKey for a specific chain.
     *
     * @param chainId        The unique identifier for the chain.
     * @param explorerAPIKey The new API key to set.
     */
    public void updateExplorerAPIKey(int chainId, String explorerAPIKey) {
        ChainInfo chain = chains.get(chainId);
        if (chain != null && explorerAPIKey != null) {
            chain.setExplorerAPIKey(explorerAPIKey);
            saveChains();
            api.logging().logToOutput("Updated explorerAPIKey for chain ID " + chainId + ".");
        } else {
            api.logging().logToError("Failed to update explorerAPIKey for chain ID " + chainId + ".");
        }
    }

    /**
     * Removes a chain from the persisted storage.
     *
     * @param chainId The unique identifier for the chain to remove.
     */
    public void removeChain(int chainId) {
        if (chains.remove(chainId) != null) {
            saveChains();
            api.logging().logToOutput("Removed chain with ID " + chainId + " from Preferences.");
        } else {
            api.logging().logToError("Attempted to remove non-existent chain with ID " + chainId + ".");
        }
    }

    /**
     * Retrieves a ChainInfo by its chainId.
     *
     * @param chainId The unique identifier for the chain.
     * @return The ChainInfo object or null if not found.
     */
    public ChainInfo getChain(int chainId) {
        return chains.get(chainId);
    }

    public String getSharedEtherscanApiKey() {
        return sharedEtherscanApiKey == null ? "" : sharedEtherscanApiKey;
    }

    public void setSharedEtherscanApiKey(String apiKey) {
        this.sharedEtherscanApiKey = apiKey == null ? "" : apiKey;
        preferences.setString(PREFS_SHARED_ETHERSCAN_KEY, this.sharedEtherscanApiKey);
        api.logging().logToOutput("Updated shared Etherscan API key.");
    }

    public boolean isHistoryAnnotationEnabled() {
        return historyAnnotationEnabled;
    }

    public void setHistoryAnnotationEnabled(boolean enabled) {
        this.historyAnnotationEnabled = enabled;
        preferences.setBoolean(PREFS_ANNOTATION_ENABLED, enabled);
        api.logging().logToOutput("History annotation " + (enabled ? "enabled" : "disabled") + ".");
    }

    public boolean isBlockExplorerLookupEnabled() {
        return blockExplorerLookupEnabled;
    }

    public void setBlockExplorerLookupEnabled(boolean enabled) {
        this.blockExplorerLookupEnabled = enabled;
        preferences.setBoolean(PREFS_BLOCK_EXPLORER_LOOKUP_ENABLED, enabled);
        api.logging().logToOutput("Block Explorer ABI lookup " + (enabled ? "enabled" : "disabled") + ".");
    }

    public boolean isFourByteLookupEnabled() {
        return fourByteLookupEnabled;
    }

    public void setFourByteLookupEnabled(boolean enabled) {
        this.fourByteLookupEnabled = enabled;
        preferences.setBoolean(PREFS_FOURBYTE_LOOKUP_ENABLED, enabled);
        api.logging().logToOutput("4byte selector lookup " + (enabled ? "enabled" : "disabled") + ".");
    }

    public String resolveExplorerAPIKey(ChainInfo chain) {
        if (chain == null) {
            return "";
        }

        String chainKey = chain.getExplorerAPIKey();
        if (chainKey != null && !chainKey.isEmpty()) {
            return chainKey;
        }

        if (isEtherscanFamilyExplorer(chain.getExplorer())) {
            return getSharedEtherscanApiKey();
        }

        return "";
    }

    public boolean isEtherscanFamilyExplorer(String explorerHost) {
        String host = explorerHost == null ? "" : explorerHost.trim().toLowerCase();
        return !host.isEmpty() && host.contains("etherscan");
    }

    /**
     * Retrieves all chains.
     *
     * @return A map of chainId to ChainInfo.
     */
    public Map<Integer, ChainInfo> getAllChains() {
        return new HashMap<>(chains);
    }
}
