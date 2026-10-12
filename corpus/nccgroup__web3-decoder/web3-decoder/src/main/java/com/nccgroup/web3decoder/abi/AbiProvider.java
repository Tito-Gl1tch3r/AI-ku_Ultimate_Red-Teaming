package com.nccgroup.web3decoder.abi;

import com.nccgroup.web3decoder.persistence.CachedAbis;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import burp.api.montoya.MontoyaApi;
import burp.api.montoya.logging.Logging;

/*
 * CachingAbiProvider is an implementation of AbiProvider that fetches the ABI from the cache if available,
 * using both EtherscanAbiProvider and CachedAbiProvider.
 */
public class AbiProvider implements IAbiProvider {

    private final IAbiProvider cachedAbiProvider;
    private final IAbiProvider builtinAbiProvider;
    private final EtherscanAbiProvider etherscanAbiProvider;
    private final CachedAbis cachedAbis;
    private final int chainId;
    private final Logging logging;
    private final String blockExplorer;
    private final ExtensionConfig config;
    private String lastAbiSource;
    private AbiLookupStatus lastLookupStatus = AbiLookupStatus.FOUND;
    private String lastLookupMessage = "";
    private boolean loggedNoExplorer = false;

    public AbiLookupStatus getLastLookupStatus() {
        return lastLookupStatus;
    }

    public String getLastLookupMessage() {
        return lastLookupMessage;
    }

    public AbiProvider(MontoyaApi api, int chainId, String blockExplorer, String apiKey) {
        this(api, chainId, blockExplorer, apiKey, null);
    }

    public AbiProvider(MontoyaApi api, int chainId, String blockExplorer, String apiKey,
                       ExtensionConfig config) {
        this.cachedAbis = new CachedAbis(api);
        this.chainId = chainId;
        this.logging = api.logging();
        this.blockExplorer = blockExplorer == null ? "" : blockExplorer.trim();
        this.config = config;
        this.cachedAbiProvider = new CachedAbiProvider(api, chainId);
        this.builtinAbiProvider = new BuiltinAbiProvider();
        this.etherscanAbiProvider = new EtherscanAbiProvider(api, chainId, blockExplorer, apiKey);
    }

    @Override
    public String getAbi(String contractAddress) throws Exception {
        lastAbiSource = null;
        lastLookupStatus = AbiLookupStatus.FOUND;
        lastLookupMessage = "";

        String cachedAbi = cachedAbiProvider.getAbi(contractAddress);
        if (cachedAbi != null) {
            lastAbiSource = "cache";
            return cachedAbi;
        }

        String builtinAbi = builtinAbiProvider.getAbi(contractAddress);
        if (builtinAbi != null) {
            lastAbiSource = "builtin";
            return builtinAbi;
        }

        if (blockExplorer.isEmpty()) {
            lastLookupStatus = AbiLookupStatus.NO_EXPLORER;
            lastLookupMessage = "No block explorer configured for chain " + chainId;
            if (!loggedNoExplorer) {
                logging.logToOutput(lastLookupMessage + ". Explorer ABI fetch skipped.");
                loggedNoExplorer = true;
            }
            return null;
        }

        if (config != null && !config.isBlockExplorerLookupEnabled()) {
            lastLookupStatus = AbiLookupStatus.NO_EXPLORER;
            lastLookupMessage = "Block Explorer ABI lookup disabled in Web3 → Settings.";
            return null;
        }

        String etherscanAbi = etherscanAbiProvider.getAbi(contractAddress);
        lastLookupStatus = etherscanAbiProvider.getLastStatus();
        lastLookupMessage = humanMessage(etherscanAbiProvider.getLastStatus(), etherscanAbiProvider.getLastMessage());
        if (etherscanAbi != null) {
            cachedAbis.saveAbi(chainId, contractAddress, etherscanAbi);
            lastAbiSource = "etherscan";
            lastLookupStatus = AbiLookupStatus.FOUND;
            logging.logToOutput("ABI fetched from Etherscan and cached for contract: " + contractAddress);
            return etherscanAbi;
        }
        logging.logToOutput("ABI not found for contract: " + contractAddress + " (" + lastLookupMessage + ")");
        return null;
    }

    /** Turns a raw explorer status/message into an analyst-facing sentence. */
    private String humanMessage(AbiLookupStatus status, String raw) {
        return switch (status) {
            case MISSING_API_KEY -> "Etherscan API key not set for chain " + chainId
                    + " — add it under the \"Web3\" tab → Chains.";
            case RATE_LIMITED -> "Rate limited by Etherscan for chain " + chainId + "; try again shortly.";
            case NOT_VERIFIED -> "Contract source is not verified on the explorer for chain " + chainId + ".";
            case UNSUPPORTED_CHAIN -> "The explorer does not support chain " + chainId + ".";
            case NO_EXPLORER -> "No block explorer configured for chain " + chainId + ".";
            case HTTP_ERROR -> "Explorer returned an HTTP error for chain " + chainId + " (" + raw + ").";
            case FOUND -> "";
            default -> (raw == null || raw.isBlank()) ? "ABI lookup failed for chain " + chainId + "." : raw;
        };
    }

    public String getLastAbiSource() {
        return lastAbiSource;
    }
}
