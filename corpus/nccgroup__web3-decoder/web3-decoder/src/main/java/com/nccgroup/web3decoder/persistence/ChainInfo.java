package com.nccgroup.web3decoder.persistence;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Represents the information of a blockchain chain.
 */
public class ChainInfo {
    @JsonProperty("chainId")
    private int chainId;

    @JsonProperty("name")
    private String name;

    @JsonProperty("explorer")
    private String explorer;

    @JsonProperty("explorerAPIKey")
    private String explorerAPIKey;

    /**
     * Default constructor for Jackson.
     */
    public ChainInfo() {
        // Default constructor needed for Jackson
    }

    /**
     * Constructs a ChainInfo instance.
     *
     * @param chainId        The unique identifier for the chain.
     * @param name           The name of the chain.
     * @param explorer       The explorer URL.
     * @param explorerAPIKey The API key for the explorer.
     */
    public ChainInfo(int chainId, String name, String explorer, String explorerAPIKey) {
        this.chainId = chainId;
        this.name = name == null ? "" : name;
        this.explorer = explorer == null ? "" : explorer;
        this.explorerAPIKey = explorerAPIKey == null ? "" : explorerAPIKey;
    }

    // Getters
    public int getChainId() { return chainId; }
    public String getName() { return name == null ? "" : name; }
    public String getExplorer() { return explorer == null ? "" : explorer; }
    public String getExplorerAPIKey() { return explorerAPIKey == null ? "" : explorerAPIKey; }

    // Setters
    public void setChainId(int chainId) { this.chainId = chainId; }
    public void setName(String name) { this.name = name == null ? "" : name; }
    public void setExplorer(String explorer) { this.explorer = explorer == null ? "" : explorer; }
    public void setExplorerAPIKey(String explorerAPIKey) { this.explorerAPIKey = explorerAPIKey == null ? "" : explorerAPIKey; }

    @Override
    public String toString() {
        return "ChainInfo{" +
                "chainId=" + chainId +
                ", name='" + name + '\'' +
                ", explorer='" + explorer + '\'' +
                ", explorerAPIKey='" + (explorerAPIKey == null || explorerAPIKey.isEmpty() ? "None" : "Set") + '\'' +
                '}';
    }
}
