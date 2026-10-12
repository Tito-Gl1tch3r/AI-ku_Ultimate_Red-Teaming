(function() {
    async function renamePluginAiThread(threadId) {
        const state = window.getPluginAiState();
        const thread = Array.isArray(state.threads) ? state.threads.find((item) => Number(item.id || 0) === Number(threadId || 0)) : null;
        const fallbackIndex = Math.max(0, Array.isArray(state.threads) ? state.threads.findIndex((item) => Number(item.id || 0) === Number(threadId || 0)) : 0);
        const currentTitle = String(thread?.title || '').trim() || `Chat ${fallbackIndex + 1}`;
        const nextTitle = await window.showPrompt({
            title: 'Rename chat',
            message: 'Enter a new name for this chat.',
            defaultValue: currentTitle,
            confirmText: 'Save',
            cancelText: 'Cancel',
        });
        if (nextTitle == null) return;
        const normalized = String(nextTitle || '').trim();
        if (!normalized) {
            window.showToast('Chat name cannot be empty.', 'warn');
            return;
        }

        const response = await fetch(`/api/ai/threads/${threadId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plugin_slug: String(state.plugin || '').trim(),
                is_theme: !!state.isTheme,
                title: normalized,
            }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }
        window.replacePluginAiThreadInState(data);
        window.showToast('Chat name updated.', 'success');
    }

    async function deletePluginAiThread(threadId) {
        const state = window.getPluginAiState();
        const confirmed = await window.showConfirm('Delete this chat? This action cannot be undone.');
        if (!confirmed) return;

        const response = await fetch(`/api/ai/threads/${threadId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plugin_slug: String(state.plugin || '').trim(),
                is_theme: !!state.isTheme,
            }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }

        window.removePluginAiThreadFromState(threadId);
        if (Number(state.threadId || 0) === Number(threadId || 0)) {
            const nextThread = Array.isArray(state.threads) && state.threads.length ? state.threads[0] : null;
            if (nextThread?.id) {
                state.threadId = Number(nextThread.id);
                await window.switchPluginAiThread(state.threadId);
            } else {
                state.threadId = null;
                state.messages = [];
                state.events = [];
                window.refreshPluginAiRenderedState();
                window.updatePluginAiComposerState(false);
            }
        }
    }

    async function preparePluginAiSource() {
        const state = window.getPluginAiState();
        const threadId = Number(state.threadId || 0);
        const slug = String(state.plugin || '').trim();
        if (!threadId || !slug || state.sourcePreparing) return;

        state.sourcePreparing = true;
        if (typeof window.refreshPluginAiRenderedState === 'function') {
            window.refreshPluginAiRenderedState();
        }
        window.setPluginAiStatus('Preparing source...');

        try {
            const response = await fetch(`/api/ai/threads/${threadId}/source`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plugin_slug: slug,
                    is_theme: !!state.isTheme,
                    last_scan_session_id: typeof window.getCurrentScanId === 'function' ? window.getCurrentScanId() || null : null,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || `HTTP ${response.status}`);
            }
            if (data.thread && typeof window.replacePluginAiThreadInState === 'function') {
                window.replacePluginAiThreadInState(data.thread);
            }
            if (data.thread && typeof window.rememberPluginAiThread === 'function') {
                window.rememberPluginAiThread(data.thread);
            }
            window.setPluginAiStatus('Source ready.');
        } catch (error) {
            window.setPluginAiStatus(`Source prepare failed: ${error.message}`);
        } finally {
            state.sourcePreparing = false;
            if (typeof window.refreshPluginAiRenderedState === 'function') {
                window.refreshPluginAiRenderedState();
            }
        }
    }

    function bindPluginAiSessionEvents() {
        const container = document.getElementById('plugin-ai-sessions');
        if (container && !container.dataset.bound) {
            container.addEventListener('click', async (event) => {
                const renameButton = event.target.closest('[data-thread-rename]');
                if (renameButton) {
                    event.preventDefault();
                    event.stopPropagation();
                    const threadId = Number(renameButton.getAttribute('data-thread-rename') || 0);
                    if (threadId > 0) {
                        try {
                            await renamePluginAiThread(threadId);
                        } catch (error) {
                            window.setPluginAiStatus(`Failed to rename chat: ${error.message}`);
                        }
                    }
                    return;
                }

                const deleteButton = event.target.closest('[data-thread-delete]');
                if (deleteButton) {
                    event.preventDefault();
                    event.stopPropagation();
                    const threadId = Number(deleteButton.getAttribute('data-thread-delete') || 0);
                    if (threadId > 0) {
                        try {
                            await deletePluginAiThread(threadId);
                        } catch (error) {
                            window.setPluginAiStatus(`Failed to delete chat: ${error.message}`);
                        }
                    }
                    return;
                }

                const button = event.target.closest('[data-thread-id]');
                if (!button) return;
                const threadId = Number(button.getAttribute('data-thread-id') || 0);
                if (threadId > 0) {
                    await window.switchPluginAiThread(threadId);
                }
            });
            container.dataset.bound = '1';
        }

        const newChatButton = document.getElementById('plugin-ai-new-chat-btn');
        if (newChatButton && !newChatButton.dataset.bound) {
            newChatButton.addEventListener('click', async () => {
                await window.createNewPluginAiThread();
            });
            newChatButton.dataset.bound = '1';
        }

        const sourceButton = document.getElementById('plugin-ai-source-download-btn');
        if (sourceButton && !sourceButton.dataset.bound) {
            sourceButton.addEventListener('click', async () => {
                await preparePluginAiSource();
            });
            sourceButton.dataset.bound = '1';
        }
    }

    function initializePluginAiHelpers() {
        bindPluginAiSessionEvents();
        window.updatePluginAiSessionUi();
        if (typeof window.bindPluginAiLayoutEvents === 'function') {
            window.bindPluginAiLayoutEvents();
        }
        if (typeof window.bindAiSettingsEvents === 'function') {
            window.bindAiSettingsEvents();
        }
    }

    function initializePluginAiModal() {
        initializePluginAiHelpers();
        if (typeof window.setPluginAiExpanded === 'function') {
            window.setPluginAiExpanded(false);
        }
    }

    function appendPluginAiDetachedEvents({ slug, threadId, isTheme, events = [] }) {
        if (typeof window.getPluginAiEventsSnapshot !== 'function' || typeof window.rememberPluginAiEventsSnapshot !== 'function') {
            return;
        }
        const snapshot = window.getPluginAiEventsSnapshot(slug, threadId, !!isTheme);
        const existing = Array.isArray(snapshot?.events) ? snapshot.events : [];
        const nextEvents = Array.isArray(events) ? events.filter(Boolean) : [];
        if (!nextEvents.length) return;
        const mergedEvents = [...existing, ...nextEvents].slice(-120);
        window.rememberPluginAiEventsSnapshot({
            plugin: slug,
            threadId,
            isTheme: !!isTheme,
            events: mergedEvents,
            createdAt: new Date().toISOString(),
        });
        if (typeof window.rememberPluginAiThreadUiSnapshot === 'function') {
            const uiSnapshot = typeof window.getPluginAiThreadUiSnapshot === 'function'
                ? window.getPluginAiThreadUiSnapshot(slug, threadId, !!isTheme)
                : null;
            window.rememberPluginAiThreadUiSnapshot({
                plugin: slug,
                threadId,
                isTheme: !!isTheme,
                messages: Array.isArray(uiSnapshot?.messages) ? uiSnapshot.messages : [],
                events: mergedEvents,
                liveActivity: mergedEvents,
                sending: true,
                runStartedAt: String(uiSnapshot?.runStartedAt || ''),
                badgeText: String(uiSnapshot?.badgeText || window.buildPluginAiRunningBadgeLabel(uiSnapshot?.runStartedAt)),
                statusText: String(uiSnapshot?.statusText || window.buildPluginAiRunningStatusText(uiSnapshot?.runStartedAt)),
                sourceStatus: uiSnapshot?.sourceStatus || {},
            });
        }
    }

    async function submitPluginAiMessage(promptOverride = '') {
        const state = window.getPluginAiState();
        const input = document.getElementById('plugin-ai-input');
        if (!state.threadId || !input) return;
        const isCurrentThreadStreaming = !!state.sending
            && Number(state.streamThreadId || 0) === Number(state.threadId || 0)
            && !!String(state.streamRequestId || '').trim();
        if (isCurrentThreadStreaming) return;

        const slug = String(state.plugin || '').trim();
        const threadId = state.threadId;
        const viewToken = state.viewToken;
        const content = window.normalizePluginAiInput(promptOverride, input.value);
        if (!content) {
            window.setPluginAiNoMessageWarning();
            return;
        }

        if (!window.getCurrentScanId || !window.getCurrentScanId()) {
            window.setPluginAiStatus('No active scan context. AI will use a trusted local source if available, otherwise stored metadata only.');
        }

        state.sending = true;
        state.runStartedAt = new Date().toISOString();
        state.sourcePreparing = false;
        if (typeof window.stopPluginAiPendingRunPoll === 'function') {
            window.stopPluginAiPendingRunPoll();
        }
        if (typeof window.stopPluginAiThreadSyncPoll === 'function') {
            window.stopPluginAiThreadSyncPoll();
        }
        const streamRequestId = window.beginPluginAiStreamRequest(threadId);
        const hasAssistantHistory = Array.isArray(state.messages) && state.messages.some((item) => String(item?.role || '') === 'assistant' && !item?.is_pending_assistant);
        const activeThread = Array.isArray(state.threads) ? state.threads.find((item) => Number(item?.id || 0) === Number(threadId || 0)) : null;
        const workspaceRoot = String(activeThread?.workspace_path || state.workspacePath || '').trim();
        window.setPluginAiLiveActivityOptions({ showSource: !hasAssistantHistory, workspaceRoot });
        state.liveActivity = [];
        window.updatePluginAiComposerState(false);
        window.setPluginAiRunningBadge();
        window.setPluginAiStatus(window.buildPluginAiRunningStatusText(state.runStartedAt));
        if (state.runningIndicatorTimer) {
            window.clearInterval(state.runningIndicatorTimer);
        }
        state.runningIndicatorTimer = window.setInterval(() => {
            if (typeof window.refreshPluginAiRunningIndicators === 'function') {
                window.refreshPluginAiRunningIndicators();
            }
        }, 1000);

        const optimisticUserMessage = {
            id: `tmp-user-${Date.now()}`,
            thread_id: threadId,
            role: 'user',
            content,
            created_at: new Date().toISOString(),
            tool_calls: [],
            tool_results: [],
        };
        const pendingAssistantMessage = {
            id: `tmp-assistant-${Date.now()}`,
            thread_id: threadId,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
            tool_calls: [],
            tool_results: [],
            is_pending_assistant: true,
        };
        window.pushPluginAiMessage(optimisticUserMessage);
        window.pushPluginAiMessage(pendingAssistantMessage);
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({
                threadId,
                messages: state.messages,
                liveActivity: state.liveActivity,
                events: state.events,
                sending: true,
                runStartedAt: state.runStartedAt,
                badgeText: window.buildPluginAiRunningBadgeLabel(state.runStartedAt),
                statusText: window.buildPluginAiRunningStatusText(state.runStartedAt),
            });
        }
        if (typeof window.rememberPluginAiPendingSnapshot === 'function') {
            window.rememberPluginAiPendingSnapshot({
                plugin: slug,
                threadId,
                isTheme: !!state.isTheme,
                content,
                createdAt: optimisticUserMessage.created_at,
            });
        }
        window.refreshPluginAiRenderedState();
        input.value = '';

        try {
            let requestPayload;
            try {
                requestPayload = window.buildPluginAiMessagePayload({ threadId, content });
            } catch (payloadError) {
                state.sending = false;
                window.updatePluginAiComposerState(false);
                window.setPluginAiStatus(payloadError.message || 'Invalid AI runtime options.');
                window.showToast(payloadError.message || 'Invalid AI runtime options.', 'warn');
                return;
            }
            const response = await fetch('/api/ai/messages/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestPayload),
            });
            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || `HTTP ${response.status}`);
            }
            if (!response.body) {
                throw new Error('Streaming response body is not available.');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalPayload = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const rawLine of lines) {
                    const line = String(rawLine || '').trim();
                    if (!line) continue;
                    let chunk = {};
                    try {
                        chunk = JSON.parse(line);
                    } catch (parseError) {
                        continue;
                    }
                    if (!window.isCurrentPluginAiStreamRequest(streamRequestId)) {
                        return;
                    }
                    if (window.shouldIgnorePluginAiResponse(slug, viewToken, threadId)) {
                        if (chunk.type === 'bridge_event' || chunk.type === 'runtime_event') {
                            appendPluginAiDetachedEvents({
                                slug,
                                threadId,
                                isTheme: !!state.isTheme,
                                events: [chunk.data],
                            });
                        }
                        if (chunk.type === 'final' && chunk.data && typeof chunk.data === 'object') {
                            const detachedEvents = Array.isArray(chunk.data.team_events) ? chunk.data.team_events : [];
                            if (detachedEvents.length) {
                                appendPluginAiDetachedEvents({
                                    slug,
                                    threadId,
                                    isTheme: !!state.isTheme,
                                    events: detachedEvents,
                                });
                            }
                            if (typeof window.clearPluginAiPendingSnapshot === 'function') {
                                window.clearPluginAiPendingSnapshot(slug, threadId, !!state.isTheme);
                            }
                        }
                        continue;
                    }
                    if (chunk.type === 'error') {
                        throw new Error(chunk?.data?.detail || 'AI stream failed.');
                    }
                    window.applyPluginAiStreamChunk(chunk);
                    if (chunk.type === 'final') {
                        finalPayload = chunk.data || null;
                    }
                    window.refreshPluginAiRenderedState();
                }
            }

            if (buffer.trim()) {
                try {
                    const chunk = JSON.parse(buffer.trim());
                    if (window.shouldIgnorePluginAiResponse(slug, viewToken, threadId)) {
                        if (chunk.type === 'bridge_event' || chunk.type === 'runtime_event') {
                            appendPluginAiDetachedEvents({
                                slug,
                                threadId,
                                isTheme: !!state.isTheme,
                                events: [chunk.data],
                            });
                        }
                        if (chunk.type === 'final' && chunk.data && typeof chunk.data === 'object') {
                            const detachedEvents = Array.isArray(chunk.data.team_events) ? chunk.data.team_events : [];
                            if (detachedEvents.length) {
                                appendPluginAiDetachedEvents({
                                    slug,
                                    threadId,
                                    isTheme: !!state.isTheme,
                                    events: detachedEvents,
                                });
                            }
                            if (typeof window.clearPluginAiPendingSnapshot === 'function') {
                                window.clearPluginAiPendingSnapshot(slug, threadId, !!state.isTheme);
                            }
                        }
                    } else {
                        if (chunk.type === 'error') {
                            throw new Error(chunk?.data?.detail || 'AI stream failed.');
                        }
                        window.applyPluginAiStreamChunk(chunk);
                        if (chunk.type === 'final') {
                            finalPayload = chunk.data || null;
                        }
                    }
                } catch (parseError) {
                    if (!finalPayload) {
                        throw new Error('AI stream ended with malformed output.');
                    }
                }
            }

            if (window.shouldIgnorePluginAiResponse(slug, viewToken, threadId)) {
                return;
            }

            if (!finalPayload && state.sending && typeof window.startPluginAiPendingRunPoll === 'function') {
                window.startPluginAiPendingRunPoll({ slug, threadId, viewToken });
            }

            if (typeof window.clearPluginAiPendingSnapshot === 'function') {
                window.clearPluginAiPendingSnapshot(slug, threadId, !!state.isTheme);
            }
            if (finalPayload && typeof finalPayload === 'object') {
                state.events = Array.isArray(finalPayload.team_events) ? finalPayload.team_events : [];
                state.liveActivity = state.events.length ? state.events : (state.liveActivity || []);
                state.pendingApproval = finalPayload.pending_approval && typeof finalPayload.pending_approval === 'object'
                    ? finalPayload.pending_approval
                    : null;
                if (finalPayload.assistant_message && finalPayload.agents && Array.isArray(finalPayload.agents)) {
                    const latestStructured = finalPayload.agents.find((agent) => agent && typeof agent === 'object' && agent.structured)?.structured;
                    if (latestStructured && Array.isArray(state.messages) && state.messages.length) {
                        const lastIndex = state.messages.length - 1;
                        state.messages[lastIndex] = {
                            ...state.messages[lastIndex],
                            structured: latestStructured,
                        };
                    }
                }
                if (state.runningIndicatorTimer) {
                    window.clearInterval(state.runningIndicatorTimer);
                    state.runningIndicatorTimer = null;
                }
                if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
                    window.syncCurrentPluginAiThreadSnapshot({
                        threadId,
                        messages: state.messages,
                        events: state.events,
                        liveActivity: state.liveActivity,
                        sending: false,
                        runStartedAt: '',
                        badgeText: 'Ready',
                        statusText: 'AI response received.',
                        pendingApproval: state.pendingApproval,
                    });
                }
                window.refreshPluginAiRenderedState();
            } else {
                window.removePendingAssistantMessage();
                state.liveActivity = [];
                window.refreshPluginAiRenderedState();
            }
            window.updatePluginAiThreadsAfterMessage(threadId);
            window.setPluginAiBadge(window.buildPluginAiThreadBadge());
            window.setPluginAiResponseReceivedStatus();
        } catch (error) {
            if (window.shouldIgnorePluginAiResponse(slug, viewToken, threadId)) {
                return;
            }
            if (typeof window.clearPluginAiPendingSnapshot === 'function') {
                window.clearPluginAiPendingSnapshot(slug, threadId, !!state.isTheme);
            }
            window.removePendingAssistantMessage();
            state.liveActivity = [];
            if (state.runningIndicatorTimer) {
                window.clearInterval(state.runningIndicatorTimer);
                state.runningIndicatorTimer = null;
            }
            if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
                window.syncCurrentPluginAiThreadSnapshot({
                    threadId,
                    messages: state.messages,
                    events: state.events,
                    liveActivity: state.liveActivity,
                    sending: false,
                    runStartedAt: '',
                    badgeText: 'Error',
                    statusText: `AI request failed: ${error.message}`,
                });
            }
            window.refreshPluginAiRenderedState();
            window.setPluginAiErrorBadge();
            window.setPluginAiRequestFailure(error);
            window.setPluginAiRequestErrorToast(error);
        } finally {
            const latestState = window.getPluginAiState();
            const ownsActiveStream = window.isCurrentPluginAiStreamRequest(streamRequestId)
                || Number(latestState.streamThreadId || 0) === Number(threadId || 0);
            if (ownsActiveStream) {
                window.endPluginAiStreamRequest(streamRequestId);
                latestState.sending = false;
                latestState.pendingSnapshotRetryInFlight = false;
            }
            const isActiveThread = Number(latestState.threadId || 0) === Number(threadId || 0);
            if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
                window.syncCurrentPluginAiThreadSnapshot({
                    threadId,
                    messages: latestState.messages,
                    events: latestState.events,
                    liveActivity: latestState.liveActivity,
                    sending: latestState.sending,
                });
            }
            const canCompose = !!latestState.threadId && !latestState.loading && (!latestState.sending || !isActiveThread);
            window.updatePluginAiComposerState(canCompose);
            if (window.isPluginAiViewCurrent(slug, viewToken) && isActiveThread && !latestState.sending) {
                window.setPluginAiBadge(window.buildPluginAiThreadBadge());
                if (typeof window.startPluginAiThreadSyncPoll === 'function') {
                    window.startPluginAiThreadSyncPoll({ slug, threadId, viewToken });
                }
            }
        }
    }

    async function submitPluginAiApprovalDecision(decision) {
        const state = window.getPluginAiState();
        const pendingApproval = state.pendingApproval && typeof state.pendingApproval === 'object' ? state.pendingApproval : null;
        const threadId = Number(state.threadId || 0);
        const slug = String(state.plugin || '').trim();
        if (!pendingApproval || !threadId || !slug) return;
        const response = await fetch(`/api/ai/runs/${encodeURIComponent(pendingApproval.run_id)}/approval`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plugin_slug: slug,
                is_theme: !!state.isTheme,
                decision,
            }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }
        state.pendingApproval = null;
        if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
            window.syncCurrentPluginAiThreadSnapshot({ pendingApproval: null, sending: true });
        }
        window.setPluginAiStatus(decision === 'approved' ? 'Approval granted. Continuing run...' : 'Approval rejected. Finishing run...');
        if (typeof window.startPluginAiPendingRunPoll === 'function') {
            window.startPluginAiPendingRunPoll({ slug, threadId, viewToken: state.viewToken });
        }
        window.refreshPluginAiRenderedState();
        return data;
    }

    function bindPluginAiUiEvents() {
        initializePluginAiModal();
        if (typeof window.fetchCurrentAiSettings === 'function') {
            window.fetchCurrentAiSettings().catch(() => null);
        }

        const form = document.getElementById('plugin-ai-form');
        if (form && !form.dataset.bound) {
            form.addEventListener('submit', (event) => {
                event.preventDefault();
                submitPluginAiMessage();
            });
            form.dataset.bound = '1';
        }

        const input = document.getElementById('plugin-ai-input');
        if (input && !input.dataset.bound) {
            input.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    submitPluginAiMessage();
                }
            });
            input.dataset.bound = '1';
        }

        const messagePanel = document.getElementById('plugin-ai-messages');
        if (messagePanel && !messagePanel.dataset.approvalBound) {
            messagePanel.addEventListener('click', async (event) => {
                const target = event.target instanceof HTMLElement ? event.target : null;
                if (!target) return;
                if (target.id === 'plugin-ai-approve-run') {
                    event.preventDefault();
                    try {
                        await submitPluginAiApprovalDecision('approved');
                    } catch (error) {
                        window.showToast(error.message || 'Failed to approve run.', 'warn');
                    }
                }
                if (target.id === 'plugin-ai-reject-run') {
                    event.preventDefault();
                    try {
                        await submitPluginAiApprovalDecision('rejected');
                    } catch (error) {
                        window.showToast(error.message || 'Failed to reject run.', 'warn');
                    }
                }
            });
            messagePanel.dataset.approvalBound = '1';
        }

        const combinedSelect = document.getElementById('plugin-ai-profile-model-select');
        if (combinedSelect && !combinedSelect.dataset.bound) {
            combinedSelect.addEventListener('change', (event) => {
                const raw = String(event.target.value || '').trim();
                const [profileKey, model] = raw.split('::');
                window.updatePluginAiComposerSelections({
                    selectedProfileKey: String(profileKey || '').trim() || null,
                    selectedModel: String(model || '').trim() || null,
                });
            });
            combinedSelect.dataset.bound = '1';
        }

        if (typeof window.renderPluginAiComposerProfiles === 'function') {
            window.renderPluginAiComposerProfiles();
        }
    }

    window.bindPluginAiSessionEvents = bindPluginAiSessionEvents;
    window.initializePluginAiHelpers = initializePluginAiHelpers;
    window.initializePluginAiModal = initializePluginAiModal;
    window.submitPluginAiMessage = submitPluginAiMessage;
    window.bindPluginAiUiEvents = bindPluginAiUiEvents;
})();
