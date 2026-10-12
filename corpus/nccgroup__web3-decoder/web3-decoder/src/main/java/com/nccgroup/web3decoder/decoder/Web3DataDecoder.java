// File: InputDataDecoder.java
package com.nccgroup.web3decoder.decoder;

import com.nccgroup.web3decoder.abi.AbiProvider;
import com.nccgroup.web3decoder.abi.FourByteSignatureProvider;
import com.nccgroup.web3decoder.detection.DetectedAbi;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import com.nccgroup.web3decoder.proxies.ProxyDetector;

import burp.api.montoya.logging.Logging;

import java.util.Map;

public class Web3DataDecoder {

    private final ProxyDetector proxyDetector;
    private final AbiProvider abiProvider;
    private final FourByteSignatureProvider fourByteSignatureProvider;
    private final DetectedAbiStore detectedAbiStore;
    private final ExtensionConfig config;
    private String lastAbiJson;
    private final Logging logging;

    public Web3DataDecoder(ProxyDetector proxyDetector, AbiProvider abiProvider, Logging logging) {
        this(proxyDetector, abiProvider, logging, null, null, null);
    }

    public Web3DataDecoder(ProxyDetector proxyDetector, AbiProvider abiProvider, Logging logging, FourByteSignatureProvider fourByteSignatureProvider) {
        this(proxyDetector, abiProvider, logging, fourByteSignatureProvider, null, null);
    }

    public Web3DataDecoder(ProxyDetector proxyDetector,
                           AbiProvider abiProvider,
                           Logging logging,
                           FourByteSignatureProvider fourByteSignatureProvider,
                           DetectedAbiStore detectedAbiStore) {
        this(proxyDetector, abiProvider, logging, fourByteSignatureProvider, detectedAbiStore, null);
    }

    public Web3DataDecoder(ProxyDetector proxyDetector,
                           AbiProvider abiProvider,
                           Logging logging,
                           FourByteSignatureProvider fourByteSignatureProvider,
                           DetectedAbiStore detectedAbiStore,
                           ExtensionConfig config) {
        this.proxyDetector = proxyDetector;
        this.abiProvider = abiProvider;
        this.logging = logging;
        this.fourByteSignatureProvider = fourByteSignatureProvider;
        this.detectedAbiStore = detectedAbiStore;
        this.config = config;
    }

