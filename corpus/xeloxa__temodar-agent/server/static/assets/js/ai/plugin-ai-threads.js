(function() {
    function stopPluginAiThreadSyncPoll() {
        const state = window.getPluginAiState();
        if (state.threadSyncPollTimer) {
            window.clearTimeout(state.threadSyncPollTimer);
            state.threadSyncPollTimer = null;
        }
        state.threadSyncPollKey = null;
    }

    function startPluginAiThreadSyncPoll(options = {}) {
        const state = window.getPluginAiState();
        const slug = String(options.slug || state.plugin || '').trim();
        const threadId = Number(options.threadId || state.threadId || 0);
        const viewToken = options.viewToken ?? state.viewToken;
        if (!slug || !threadId) return;

        const pollKey = `${slug}::${threadId}::${viewToken}`;
        if (state.threadSyncPollKey === pollKey && state.threadSyncPollTimer) return;

        stopPluginAiThreadSyncPoll();
        state.threadSyncPollKey = pollKey;

        let tickCount = 0;
        const poll = async () => {
            const liveState = window.getPluginAiState();
            if (!window.isPluginAiViewCurrent(slug, viewToken) || Number(liveState.threadId || 0) !== threadId) {
                stopPluginAiThreadSyncPoll();
                return;
            }
            if (liveState.loading) {
                liveState.threadSyncPollTimer = window.setTimeout(poll, 600);
                return;
            }

            await loadPluginAiMessages({ slug, threadId, viewToken, silent: true });
            tickCount += 1;
            const nextDelay = tickCount <= 4 ? 500 : 1500;
            liveState.threadSyncPollTimer = window.setTimeout(poll, nextDelay);
        };

        state.threadSyncPollTimer = window.setTimeout(poll, 120);
    }

    function stopPluginAiPendingRunPoll() {
        const state = window.getPluginAiState();
        if (state.pendingRunPollTimer) {
            window.clearTimeout(state.pendingRunPollTimer);
            state.pendingRunPollTimer = null;
        }
        state.pendingRunPollKey = null;
    }

    function startPluginAiPendingRunPoll(options = {}) {
        const state = window.getPluginAiState();
        const slug = String(options.slug || state.plugin || '').trim();
        const threadId = Number(options.threadId || state.threadId || 0);
        const viewToken = options.viewToken ?? state.viewToken;
        if (!slug || !threadId) return;

        const pollKey = `${slug}::${threadId}::${viewToken}`;
        if (state.pendingRunPollKey === pollKey && state.pendingRunPollTimer) {
            return;
        }

        stopPluginAiPendingRunPoll();
        stopPluginAiThreadSyncPoll();
        state.pendingRunPollKey = pollKey;

        const poll = async () => {
            if (!window.isPluginAiViewCurrent(slug, viewToken) || Number(window.getPluginAiState().threadId || 0) !== threadId) {
                stopPluginAiPendingRunPoll();
                return;
            }

            const result = await loadPluginAiMessages({ slug, threadId, viewToken });
            if (!result?.hasPendingRun) {
                stopPluginAiPendingRunPoll();
                if (window.isPluginAiViewCurrent(slug, viewToken) && Number(window.getPluginAiState().threadId || 0) === threadId) {
                    state.sending = false;
                    window.setPluginAiBadge(window.buildPluginAiThreadBadge());
                    window.updatePluginAiComposerState(true);
                    window.setPluginAiResponseReceivedStatus();
                }
                return;
            }

            state.pendingRunPollTimer = window.setTimeout(poll, 800);
        };

        state.pendingRunPollTimer = window.setTimeout(poll, 180);
    }

    async function loadPluginAiThreads(plugin, options = {}) {
        const state = window.getPluginAiState();
        const slug = String(plugin?.slug || state.plugin || '').trim();
        const isTheme = options.isTheme ?? !!plugin?.is_theme ?? state.isTheme;
        const viewToken = options.viewToken ?? state.viewToken;
        if (!slug) return [];

        const response = await fetch(`/api/ai/threads/plugin?plugin_slug=${encodeURIComponent(slug)}&is_theme=${isTheme ? 'true' : 'false'}&_ts=${Date.now()}`, {
            cache: 'no-store',
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }
        if (!window.isPluginAiViewCurrent(slug, viewToken)) {
            return [];
        }
        const threads = Array.isArray(data.threads) ? data.threads : [];
        window.rememberPluginAiThreads(threads);
        window.renderPluginAiSessions(threads, state.threadId);
        return threads;
    }

    async function loadPluginAiMessages(options = {}) {
        const state = window.getPluginAiState();
        const slug = String(options.slug || state.plugin || '').trim();
        const viewToken = options.viewToken ?? state.viewToken;
        const threadId = options.threadId ?? state.threadId;
        const silent = !!options.silent;

        if (threadId && typeof window.hydratePluginAiThreadUiSnapshot === 'function') {
            const hydratedSnapshot = window.hydratePluginAiThreadUiSnapshot(slug, threadId, !!state.isTheme);
            if (hydratedSnapshot && !silent) {
                window.refreshPluginAiRenderedState();
                if (hydratedSnapshot.badgeText) {
                    window.setPluginAiBadge(hydratedSnapshot.badgeText);
                }
                if (hydratedSnapshot.statusText) {
                    window.setPluginAiStatus(hydratedSnapshot.statusText);
                }
                if (hydratedSnapshot.sending && hydratedSnapshot.runStartedAt) {
                    if (state.runningIndicatorTimer) {
                        window.clearInterval(state.runningIndicatorTimer);
                    }
                    state.runningIndicatorTimer = window.setInterval(() => {
                        if (typeof window.refreshPluginAiRunningIndicators === 'function') {
                            window.refreshPluginAiRunningIndicators();
                        }
                    }, 1000);
                }
                window.updatePluginAiComposerState(!hydratedSnapshot.sending && !!threadId);
            }
        }

        if (!threadId) {
            if (!slug || window.isPluginAiViewCurrent(slug, viewToken)) {
                window.setPluginAiMessagesEmptyView();
                window.setPluginAiActivityEmptyView();
            }
            return { hasPendingRun: false, messages: [] };
        }

        try {
            const params = new URLSearchParams({
                plugin_slug: slug,
                is_theme: String(!!state.isTheme),
            });
            params.set('_ts', String(Date.now()));
            const response = await fetch(`/api/ai/threads/${threadId}/messages?${params.toString()}`, {
                cache: 'no-store',
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || `HTTP ${response.status}`);
            }
            if (slug && !window.isPluginAiViewCurrent(slug, viewToken)) {
                return { hasPendingRun: false, messages: [] };
            }
            const messages = window.extractPluginAiMessages(data);
            const hydratedMessages = Array.isArray(messages) ? [...messages] : [];
            const hasPendingRun = !!data.has_pending_run;
            const pendingSnapshot = typeof window.getPluginAiPendingSnapshot === 'function'
                ? window.getPluginAiPendingSnapshot(slug, threadId, !!state.isTheme)
                : null;
            const pendingSnapshotContent = String(pendingSnapshot?.content || '').trim();
            const hasSameUserMessage = !!pendingSnapshotContent && hydratedMessages.some((item) => {
                const role = String(item?.role || '').trim();
                const content = String(item?.content || '').trim();
                return role === 'user' && content === pendingSnapshotContent;
            });
            const isActiveStreamThread = !!state.sending
                && Number(state.streamThreadId || 0) === Number(threadId || 0)
                && !!String(state.streamRequestId || '').trim();
            const shouldPreserveOptimisticState = !hasPendingRun && !!pendingSnapshotContent && !hasSameUserMessage;
            if (hasSameUserMessage && typeof window.clearPluginAiPendingSnapshot === 'function') {
                window.clearPluginAiPendingSnapshot(slug, threadId, !!state.isTheme);
            }
            if (pendingSnapshotContent && !hasSameUserMessage) {
                hydratedMessages.push({
                    id: `pending-user-${threadId}`,
                    thread_id: threadId,
                    role: 'user',
                    content: pendingSnapshotContent,
                    created_at: pendingSnapshot.createdAt || new Date().toISOString(),
                    tool_calls: [],
                    tool_results: [],
                });
            }
            if (hasPendingRun || shouldPreserveOptimisticState || isActiveStreamThread) {
                if (!hydratedMessages.some((item) => item?.is_pending_assistant)) {
                    hydratedMessages.push({
                        id: `pending-refresh-${threadId}`,
                        thread_id: threadId,
                        role: 'assistant',
                        content: '',
                        created_at: new Date().toISOString(),
                        tool_calls: [],
                        tool_results: [],
                        is_pending_assistant: true,
                    });
                }
                if (!String(state.runStartedAt || '').trim()) {
                    state.runStartedAt = String(pendingSnapshot?.createdAt || new Date().toISOString());
                }
                state.sending = true;
                window.setPluginAiRunningBadge();
                if (!silent) {
                    window.setPluginAiStatus(window.buildPluginAiRunningStatusText(state.runStartedAt));
                }
                if (typeof window.startPluginAiPendingRunPoll === 'function') {
                    window.startPluginAiPendingRunPoll({ slug, threadId, viewToken });
                }
            } else {
                state.sending = false;
                state.runStartedAt = '';
                if (state.runningIndicatorTimer) {
                    window.clearInterval(state.runningIndicatorTimer);
                    state.runningIndicatorTimer = null;
                }
                state.pendingSnapshotRetryInFlight = false;
                if (typeof window.clearPluginAiPendingSnapshot === 'function') {
                    window.clearPluginAiPendingSnapshot(slug, threadId, !!state.isTheme);
                }
                if (typeof window.stopPluginAiPendingRunPoll === 'function') {
                    window.stopPluginAiPendingRunPoll();
                }
            }
            const existingMessages = Array.isArray(state.messages) ? state.messages : [];
            const mergedHydratedMessages = shouldPreserveOptimisticState || isActiveStreamThread
                ? window.mergePluginAiMessages(existingMessages, hydratedMessages)
                : window.mergePluginAiMessages([], hydratedMessages);
            window.capturePluginAiMessages(mergedHydratedMessages);
            state.pendingApproval = data.pending_approval && typeof data.pending_approval === 'object'
                ? data.pending_approval
                : null;
            const persistedTeamEvents = Array.isArray(data.team_events) ? data.team_events : [];
            if (persistedTeamEvents.length) {
                state.events = persistedTeamEvents;
                state.liveActivity = state.events;
                if (typeof window.rememberPluginAiEventsSnapshot === 'function') {
                    window.rememberPluginAiEventsSnapshot({
                        plugin: slug,
                        threadId,
                        isTheme: !!state.isTheme,
                        events: state.liveActivity,
                        createdAt: new Date().toISOString(),
                    });
                }
            } else {
                const cachedEventsSnapshot = typeof window.getPluginAiEventsSnapshot === 'function'
                    ? window.getPluginAiEventsSnapshot(slug, threadId, !!state.isTheme)
                    : null;
                const cachedEvents = Array.isArray(cachedEventsSnapshot?.events) ? cachedEventsSnapshot.events : [];
                if (cachedEvents.length) {
                    state.events = cachedEvents;
                    state.liveActivity = cachedEvents;
                } else {
                    window.capturePluginAiToolAudit(messages);
                    state.liveActivity = state.events;
                }
            }
            window.refreshPluginAiRenderedState();
            if (typeof window.syncCurrentPluginAiThreadSnapshot === 'function') {
                window.syncCurrentPluginAiThreadSnapshot({
                    threadId,
                    messages: state.messages,
                    events: state.events,
                    liveActivity: state.liveActivity,
                    sending: hasPendingRun,
                    pendingApproval: state.pendingApproval,
                });
            }
            if (!hasPendingRun) {
                window.notePluginAiMessagesLoaded(messages);
            }
            return { hasPendingRun, messages };
        } catch (error) {
            if (slug && !window.isPluginAiViewCurrent(slug, viewToken)) {
                return { hasPendingRun: false, messages: [] };
            }
            if (!silent) {
                window.setPluginAiActivityEmptyView();
                window.setPluginAiStatus(`Unable to load AI messages: ${error.message}`);
            }
            return { hasPendingRun: false, messages: [] };
        }
    }

    async function switchPluginAiThread(threadId) {
        const state = window.getPluginAiState();
        const slug = String(state.plugin || '').trim();
        if (!threadId || !slug) return;
        stopPluginAiPendingRunPoll();
        state.threadId = threadId;
        if (typeof window.rememberPluginAiSelectedThread === 'function') {
            window.rememberPluginAiSelectedThread(slug, threadId, !!state.isTheme);
        }
        if (typeof window.hydratePluginAiThreadUiSnapshot === 'function') {
            const snapshot = window.hydratePluginAiThreadUiSnapshot(slug, threadId, !!state.isTheme);
            if (snapshot) {
                window.refreshPluginAiRenderedState();
                window.setPluginAiBadge(snapshot.badgeText || (snapshot.sending ? 'Running' : window.buildPluginAiThreadBadge()));
                window.setPluginAiStatus(snapshot.statusText || (snapshot.sending ? 'Restoring running chat…' : 'Restoring chat…'));
            } else {
                window.setPluginAiThreadLoadingBadge();
                window.setPluginAiStatus('Loading chat messages...');
            }
        } else {
            window.setPluginAiThreadLoadingBadge();
            window.setPluginAiStatus('Loading chat messages...');
        }
        window.updatePluginAiSessionUi();
        const result = await loadPluginAiMessages({ slug, threadId, viewToken: state.viewToken });
        if (window.getPluginAiState().threadId === threadId) {
            const isThreadStreaming = !!state.sending
                && Number(state.streamThreadId || 0) === Number(threadId || 0)
                && !!String(state.streamRequestId || '').trim();
            window.setPluginAiBadge(isThreadStreaming ? 'Running' : window.buildPluginAiThreadBadge());
            window.updatePluginAiComposerState(!isThreadStreaming);
            if (result?.hasPendingRun) {
                startPluginAiPendingRunPoll({ slug, threadId, viewToken: state.viewToken });
            } else {
                startPluginAiThreadSyncPoll({ slug, threadId, viewToken: state.viewToken });
            }
        }
    }

    async function createNewPluginAiThread() {
        const state = window.getPluginAiState();
        const slug = String(state.plugin || '').trim();
        if (!slug || state.loading) return;

        try {
            state.pendingSnapshotRetryInFlight = false;
            if (typeof window.stopPluginAiPendingRunPoll === 'function') {
                window.stopPluginAiPendingRunPoll();
            }
            window.setPluginAiStatus('Creating new chat...');
            const response = await fetch('/api/ai/threads/plugin/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(window.buildPluginThreadRequest({ slug, is_theme: state.isTheme })),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || `HTTP ${response.status}`);
            }
            await loadPluginAiThreads({ slug, is_theme: state.isTheme }, { viewToken: state.viewToken });
            stopPluginAiThreadSyncPoll();
            window.rememberPluginAiThread(data);
            window.clearPluginAiTransientState(state);
            window.refreshPluginAiRenderedState();
            window.updatePluginAiSessionUi();
            window.setPluginAiBadge(window.buildPluginAiThreadBadge());
            window.setPluginAiStatus('New chat ready.');
        } catch (error) {
            window.setPluginAiErrorBadge();
            window.setPluginAiStatus(`Unable to create new chat: ${error.message}`);
        }
    }

    async function ensurePluginAiThread(plugin) {
        const slug = String(plugin?.slug || '').trim();
        if (!slug) return null;

        if (typeof window.stopPluginAiPendingRunPoll === 'function') {
            window.stopPluginAiPendingRunPoll();
        }

        const state = window.getPluginAiState();
        if (window.currentPluginMatchesState(plugin, state) && state.threadId) {
            return state.threadId;
        }

        const previousThreadId = Number(state.threadId || 0) || null;
        const previousSnapshot = typeof window.getPluginAiThreadUiSnapshot === 'function'
            ? window.getPluginAiThreadUiSnapshot(slug, previousThreadId, !!plugin?.is_theme)
            : null;
        const viewToken = window.startPluginAiView(plugin);
        state.loading = true;
        if (!(previousSnapshot && Array.isArray(previousSnapshot.messages) && previousSnapshot.messages.length)) {
            window.setPluginAiMessagesEmptyView();
            window.setPluginAiActivityEmptyView();
        }
        window.setPluginAiThreadLoadingBadge();
        window.setPluginAiThreadStatusLoading(plugin);
        window.updatePluginAiComposerState(false);

        try {
            let threads = await loadPluginAiThreads(plugin, { viewToken, isTheme: !!plugin?.is_theme });
            if (!window.isPluginAiViewCurrent(slug, viewToken)) {
                return null;
            }

            const rememberedThreadId = typeof window.getPluginAiSelectedThread === 'function'
                ? window.getPluginAiSelectedThread(slug, !!plugin?.is_theme)
                : null;
            let threadId = Array.isArray(threads)
                ? (threads.find((item) => Number(item?.id || 0) === Number(rememberedThreadId || 0))?.id || null)
                : null;
            if (!threadId) {
                threadId = window.resolvePreferredPluginAiThreadId(threads);
            }
            if (!threadId) {
                const response = await fetch('/api/ai/threads/plugin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(window.buildPluginThreadRequest(plugin)),
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(data.detail || `HTTP ${response.status}`);
                }
                threads = [data];
                window.rememberPluginAiThreads(threads);
                window.renderPluginAiSessions(threads, data.id);
                window.rememberPluginAiThread(data);
                threadId = data.id;
            } else {
                const activeThread = Array.isArray(threads) ? threads.find((item) => Number(item?.id || 0) === Number(threadId || 0)) : null;
                window.rememberPluginAiThread(activeThread || { id: threadId, is_theme: !!plugin?.is_theme });
            }

            if (!threadId || !window.isPluginAiViewCurrent(slug, viewToken)) {
                return null;
            }

            window.updatePluginAiSessionUi();
            window.setPluginAiBadge(window.buildPluginAiThreadBadge());
            window.setPluginAiThreadReadyStatus();
            const result = await loadPluginAiMessages({ slug, threadId, viewToken });
            if (!window.isPluginAiViewCurrent(slug, viewToken)) {
                return null;
            }
            if (result?.hasPendingRun) {
                startPluginAiPendingRunPoll({ slug, threadId, viewToken });
                window.updatePluginAiComposerState(false);
            } else {
                stopPluginAiPendingRunPoll();
                startPluginAiThreadSyncPoll({ slug, threadId, viewToken });
                window.updatePluginAiComposerState(true);
            }
            return threadId;
        } catch (error) {
            if (!window.isPluginAiViewCurrent(slug, viewToken)) {
                return null;
            }
            window.setPluginAiErrorBadge();
            window.setPluginAiStatus(`Unable to load AI chat: ${error.message}`);
            window.setPluginAiMessagesEmptyView();
            window.updatePluginAiComposerState(!!state.threadId);
            return null;
        } finally {
            if (window.isPluginAiViewCurrent(slug, viewToken)) {
                state.loading = false;
            }
        }
    }

    window.stopPluginAiThreadSyncPoll = stopPluginAiThreadSyncPoll;
    window.startPluginAiThreadSyncPoll = startPluginAiThreadSyncPoll;
    window.stopPluginAiPendingRunPoll = stopPluginAiPendingRunPoll;
    window.startPluginAiPendingRunPoll = startPluginAiPendingRunPoll;
    window.loadPluginAiThreads = loadPluginAiThreads;
    window.loadPluginAiMessages = loadPluginAiMessages;
    window.switchPluginAiThread = switchPluginAiThread;
    window.createNewPluginAiThread = createNewPluginAiThread;
    window.ensurePluginAiThread = ensurePluginAiThread;
})();
