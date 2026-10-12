package com.nccgroup.web3decoder.abi;

import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;
import burp.api.montoya.logging.Logging;
import burp.api.montoya.http.HttpService;
import burp.api.montoya.MontoyaApi;

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import com.nccgroup.web3decoder.abi.EtherscanResponseClassifier.Classification;

import java.util.HashMap;
import java.util.Map;

public class EtherscanAbiProvider implements IAbiProvider {

    private static final String ETHERSCAN_V2_HOST = "api.etherscan.io";
    private static final String ETHERSCAN_V2_ABI_PATH = "/v2/api";

    private static final Map<Integer, Boolean> chainIdSupportCache = new HashMap<>();

    private final MontoyaApi api;
    private final Logging logging;
    private final String apiKey;
    private final int chainId;
    private final String blockExplorer;

    private static final int MAX_RETRIES = 2;          // few quick retries
    private static final long RETRY_WAIT_MILLIS = 1000; // ~1s fixed wait

    private AbiLookupStatus lastStatus = AbiLookupStatus.ERROR;
    private String lastMessage = "";

    public AbiLookupStatus getLastStatus() {
        return lastStatus;
    }

    public String getLastMessage() {
        return lastMessage;
    }

    /**
     * Constructs the EtherscanAbiProvider with necessary configurations.
     *
     * @param api           The Montoya API instance.
     * @param chainId       Chain ID used by Etherscan v2 `chainid` parameter.
     * @param blockExplorer The block explorer's hostname (e.g., etherscan.io).
     * @param apiKey        The API key for accessing the block explorer.
     */
    public EtherscanAbiProvider(MontoyaApi api, int chainId, String blockExplorer, String apiKey) {
        this.api = api;
        this.logging = api.logging();
        this.apiKey = apiKey;
        this.chainId = chainId;
        this.blockExplorer = blockExplorer;
    }

    @Override
    public String getAbi(String contractAddress) {
        // The Etherscan v2 path requires a key; if it is blank, report it without
        // spending a call against the (shared, 5/sec) free-tier budget.
        if (apiKey == null || apiKey.isBlank()) {
            lastStatus = AbiLookupStatus.MISSING_API_KEY;
            lastMessage = "Etherscan API key not set for chain " + chainId;
            logging.logToOutput("Skipping Etherscan lookup for " + contractAddress
                    + ": no API key configured for chain " + chainId + ".");
            return null;
        }
        try {
            String abi = getAbiFromV2(contractAddress);
            if (abi != null) {
                return abi;
            }
            return getAbiFromLegacyExplorer(contractAddress);
        } catch (Exception e) {
            lastStatus = AbiLookupStatus.ERROR;
            lastMessage = "Explorer lookup error: " + e.getMessage();
            logging.logToError("Exception while fetching ABI from explorer for contract: " + contractAddress + ". Error: " + e.getMessage());
            return null;
        }
    }

    private String getAbiFromV2(String contractAddress) {
        if (!isV2SupportedChain(chainId)) {
            lastStatus = AbiLookupStatus.UNSUPPORTED_CHAIN;
            lastMessage = "Etherscan v2 does not support chain ID " + chainId;
            logging.logToOutput(lastMessage + ". Falling back to configured explorer host.");
            return null;
        }

        String url = String.format(
                "%s?chainid=%d&module=contract&action=getabi&address=%s&apikey=%s",
                ETHERSCAN_V2_ABI_PATH, chainId, contractAddress, apiKey);
        HttpService service = HttpService.httpService("https://" + ETHERSCAN_V2_HOST);

        Classification c = classifyWithRetry(service, url);
        lastStatus = c.status();
        lastMessage = c.message();

        switch (c.status()) {
            case FOUND:
                logging.logToOutput("ABI fetched from Etherscan v2 for contract: " + contractAddress + " (chainId " + chainId + ")");
                return c.abi();
            case UNSUPPORTED_CHAIN:
                synchronized (chainIdSupportCache) {
                    chainIdSupportCache.put(chainId, false);
                }
                logging.logToOutput("Etherscan v2 reported unsupported chain ID " + chainId + ". Falling back to configured explorer host.");
                return null;
            case RATE_LIMITED:
                logging.logToError("Etherscan v2 rate limited for contract " + contractAddress + " (chainId " + chainId + ") after retries.");
                return null;
            default:
                logging.logToOutput("ABI not resolved on Etherscan v2 for contract: " + contractAddress
                        + " (chainId " + chainId + "): " + c.message());
                return null;
        }
    }