    /**
     * Decodes the input data for a given contract address.
     * If the contract is a proxy, it retrieves the implementation address and ABI.
     *
     * @param contractAddress The address of the contract.
     * @param inputData       The input data to decode.
     * @return A map containing the decoded function name and arguments.
     * @throws Exception If an error occurs during decoding.
     */
    public Map<String, Object> decodeInput(String contractAddress, String inputData) throws Exception {
        // Attempt to get the implementation address via ProxyDetector
        String implementationAddress = proxyDetector == null
                ? null : proxyDetector.getImplementationAddress(contractAddress);
        boolean proxyDetected = implementationAddress != null;
        String decodedUsingAddress = contractAddress;
        String decodeSource = null;
        String abiJson = null;

        // The AbiProvider chain (cache → builtin → etherscan) is chain-scoped. If
        // no chain context is available (e.g. eth_chainId probe failed), the caller
        // passes null and we skip straight to the chain-agnostic fallbacks below
        // (detected pool + 4byte).
        if (abiProvider != null) {
            if (proxyDetected) {
                // Prefer the implementation contract ABI when a proxy is detected.
                String abi = abiProvider.getAbi(implementationAddress);
                if (abi != null) {
                    abiJson = abi;
                    decodeSource = abiProvider.getLastAbiSource();
                    decodedUsingAddress = implementationAddress;
                } else {
                    // Fall back to an ABI stored against the proxy address itself —
                    // users commonly cache ABIs under the address they see in the
                    // calldata, not the resolved implementation.
                    abi = abiProvider.getAbi(contractAddress);
                    if (abi != null) {
                        abiJson = abi;
                        decodeSource = abiProvider.getLastAbiSource();
                        decodedUsingAddress = contractAddress;
                        proxyDetected = false;
                    }
                }
            } else {
                // Fetch the ABI for the original contract
                String abi = abiProvider.getAbi(contractAddress);
                if (abi != null) {
                    abiJson = abi;
                    decodeSource = abiProvider.getLastAbiSource();
                }
            }
        }

        Map<String, Object> decoded = null;
        if (abiJson != null) {
            lastAbiJson = abiJson;
            decoded = ABIInputDecoder.decodeInput(lastAbiJson, inputData);
        }

        // Detected-ABI pool fallback: consulted between the provider and 4byte.
        if (decoded == null && detectedAbiStore != null
                && inputData != null && inputData.length() >= 10) {
            String selector = inputData.substring(0, 10).toLowerCase();
            for (DetectedAbi candidate : detectedAbiStore.findBySelector(selector)) {
                try {
                    decoded = ABIInputDecoder.decodeInput(candidate.canonicalJson(), inputData);
                    lastAbiJson = candidate.canonicalJson();
                    decodeSource = "detected";
                    break;
                } catch (Exception ignored) {
                    // try next candidate
                }
            }
        }

        if (decoded == null) {
            String lookupNote = abiProvider == null ? "" : abiProvider.getLastLookupMessage();
            if (lookupNote != null && !lookupNote.isBlank()) {
                logging.logToError("ABI unavailable for " + contractAddress + ": " + lookupNote);
            }
            boolean fourByteAllowed = fourByteSignatureProvider != null
                    && (config == null || config.isFourByteLookupEnabled());
            if (!fourByteAllowed) {
                String reason = lookupNote;
                if (fourByteSignatureProvider != null && config != null && !config.isFourByteLookupEnabled()) {
                    reason = appendReason(reason, "4byte selector lookup disabled in Web3 → Settings.");
                }
                String base = proxyDetected
                        ? "Failed to retrieve ABI for implementation contract at " + implementationAddress
                                + " (proxy target " + contractAddress + ")"
                        : "Failed to retrieve ABI for contract at " + contractAddress;
                throw new Exception(appendReason(base, reason));
            }
            try {
                FourByteDecode fourByteDecode = decodeWithFourByte(inputData);
                decoded = fourByteDecode.decoded;
                lastAbiJson = fourByteDecode.syntheticAbiJson;
                decodeSource = "4byte";
                if (lookupNote != null && !lookupNote.isBlank()) {
                    decoded.put("abiLookupNote", lookupNote);
                }
            } catch (Exception fourByteFailure) {
                String attempted = proxyDetected
                        ? ("implementation " + implementationAddress + " (proxy target " + contractAddress + ")")
                        : contractAddress;
                String base = "ABI lookup failed for " + attempted + "; " + fourByteFailure.getMessage();
                throw new Exception(appendReason(base, lookupNote));
            }
        }

        decoded.put("isProxy", proxyDetected);
        decoded.put("proxyTarget", contractAddress);
        decoded.put("decodedUsing", decodedUsingAddress);
        if (decodeSource != null) {
            decoded.put("decodeSource", decodeSource);
        }
        if (proxyDetected) {
            decoded.put("implementationAddress", implementationAddress);
        }
        return decoded;
    }

    private static String appendReason(String base, String reason) {
        if (reason == null || reason.isBlank()) {
            return base;
        }
        return base + " — " + reason;
    }

    private FourByteDecode decodeWithFourByte(String inputData) throws Exception {
        if (inputData == null || inputData.length() < 10 || !inputData.startsWith("0x")) {
            throw new IllegalArgumentException("Input data must start with 0x and include a 4-byte selector.");
        }

        String selector = inputData.substring(0, 10).toLowerCase();
        java.util.List<String> candidates = fourByteSignatureProvider.lookupFunctionSignatures(selector);
        if (candidates.isEmpty()) {
            throw new Exception("ABI not found and no 4byte signatures found for selector " + selector + ".");
        }

        Exception lastException = null;
        for (String signature : candidates) {
            try {
                String syntheticAbi = fourByteSignatureProvider.buildSyntheticAbiFromSignature(signature);
                Map<String, Object> decoded = ABIInputDecoder.decodeInput(syntheticAbi, inputData);
                return new FourByteDecode(decoded, syntheticAbi);
            } catch (Exception e) {
                lastException = e;
            }
        }

        if (lastException != null) {
            throw new Exception("Failed to decode selector " + selector + " using 4byte candidates: " + lastException.getMessage());
        }
        throw new Exception("Failed to decode selector " + selector + " using 4byte candidates.");
    }

    public Map<String, Object> decodeOutput(String functionSignature, String outputData) throws Exception {
        if (lastAbiJson == null) {
            throw new Exception("No ABI JSON available for decoding output.");
        }
        return ABIInputDecoder.decodeOutput(lastAbiJson, functionSignature, outputData);
    }

    public String getLastAbi() {
        return lastAbiJson;
    }

    public void setLastAbiJson(String abiJson) {
        this.lastAbiJson = abiJson;
    }

    private static final class FourByteDecode {
        private final Map<String, Object> decoded;
        private final String syntheticAbiJson;

        private FourByteDecode(Map<String, Object> decoded, String syntheticAbiJson) {
            this.decoded = decoded;
            this.syntheticAbiJson = syntheticAbiJson;
        }
    }
}
