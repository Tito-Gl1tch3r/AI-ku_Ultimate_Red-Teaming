package com.nccgroup.web3decoder;

import com.nccgroup.web3decoder.detection.DetectedAbiStore;
import com.nccgroup.web3decoder.persistence.ExtensionConfig;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.ui.editor.extension.EditorCreationContext;
import burp.api.montoya.ui.editor.extension.ExtensionProvidedHttpRequestEditor;
import burp.api.montoya.ui.editor.extension.ExtensionProvidedHttpResponseEditor;
import burp.api.montoya.ui.editor.extension.HttpRequestEditorProvider;
import burp.api.montoya.ui.editor.extension.HttpResponseEditorProvider;

class Web3EditorTabProvider implements HttpRequestEditorProvider, HttpResponseEditorProvider
{
    private final MontoyaApi api;
    private final ExtensionConfig config;
    private final DetectedAbiStore detectedAbiStore;

    Web3EditorTabProvider(MontoyaApi api, ExtensionConfig config)
    {
        this(api, config, null);
    }

    Web3EditorTabProvider(MontoyaApi api, ExtensionConfig config, DetectedAbiStore detectedAbiStore)
    {
        this.api = api;
        this.config = config;
        this.detectedAbiStore = detectedAbiStore;
    }

    @Override
    public ExtensionProvidedHttpRequestEditor provideHttpRequestEditor(EditorCreationContext creationContext)
    {
        return new Web3RequestEditor(api, config, creationContext, detectedAbiStore);
    }

    @Override
    public ExtensionProvidedHttpResponseEditor provideHttpResponseEditor(EditorCreationContext creationContext) {
        return new Web3ResponseEditor(api, config, creationContext, detectedAbiStore);
    }
}
