package com.nccgroup.web3decoder;

import com.nccgroup.web3decoder.annotation.Web3HistoryAnnotator;
import com.nccgroup.web3decoder.detection.AbiDetectionHttpHandler;
import com.nccgroup.web3decoder.detection.AbiDetectionScanCheck;
import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;
import com.nccgroup.web3decoder.ui.MainChainsPanel;

import burp.api.montoya.BurpExtension;
import burp.api.montoya.MontoyaApi;
import burp.api.montoya.scanner.scancheck.ScanCheckType;

public class Web3DecoderExtension implements BurpExtension
{
    private static final int DETECTED_ABI_STORE_CAPACITY = 1024;

    private MontoyaApi api;
    private ExtensionConfig config;
    private DetectedAbiStore detectedAbiStore;
    private Web3HistoryAnnotator historyAnnotator;

    @Override
    public void initialize(MontoyaApi api)
    {
        this.api = api;
        this.config = new ExtensionConfig(api);
        this.detectedAbiStore = new DetectedAbiStore(api, DETECTED_ABI_STORE_CAPACITY);

        api.extension().setName("Web3 Decoder");
        Web3EditorTabProvider web3EditorTabProvider = new Web3EditorTabProvider(api, config, detectedAbiStore);
        api.userInterface().registerHttpRequestEditorProvider(web3EditorTabProvider);
        api.userInterface().registerHttpResponseEditorProvider(web3EditorTabProvider);
        this.historyAnnotator = new Web3HistoryAnnotator(api, config, detectedAbiStore);
        api.http().registerHttpHandler(historyAnnotator);
        // Detect ABIs on every response — covers cases where Burp's Live Audit
        // deduplicates identical requests and would otherwise skip the scan check
        // (e.g. after manually deleting an entry from the Detected ABIs panel).
        api.http().registerHttpHandler(new AbiDetectionHttpHandler(api, detectedAbiStore));
        api.scanner().registerPassiveScanCheck(
                new AbiDetectionScanCheck(detectedAbiStore, api.logging()),
                ScanCheckType.PER_REQUEST);

        api.extension().registerUnloadingHandler(this::unload);

        initializeUI();
    }

    private void unload() {
        if (historyAnnotator != null) {
            historyAnnotator.shutdown();
        }
    }


    /**
     * Initializes the user interface by adding the ChainsTablePanel as a new tab.
     */
    private void initializeUI() {
        // Create the ChainsTablePanel
        MainChainsPanel mainPanel = new MainChainsPanel(api, config, detectedAbiStore);

        // Add the Tab to Burp's UI
        api.userInterface().registerSuiteTab("Web3", mainPanel);

        api.logging().logToOutput("Chains Manager tab added to Burp UI.");
    }
}
