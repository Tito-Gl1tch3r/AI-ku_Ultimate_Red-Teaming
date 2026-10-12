(function() {
    function setPluginAiStatus(message) {
        const safeMessage = String(message || '');
        const statusEl = document.getElementById('plugin-ai-status');
        if (statusEl) statusEl.textContent = safeMessage;
        const state = typeof window.getPluginAiState === 'function' ? window.getPluginAiState() : null;
        if (state && typeof state === 'object') {
            state.statusText = safeMessage;
        }
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({ statusText: safeMessage });
        }
    }

    function setPluginAiBadge(message) {
        const safeMessage = String(message || '');
        const badgeEl = document.getElementById('plugin-ai-thread-badge');
        if (badgeEl) badgeEl.textContent = safeMessage;
        const state = typeof window.getPluginAiState === 'function' ? window.getPluginAiState() : null;
        if (state && typeof state === 'object') {
            state.badgeText = safeMessage;
        }
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({ badgeText: safeMessage });
        }
    }

    function setPluginAiComposerEnabled(enabled) {
        const input = document.getElementById('plugin-ai-input');
        const sendBtn = document.getElementById('plugin-ai-send');
        const combinedSelect = document.getElementById('plugin-ai-profile-model-select');
        if (input) input.disabled = !enabled;
        if (sendBtn) sendBtn.disabled = !enabled;
        if (combinedSelect) combinedSelect.disabled = !enabled;
    }

    function formatPluginAiRunDuration(runStartedAt) {
        const startedAt = String(runStartedAt || '').trim();
        if (!startedAt) return '0m 00s';
        const startedMs = new Date(startedAt).getTime();
        if (!Number.isFinite(startedMs)) return '0m 00s';
        const diffSeconds = Math.max(0, Math.floor((Date.now() - startedMs) / 1000));
        const minutes = Math.floor(diffSeconds / 60);
        const seconds = diffSeconds % 60;
        return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
    }

    function buildPluginAiRunningBadgeLabel(runStartedAt) {
        return `Running • ${formatPluginAiRunDuration(runStartedAt)}`;
    }

    function buildPluginAiRunningStatusText(runStartedAt) {
        return `AI is running • ${formatPluginAiRunDuration(runStartedAt)}`;
    }

    function refreshPluginAiRunningIndicators() {
        const state = typeof window.getPluginAiState === 'function' ? window.getPluginAiState() : null;
        if (!state || !state.sending || !String(state.runStartedAt || '').trim()) return;
        const badgeEl = document.getElementById('plugin-ai-thread-badge');
        const statusEl = document.getElementById('plugin-ai-status');
        if (badgeEl) badgeEl.textContent = buildPluginAiRunningBadgeLabel(state.runStartedAt);
        if (statusEl && String(state.statusText || '').includes('AI is running')) {
            statusEl.textContent = buildPluginAiRunningStatusText(state.runStartedAt);
        }
        if (typeof window.updatePluginAiSessionUi === 'function') {
            window.updatePluginAiSessionUi();
        }
    }

    function updatePluginAiComposerState(enabled) {
        setPluginAiComposerEnabled(enabled);
    }

    function getMaskedApiKeyPlaceholder(config = {}) {
        const masked = String(config.api_key_masked || '').trim();
        return masked || 'Enter a new API key';
    }

    function shouldRequireApiKeyInput(config = {}) {
        return !String(config.api_key_masked || '').trim();
    }

    function updatePluginAiApiKeyHint(config = {}) {
        const apiKeyInput = document.getElementById('plugin-ai-api-key');
        if (!apiKeyInput) return;
        apiKeyInput.placeholder = getMaskedApiKeyPlaceholder(config);
        apiKeyInput.required = shouldRequireApiKeyInput(config);
    }

    function buildPluginAiThreadBadge() {
        return 'Ready';
    }

    function setPluginAiThreadLoadingBadge() {
        setPluginAiBadge('Loading');
    }

    function setPluginAiRunningBadge() {
        const state = typeof window.getPluginAiState === 'function' ? window.getPluginAiState() : null;
        setPluginAiBadge(buildPluginAiRunningBadgeLabel(state?.runStartedAt));
    }

    function setPluginAiErrorBadge() {
        setPluginAiBadge('Error');
    }

    function currentPluginAiLabel(plugin) {
        return plugin?.is_theme ? 'theme' : 'plugin';
    }

    function buildPluginAiThreadStatus(plugin) {
        return `Loading AI thread for ${currentPluginAiLabel(plugin)} ${String(plugin?.slug || '').trim()}...`;
    }

    function setPluginAiThreadStatusLoading(plugin) {
        setPluginAiStatus(buildPluginAiThreadStatus(plugin));
    }

    function setPluginAiThreadReadyStatus() {
        setPluginAiStatus('AI thread ready. Loading existing messages...');
    }

    function setPluginAiResponseReceivedStatus() {
        setPluginAiStatus('AI response received.');
    }

    function setPluginAiSettingsLoadingStatus() {
        setPluginAiStatus('Loading AI settings...');
    }

    function buildPluginAiLoadedStatus(messages = []) {
        return messages.length ? 'AI messages loaded.' : 'Thread ready.';
    }

    function notePluginAiMessagesLoaded(messages = []) {
        setPluginAiStatus(buildPluginAiLoadedStatus(messages));
    }

    function buildPluginAiRequestFailureStatus(error) {
        return `AI request failed: ${error.message}`;
    }

    function buildPluginAiSettingsLoadedStatus(config) {
        const label = config?.display_name || config?.model || config?.provider;
        return label ? `Loaded AI profile ${label}.` : 'No AI profile configured yet.';
    }

    function buildPluginAiSettingsSavedStatus(provider) {
        return `Saved AI profile for ${provider}.`;
    }

    function setPluginAiRequestFailure(error) {
        setPluginAiStatus(buildPluginAiRequestFailureStatus(error));
    }

    function setPluginAiSettingsStatus(config) {
        setPluginAiStatus(buildPluginAiSettingsLoadedStatus(config));
    }

    function setPluginAiSavedStatus(provider) {
        setPluginAiStatus(buildPluginAiSettingsSavedStatus(provider));
    }

    function setPluginAiSettingsSavedToast() {
        showToast('AI settings saved.', 'success');
    }

    function setPluginAiNoMessageWarning() {
        showToast('Enter a message for AI first.', 'warn');
    }

    function buildPluginAiNoScanWarning(plugin) {
        return `Open this ${currentPluginAiLabel(plugin)} from a scan result before starting AI chat.`;
    }

    function setPluginAiNoScanWarningForPlugin(plugin) {
        showToast(buildPluginAiNoScanWarning(plugin), 'warn');
    }

    function setPluginAiSettingsErrorToast(error) {
        showToast(`Failed to save AI settings: ${error.message}`, 'error');
    }

    function setPluginAiLoadSettingsErrorToast(error) {
        showToast(`Failed to load AI settings: ${error.message}`, 'error');
    }

    function setPluginAiRequestErrorToast(error) {
        showToast(buildPluginAiRequestFailureStatus(error), 'error');
    }

    window.setPluginAiStatus = setPluginAiStatus;
    window.setPluginAiBadge = setPluginAiBadge;
    window.setPluginAiComposerEnabled = setPluginAiComposerEnabled;
    window.updatePluginAiComposerState = updatePluginAiComposerState;
    window.formatPluginAiRunDuration = formatPluginAiRunDuration;
    window.buildPluginAiRunningBadgeLabel = buildPluginAiRunningBadgeLabel;
    window.buildPluginAiRunningStatusText = buildPluginAiRunningStatusText;
    window.refreshPluginAiRunningIndicators = refreshPluginAiRunningIndicators;
    window.getMaskedApiKeyPlaceholder = getMaskedApiKeyPlaceholder;
    window.shouldRequireApiKeyInput = shouldRequireApiKeyInput;
    window.updatePluginAiApiKeyHint = updatePluginAiApiKeyHint;
    window.buildPluginAiThreadBadge = buildPluginAiThreadBadge;
    window.setPluginAiThreadLoadingBadge = setPluginAiThreadLoadingBadge;
    window.setPluginAiRunningBadge = setPluginAiRunningBadge;
    window.setPluginAiErrorBadge = setPluginAiErrorBadge;
    window.currentPluginAiLabel = currentPluginAiLabel;
    window.buildPluginAiThreadStatus = buildPluginAiThreadStatus;
    window.setPluginAiThreadStatusLoading = setPluginAiThreadStatusLoading;
    window.setPluginAiThreadReadyStatus = setPluginAiThreadReadyStatus;
    window.setPluginAiResponseReceivedStatus = setPluginAiResponseReceivedStatus;
    window.setPluginAiSettingsLoadingStatus = setPluginAiSettingsLoadingStatus;
    window.buildPluginAiLoadedStatus = buildPluginAiLoadedStatus;
    window.notePluginAiMessagesLoaded = notePluginAiMessagesLoaded;
    window.buildPluginAiRequestFailureStatus = buildPluginAiRequestFailureStatus;
    window.buildPluginAiSettingsLoadedStatus = buildPluginAiSettingsLoadedStatus;
    window.buildPluginAiSettingsSavedStatus = buildPluginAiSettingsSavedStatus;
    window.setPluginAiRequestFailure = setPluginAiRequestFailure;
    window.setPluginAiSettingsStatus = setPluginAiSettingsStatus;
    window.setPluginAiSavedStatus = setPluginAiSavedStatus;
    window.setPluginAiSettingsSavedToast = setPluginAiSettingsSavedToast;
    window.setPluginAiNoMessageWarning = setPluginAiNoMessageWarning;
    window.buildPluginAiNoScanWarning = buildPluginAiNoScanWarning;
    window.setPluginAiNoScanWarningForPlugin = setPluginAiNoScanWarningForPlugin;
    window.setPluginAiSettingsErrorToast = setPluginAiSettingsErrorToast;
    window.setPluginAiLoadSettingsErrorToast = setPluginAiLoadSettingsErrorToast;
    window.setPluginAiRequestErrorToast = setPluginAiRequestErrorToast;
})();