    /** Sends the GET through the rate limiter, retrying a couple of times if rate limited. */
    private Classification classifyWithRetry(HttpService service, String pathAndQuery) {
        Classification last = null;
        for (int attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                EtherscanRateLimiter.getInstance().acquire();
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                return new Classification(AbiLookupStatus.ERROR, null, "Interrupted while waiting for rate limiter");
            }

            HttpRequest request = HttpRequest.httpRequest(
                    service, "GET " + pathAndQuery + " HTTP/1.1\r\nHost: " + service.host() + "\r\n\r\n");
            HttpResponse response = api.http().sendRequest(request).response();
            last = EtherscanResponseClassifier.classify(response.statusCode(), response.bodyToString());

            if (last.status() != AbiLookupStatus.RATE_LIMITED) {
                return last;
            }
            if (attempt < MAX_RETRIES) {
                try {
                    Thread.sleep(RETRY_WAIT_MILLIS);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return last;
                }
            }
        }
        return last;
    }

    private String getAbiFromLegacyExplorer(String contractAddress) {
        String url = String.format("/api?module=contract&action=getabi&address=%s&apikey=%s", contractAddress, apiKey);
        HttpService service = HttpService.httpService("https://" + blockExplorer);

        Classification c = classifyWithRetry(service, url);
        lastStatus = c.status();
        lastMessage = c.message();

        if (c.status() == AbiLookupStatus.FOUND) {
            logging.logToOutput("ABI fetched from legacy explorer endpoint for contract: " + contractAddress + " via " + blockExplorer);
            return c.abi();
        }
        logging.logToOutput("ABI not resolved on legacy explorer for contract: " + contractAddress
                + " via " + blockExplorer + ": " + c.message());
        return null;
    }

    private JSONObject executeGet(HttpService service, String pathAndQuery) {
        try {
            EtherscanRateLimiter.getInstance().acquire();
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            logging.logToError("Interrupted while waiting for Etherscan rate limiter on " + service.host() + pathAndQuery);
            return null;
        }

        HttpRequest request = HttpRequest.httpRequest(
                service,
                "GET " + pathAndQuery + " HTTP/1.1\r\nHost: " + service.host() + "\r\n\r\n"
        );

        HttpRequestResponse requestResponse = api.http().sendRequest(request);
        HttpResponse response = requestResponse.response();

        if (response.statusCode() != 200) {
            logging.logToError("Failed to fetch ABI from " + service.host() + ". HTTP Status: " + response.statusCode());
            return null;
        }

        return new JSONObject(new JSONTokener(response.bodyToString()));
    }

    private boolean isV2SupportedChain(int chainId) {
        synchronized (chainIdSupportCache) {
            Boolean cached = chainIdSupportCache.get(chainId);
            if (cached != null) {
                return cached;
            }
        }

        try {
            HttpService service = HttpService.httpService("https://" + ETHERSCAN_V2_HOST);
            JSONObject response = executeGet(service, "/v2/chainlist");
            if (response == null) {
                return false;
            }

            JSONArray chains = response.optJSONArray("result");
            if (chains == null) {
                return false;
            }

            boolean supported = false;
            for (int i = 0; i < chains.length(); i++) {
                JSONObject chain = chains.getJSONObject(i);
                if (String.valueOf(chainId).equals(chain.optString("chainid")) && chain.optInt("status", 0) == 1) {
                    supported = true;
                    break;
                }
            }

            synchronized (chainIdSupportCache) {
                chainIdSupportCache.put(chainId, supported);
            }
            return supported;
        } catch (Exception e) {
            logging.logToError("Unable to query Etherscan v2 chain list. Falling back to legacy explorer. Error: " + e.getMessage());
            return false;
        }
    }
}
