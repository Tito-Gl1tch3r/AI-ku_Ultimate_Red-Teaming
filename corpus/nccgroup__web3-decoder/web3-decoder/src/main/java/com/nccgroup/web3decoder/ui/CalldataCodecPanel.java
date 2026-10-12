package com.nccgroup.web3decoder.ui;

import burp.api.montoya.MontoyaApi;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.ObjectWriter;
import com.nccgroup.web3decoder.ui.editor.Web3JsonEditor;
import com.nccgroup.web3decoder.abi.AbiProvider;
import com.nccgroup.web3decoder.decoder.ABIInputDecoder;
import com.nccgroup.web3decoder.abi.FourByteSignatureProvider;
import com.nccgroup.web3decoder.decoder.MulticallRecursiveDecoder;
import com.nccgroup.web3decoder.decoder.Web3DataDecoder;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.CachedAbis;
import com.nccgroup.web3decoder.persistence.ChainInfo;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import com.nccgroup.web3decoder.proxies.ProxyDetector;

import javax.swing.*;
import java.awt.*;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public class CalldataCodecPanel extends JPanel {
    private static final Pattern CONTRACT_ADDRESS_PATTERN = Pattern.compile("^0x[0-9a-fA-F]{40}$");
    private static final int MULTICALL_MAX_DEPTH = 3;

    private final MontoyaApi api;
    private final ExtensionConfig config;
    private final CachedAbis cachedAbis;
    private final ObjectMapper objectMapper;
    private final FourByteSignatureProvider fourByteSignatureProvider;
    private final DetectedAbiStore detectedAbiStore;

    private final JTextField chainIdField;
    private final JTextField contractAddressField;
    private final JTextField rpcUrlField;
    private final Web3JsonEditor calldataEditor;
    private final Web3JsonEditor decodedEditor;
    private final JButton decodeButton;
    private final JButton reencodeButton;

    private int selectedChainId = -1;
    private String selectedContractAddress = null;
    private String selectedAbi = null;
    private String lastDecodedAbiJson = null;

    public CalldataCodecPanel(MontoyaApi api, ExtensionConfig config, CachedAbis cachedAbis) {
        this(api, config, cachedAbis, null);
    }

    public CalldataCodecPanel(MontoyaApi api, ExtensionConfig config, CachedAbis cachedAbis,
                              DetectedAbiStore detectedAbiStore) {
        this.api = api;
        this.config = config;
        this.cachedAbis = cachedAbis;
        this.objectMapper = new ObjectMapper();
        this.fourByteSignatureProvider = new FourByteSignatureProvider(api);
        this.detectedAbiStore = detectedAbiStore;
        this.chainIdField = new JTextField();
        this.contractAddressField = new JTextField();
        this.rpcUrlField = new JTextField();
        this.calldataEditor = new Web3JsonEditor(true, api.logging());
        this.decodedEditor = new Web3JsonEditor(true, api.logging());
        this.decodeButton = new JButton("Decode");
        this.reencodeButton = new JButton("Re-encode");

        initializeUI();
    }

    public void setContext(int chainId, String contractAddress, String abiJson) {
        if (chainId == -1 || contractAddress == null || contractAddress.isEmpty()) {
            selectedChainId = -1;
            selectedContractAddress = null;
            selectedAbi = null;
            return;
        }

        selectedChainId = chainId;
        selectedContractAddress = contractAddress.toLowerCase();
        selectedAbi = abiJson;

        chainIdField.setText(String.valueOf(chainId));
        contractAddressField.setText(selectedContractAddress);
    }

    private void initializeUI() {
        setLayout(new BorderLayout(8, 8));

        JPanel topControls = new JPanel(new BorderLayout(0, 4));
        JPanel fieldsPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(2, 4, 2, 4);
        gbc.anchor = GridBagConstraints.WEST;
        gbc.fill = GridBagConstraints.HORIZONTAL;

        JLabel chainIdLabel = new JLabel("Chain ID:");
        chainIdField.setColumns(6);
        JLabel contractLabel = new JLabel("Contract:");
        contractAddressField.setColumns(26);
        JLabel rpcUrlLabel = new JLabel("RPC URL:");
        rpcUrlField.setColumns(24);
        rpcUrlField.setToolTipText("JSON-RPC endpoint used for proxy detection (optional but recommended).");

        decodeButton.addActionListener(e -> decodeCalldata());
        reencodeButton.addActionListener(e -> reencodeCalldata());

        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.weightx = 0.0;
        fieldsPanel.add(chainIdLabel, gbc);

        gbc.gridx = 1;
        gbc.weightx = 0.0;
        fieldsPanel.add(chainIdField, gbc);

        gbc.gridx = 2;
        gbc.weightx = 0.0;
        fieldsPanel.add(contractLabel, gbc);

        gbc.gridx = 3;
        gbc.weightx = 0.45;
        fieldsPanel.add(contractAddressField, gbc);

        gbc.gridx = 4;
        gbc.weightx = 0.0;
        fieldsPanel.add(rpcUrlLabel, gbc);

        gbc.gridx = 5;
        gbc.weightx = 0.55;
        fieldsPanel.add(rpcUrlField, gbc);

        JPanel buttonsPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 8, 0));
        buttonsPanel.add(decodeButton);
        buttonsPanel.add(reencodeButton);

        topControls.add(fieldsPanel, BorderLayout.CENTER);
        topControls.add(buttonsPanel, BorderLayout.SOUTH);

        add(topControls, BorderLayout.NORTH);

        JPanel editorsPanel = new JPanel(new GridLayout(1, 2, 8, 0));
        editorsPanel.add(createEditorWithLabel("Encoded Calldata", calldataEditor.getComponent()));
        editorsPanel.add(createEditorWithLabel("Decoded JSON", decodedEditor.getComponent()));
        add(editorsPanel, BorderLayout.CENTER);
    }

    private JPanel createEditorWithLabel(String labelText, Component editorComponent) {
        JPanel panel = new JPanel(new BorderLayout(4, 4));
        JLabel label = new JLabel(labelText);
        label.setFont(label.getFont().deriveFont(Font.BOLD));
        panel.add(label, BorderLayout.NORTH);
        panel.add(editorComponent, BorderLayout.CENTER);
        return panel;
    }

    private void decodeCalldata() {
        try {
            InputContext input = parseAndValidateInputContext();
            String calldata = readEditorContents(calldataEditor).trim();
            validateCalldata(calldata);
            DecodeResult decodeResult = decodeLikeRequestEditor(input, calldata);
            lastDecodedAbiJson = decodeResult.abiJsonUsed;
            decodedEditor.setText(prettyJson(decodeResult.output));
        } catch (Exception e) {
            api.logging().logToError("Calldata decode failed: " + e.getMessage());
            JOptionPane.showMessageDialog(this, "Decode failed: " + e.getMessage(), "Decode Error", JOptionPane.ERROR_MESSAGE);
        }
    }

    private void reencodeCalldata() {
        try {
            String decodedJson = readEditorContents(decodedEditor).trim();
            if (decodedJson.isEmpty()) {
                throw new IllegalArgumentException("Decoded JSON editor is empty.");
            }

            Map<String, Object> parsed = objectMapper.readValue(decodedJson, new TypeReference<Map<String, Object>>() {});
            Object functionObj = parsed.get("function");
            Object argsObj = parsed.get("args");
            if (!(functionObj instanceof String)) {
                throw new IllegalArgumentException("Decoded JSON must contain a string 'function' field.");
            }
            String functionSignature = (String) functionObj;
            if (!(argsObj instanceof Map<?, ?>)) {
                throw new IllegalArgumentException("Decoded JSON must contain an object 'args' field.");
            }
            Map<?, ?> rawArgs = (Map<?, ?>) argsObj;
            Map<String, Object> args = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : rawArgs.entrySet()) {
                if (entry.getKey() == null) {
                    continue;
                }
                args.put(entry.getKey().toString(), entry.getValue());
            }

            String abiJson = lastDecodedAbiJson;
            if (abiJson == null || abiJson.isBlank()) {
                InputContext input = parseAndValidateInputContext();
                AbiContext abiContext = resolveAbiForContract(input.chainId, input.contractAddress);
                abiJson = abiContext.abiJson;
            }

            String reencoded = ABIInputDecoder.encodeInput(abiJson, functionSignature, args);
            calldataEditor.setText(reencoded);
        } catch (Exception e) {
            api.logging().logToError("Calldata re-encode failed: " + e.getMessage());
            JOptionPane.showMessageDialog(this, "Re-encode failed: " + e.getMessage(), "Re-encode Error", JOptionPane.ERROR_MESSAGE);
        }
    }

    private InputContext parseAndValidateInputContext() {
        String chainIdText = chainIdField.getText().trim();
        String contractAddressInput = contractAddressField.getText().trim().toLowerCase();
        String rpcUrlInput = rpcUrlField.getText().trim();

        if (chainIdText.isEmpty()) {
            throw new IllegalArgumentException("Chain ID is required.");
        }
        if (contractAddressInput.isEmpty()) {
            throw new IllegalArgumentException("Contract address is required.");
        }

        int chainId;
        try {
            chainId = Integer.parseInt(chainIdText);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Chain ID must be a decimal integer.");
        }

        validateContractAddress(contractAddressInput);
        if (!rpcUrlInput.isEmpty() && !(rpcUrlInput.startsWith("http://") || rpcUrlInput.startsWith("https://"))) {
            throw new IllegalArgumentException("RPC URL must start with http:// or https://");
        }

        return new InputContext(chainId, contractAddressInput, rpcUrlInput);
    }

    private DecodeResult decodeLikeRequestEditor(InputContext input, String calldata) throws Exception {
        ChainInfo chain = config.getChain(input.chainId);
        Map<String, String> nestedAbiCache = new HashMap<>();

        Map<String, Object> decodedData;
        String abiUsed = null;
        if (!input.rpcUrl.isEmpty() && chain != null) {
            AbiProvider abiProvider = new AbiProvider(api, input.chainId, chain.getExplorer(), config.resolveExplorerAPIKey(chain), config);
            ProxyDetector proxyDetector = new ProxyDetector(api, input.rpcUrl);
            Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, api.logging(), fourByteSignatureProvider, detectedAbiStore, config);
            decodedData = decoder.decodeInput(input.contractAddress, calldata);
            abiUsed = decoder.getLastAbi();
            if (abiUsed != null) {
                nestedAbiCache.put(input.contractAddress, abiUsed);
            }
        } else {
            DecodeFallbackResult localDecode = decodeWithoutProxyFallback(input.chainId, input.contractAddress, calldata);
            decodedData = localDecode.decoded;
            abiUsed = localDecode.abiJson;
            decodedData.put("isProxy", false);
            decodedData.put("proxyTarget", input.contractAddress);
            decodedData.put("decodedUsing", input.contractAddress);
            if (abiUsed != null) {
                nestedAbiCache.put(input.contractAddress, abiUsed);
            }
        }

        String function = (String) decodedData.get("function");
        @SuppressWarnings("unchecked")
        Map<String, Object> args = (Map<String, Object>) decodedData.get("args");

        Map<String, Object> output = new LinkedHashMap<>();
        output.put("chainId", input.chainId);
        output.put("to", input.contractAddress);
        output.put("function", function);
        output.put("args", args);
        if (decodedData.get("decodeSource") != null) {
            output.put("decodeSource", decodedData.get("decodeSource"));
        }

        if (Boolean.TRUE.equals(decodedData.get("isProxy"))) {
            Map<String, Object> proxyInfo = new LinkedHashMap<>();
            proxyInfo.put("isProxy", true);
            proxyInfo.put("proxyTarget", decodedData.get("proxyTarget"));
            proxyInfo.put("implementationAddress", decodedData.get("implementationAddress"));
            proxyInfo.put("decodedUsing", decodedData.get("decodedUsing"));
            output.put("proxy", proxyInfo);
        }

        if (function != null && args != null) {
            List<Map<String, Object>> nestedCalls = MulticallRecursiveDecoder.decodeNestedCalls(
                    input.contractAddress,
                    function,
                    args,
                    MULTICALL_MAX_DEPTH,
                    (target, callData) -> decodeTargetForNested(input, chain, target, callData, nestedAbiCache)
            );
            if (!nestedCalls.isEmpty()) {
                output.put("nestedCalls", nestedCalls);
            }
        }

        return new DecodeResult(output, abiUsed);
    }

    private Map<String, Object> decodeTargetForNested(
            InputContext input,
            ChainInfo chain,
            String target,
            String callData,
            Map<String, String> nestedAbiCache
    ) throws Exception {
        String normalizedTarget = target == null ? "" : target.toLowerCase();
        if (normalizedTarget.isEmpty()) {
            throw new IllegalArgumentException("Missing nested target.");
        }
        validateContractAddress(normalizedTarget);
        validateCalldata(callData);

        if (!input.rpcUrl.isEmpty() && chain != null) {
            AbiProvider abiProvider = new AbiProvider(api, input.chainId, chain.getExplorer(), config.resolveExplorerAPIKey(chain), config);
            ProxyDetector proxyDetector = new ProxyDetector(api, input.rpcUrl);
            Web3DataDecoder decoder = new Web3DataDecoder(proxyDetector, abiProvider, api.logging(), fourByteSignatureProvider, detectedAbiStore, config);
            return decoder.decodeInput(normalizedTarget, callData);
        }

        DecodeFallbackResult fallback = decodeWithoutProxyFallback(input.chainId, normalizedTarget, callData);
        if (fallback.abiJson != null && !fallback.abiJson.isBlank()) {
            nestedAbiCache.put(normalizedTarget, fallback.abiJson);
        }
        return fallback.decoded;
    }

    private AbiContext resolveAbiForContract(int chainId, String contractAddressInput) throws Exception {
        if (selectedChainId == chainId
                && contractAddressInput.equals(selectedContractAddress)
                && selectedAbi != null
                && !selectedAbi.isBlank()) {
            return new AbiContext(chainId, contractAddressInput, selectedAbi, "cache");
        }

        String cachedAbi = cachedAbis.getAbi(chainId, contractAddressInput);
        if (cachedAbi != null && !cachedAbi.isBlank()) {
            return new AbiContext(chainId, contractAddressInput, cachedAbi, "cache");
        }

        ChainInfo chain = config.getChain(chainId);
        if (chain == null) {
            throw new IllegalArgumentException("Chain ID " + chainId + " is not configured; explorer fallback is unavailable.");
        }

        AbiProvider abiProvider = new AbiProvider(api, chainId, chain.getExplorer(), config.resolveExplorerAPIKey(chain), config);
        String explorerAbi = abiProvider.getAbi(contractAddressInput);
        if (explorerAbi == null || explorerAbi.isBlank()) {
            throw new IllegalArgumentException("ABI not found for contract " + contractAddressInput + " on chain ID " + chainId + ".");
        }

        return new AbiContext(chainId, contractAddressInput, explorerAbi, "etherscan");
    }

    private DecodeFallbackResult decodeWithoutProxyFallback(int chainId, String contractAddress, String calldata) throws Exception {
        try {
            AbiContext abiContext = resolveAbiForContract(chainId, contractAddress);
            Map<String, Object> decoded = ABIInputDecoder.decodeInput(abiContext.abiJson, calldata);
            decoded.put("decodeSource", abiContext.abiSource);
            return new DecodeFallbackResult(decoded, abiContext.abiJson);
        } catch (Exception abiFailure) {
            if (calldata == null || calldata.length() < 10 || !calldata.startsWith("0x")) {
                throw abiFailure;
            }

            String selector = calldata.substring(0, 10).toLowerCase();
            List<String> candidates = fourByteSignatureProvider.lookupFunctionSignatures(selector);
            Exception last = null;
            for (String signature : candidates) {
                try {
                    String syntheticAbi = fourByteSignatureProvider.buildSyntheticAbiFromSignature(signature);
                    Map<String, Object> decoded = ABIInputDecoder.decodeInput(syntheticAbi, calldata);
                    decoded.put("decodeSource", "4byte");
                    return new DecodeFallbackResult(decoded, syntheticAbi);
                } catch (Exception decodeCandidateFailure) {
                    last = decodeCandidateFailure;
                }
            }

            if (last != null) {
                throw new Exception("Unable to decode calldata using ABI/explorer or 4byte fallback: " + last.getMessage());
            }
            throw abiFailure;
        }
    }

    private void validateContractAddress(String contractAddress) {
        if (!CONTRACT_ADDRESS_PATTERN.matcher(contractAddress).matches()) {
            throw new IllegalArgumentException("Invalid contract address format. Expected 0x + 40 hex chars.");
        }
    }

    private void validateCalldata(String calldata) {
        if (calldata == null || calldata.isEmpty()) {
            throw new IllegalArgumentException("Calldata is required.");
        }
        if (!calldata.startsWith("0x")) {
            throw new IllegalArgumentException("Calldata must start with 0x.");
        }
        if (calldata.length() < 10) {
            throw new IllegalArgumentException("Calldata must include at least a 4-byte selector.");
        }
        if ((calldata.length() % 2) != 0) {
            throw new IllegalArgumentException("Calldata hex length must be even.");
        }
    }

    private String readEditorContents(Web3JsonEditor editor) {
        return editor.getText();
    }

    private String prettyJson(Object data) throws Exception {
        ObjectWriter writer = objectMapper.writerWithDefaultPrettyPrinter();
        return writer.writeValueAsString(data);
    }

    private static final class InputContext {
        private final int chainId;
        private final String contractAddress;
        private final String rpcUrl;

        private InputContext(int chainId, String contractAddress, String rpcUrl) {
            this.chainId = chainId;
            this.contractAddress = contractAddress;
            this.rpcUrl = rpcUrl;
        }
    }

    private static final class AbiContext {
        private final int chainId;
        private final String contractAddress;
        private final String abiJson;
        private final String abiSource;

        private AbiContext(int chainId, String contractAddress, String abiJson, String abiSource) {
            this.chainId = chainId;
            this.contractAddress = contractAddress;
            this.abiJson = abiJson;
            this.abiSource = abiSource;
        }
    }

    private static final class DecodeResult {
        private final Map<String, Object> output;
        private final String abiJsonUsed;

        private DecodeResult(Map<String, Object> output, String abiJsonUsed) {
            this.output = output;
            this.abiJsonUsed = abiJsonUsed;
        }
    }

    private static final class DecodeFallbackResult {
        private final Map<String, Object> decoded;
        private final String abiJson;

        private DecodeFallbackResult(Map<String, Object> decoded, String abiJson) {
            this.decoded = decoded;
            this.abiJson = abiJson;
        }
    }
}
