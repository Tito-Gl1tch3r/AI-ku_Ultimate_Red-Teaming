(function() {
    function getCurrentScanId() {
        return typeof window.getCurrentScanId === 'function' ? window.getCurrentScanId() : null;
    }

    function escapeOption(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    const PLUGIN_AI_PENDING_STORAGE_KEY = 'temodarAgentPluginAiPending';
    const PLUGIN_AI_EVENTS_STORAGE_KEY = 'temodarAgentPluginAiLiveEvents';
    const PLUGIN_AI_SELECTED_THREAD_STORAGE_KEY = 'temodarAgentPluginAiSelectedThread';
    const PLUGIN_AI_THREAD_UI_STORAGE_KEY = 'temodarAgentPluginAiThreadUi';
    const PLUGIN_AI_RUNTIME_PREFS_STORAGE_KEY = 'temodarAgentPluginAiRuntimePrefs';

    const DEFAULT_PLUGIN_AI_RUNTIME_PREFS = {
        strategy: 'auto',
        loop_mode: '',
        trace_enabled: false,
        structured_enabled: false,
        output_schema_text: '',
        tasks_json_text: '',
        approval_mode: 'manual',
        retry_preset: '',
        fanout_json_text: '',
        before_run_json_text: '',
        after_run_json_text: '',
    };

    function normalizePluginAiStrategy(value) {
        const normalized = String(value || 'auto').trim().toLowerCase();
        return normalized || 'auto';
    }

    function getPluginAiAllowedApprovalModes(strategy = 'auto') {
        const normalizedStrategy = normalizePluginAiStrategy(strategy);
        if (normalizedStrategy === 'tasks') {
            return ['manual', 'auto_approve', 'off'];
        }
        return ['manual', 'off'];
    }

    function normalizePluginAiApprovalMode(value, strategy = 'auto') {
        const normalized = String(value || 'manual').trim().toLowerCase();
        const allowed = getPluginAiAllowedApprovalModes(strategy);
        if (allowed.includes(normalized)) return normalized;
        return allowed[0] || 'manual';
    }

    function syncPluginAiApprovalModeUi(preferredValue = null) {
        const strategyEl = document.getElementById('plugin-ai-strategy');
        const approvalEl = document.getElementById('plugin-ai-approval-mode');
        if (!approvalEl) return 'manual';

        const strategyValue = normalizePluginAiStrategy(strategyEl?.value || 'auto');
        const allowedModes = getPluginAiAllowedApprovalModes(strategyValue);
        const labels = {
            manual: 'Manual gate',
            auto_approve: 'Auto approve',
            off: 'Off (YOLO • Dangerous)',
        };
        const current = preferredValue != null ? String(preferredValue).trim() : String(approvalEl.value || '').trim();
        const normalized = normalizePluginAiApprovalMode(current, strategyValue);

        approvalEl.innerHTML = allowedModes
            .map((mode) => `<option value="${escapeOption(mode)}">${escapeOption(labels[mode] || mode)}</option>`)
            .join('');
        approvalEl.value = normalized;
        return normalized;
    }

    function getPluginAiState() {
        return window.currentPluginAi || {};
    }

    function buildPluginAiPendingStorageKey(plugin, threadId, isTheme = false) {
        return [
            String(plugin || '').trim(),
            String(threadId || '').trim(),
            isTheme ? 'theme' : 'plugin',
        ].join('::');
    }

    function buildPluginAiScopeStorageKey(plugin, isTheme = false) {
        return [
            String(plugin || '').trim(),
            isTheme ? 'theme' : 'plugin',
        ].join('::');
    }

    function readPluginAiSelectedThreadSnapshot() {
        try {
            const raw = window.sessionStorage?.getItem(PLUGIN_AI_SELECTED_THREAD_STORAGE_KEY);
            if (!raw) return {};
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    function readPluginAiThreadUiSnapshotMap() {
        try {
            const raw = window.sessionStorage?.getItem(PLUGIN_AI_THREAD_UI_STORAGE_KEY);
            if (!raw) return {};
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    function writePluginAiThreadUiSnapshotMap(map) {
        try {
            if (!map || typeof map !== 'object' || !window.sessionStorage) return;
            window.sessionStorage.setItem(PLUGIN_AI_THREAD_UI_STORAGE_KEY, JSON.stringify(map));
        } catch (_error) {
            // ignore storage failures
        }
    }

    function writePluginAiSelectedThreadSnapshotMap(map) {
        try {
            if (!map || typeof map !== 'object' || !window.sessionStorage) return;
            window.sessionStorage.setItem(PLUGIN_AI_SELECTED_THREAD_STORAGE_KEY, JSON.stringify(map));
        } catch (_error) {
            // ignore storage failures
        }
    }

    function rememberPluginAiSelectedThread(plugin, threadId, isTheme = false) {
        const key = buildPluginAiScopeStorageKey(plugin, isTheme);
        if (!key.replace(/:/g, '').trim()) return null;
        const safeThreadId = Number(threadId || 0) || null;
        const map = readPluginAiSelectedThreadSnapshot();
        if (!safeThreadId) {
            delete map[key];
            writePluginAiSelectedThreadSnapshotMap(map);
            return null;
        }
        map[key] = {
            plugin: String(plugin || '').trim(),
            threadId: safeThreadId,
            isTheme: !!isTheme,
            updatedAt: new Date().toISOString(),
        };
        writePluginAiSelectedThreadSnapshotMap(map);
        return map[key];
    }

    function getPluginAiSelectedThread(plugin, isTheme = false) {
        const key = buildPluginAiScopeStorageKey(plugin, isTheme);
        const item = readPluginAiSelectedThreadSnapshot()[key] || null;
        return Number(item?.threadId || 0) || null;
    }

    function rememberPluginAiThreadUiSnapshot(snapshot = {}) {
        const state = getPluginAiState();
        const plugin = String(snapshot.plugin || state.plugin || '').trim();
        const threadId = Number(snapshot.threadId || state.threadId || 0) || null;
        const isTheme = !!(snapshot.isTheme ?? state.isTheme);
        const key = buildPluginAiPendingStorageKey(plugin, threadId, isTheme);
        if (!plugin || !threadId || !key.replace(/:/g, '').trim()) return null;
        const map = readPluginAiThreadUiSnapshotMap();
        map[key] = {
            plugin,
            threadId,
            isTheme,
            messages: Array.isArray(snapshot.messages) ? snapshot.messages : (Array.isArray(state.messages) ? state.messages : []),
            events: Array.isArray(snapshot.events) ? snapshot.events : (Array.isArray(state.events) ? state.events : []),
            liveActivity: Array.isArray(snapshot.liveActivity) ? snapshot.liveActivity : (Array.isArray(state.liveActivity) ? state.liveActivity : []),
            sending: Object.prototype.hasOwnProperty.call(snapshot, 'sending') ? !!snapshot.sending : !!state.sending,
            runStartedAt: String(snapshot.runStartedAt ?? state.runStartedAt ?? '').trim(),
            statusText: String(snapshot.statusText ?? state.statusText ?? '').trim(),
            badgeText: String(snapshot.badgeText ?? state.badgeText ?? '').trim(),
            sourceStatus: snapshot.sourceStatus && typeof snapshot.sourceStatus === 'object'
                ? snapshot.sourceStatus
                : (state.sourceStatus && typeof state.sourceStatus === 'object' ? state.sourceStatus : {}),
            pendingApproval: snapshot.pendingApproval && typeof snapshot.pendingApproval === 'object'
                ? snapshot.pendingApproval
                : (state.pendingApproval && typeof state.pendingApproval === 'object' ? state.pendingApproval : null),
            updatedAt: new Date().toISOString(),
        };
        writePluginAiThreadUiSnapshotMap(map);
        return map[key];
    }

    function getPluginAiThreadUiSnapshot(plugin, threadId, isTheme = false) {
        const key = buildPluginAiPendingStorageKey(plugin, threadId, isTheme);
        return readPluginAiThreadUiSnapshotMap()[key] || null;
    }

    function hydratePluginAiThreadUiSnapshot(plugin, threadId, isTheme = false) {
        const state = getPluginAiState();
        const snapshot = getPluginAiThreadUiSnapshot(plugin, threadId, isTheme);
        if (!snapshot) return null;
        state.plugin = String(plugin || state.plugin || '').trim();
        state.threadId = Number(threadId || state.threadId || 0) || null;
        state.isTheme = !!isTheme;
        state.messages = Array.isArray(snapshot.messages) ? snapshot.messages : [];
        state.events = Array.isArray(snapshot.events) ? snapshot.events : [];
        state.liveActivity = Array.isArray(snapshot.liveActivity) ? snapshot.liveActivity : (Array.isArray(snapshot.events) ? snapshot.events : []);
        state.sending = !!snapshot.sending;
        state.runStartedAt = String(snapshot.runStartedAt || '').trim();
        state.statusText = String(snapshot.statusText || '').trim();
        state.badgeText = String(snapshot.badgeText || '').trim();
        state.sourceStatus = snapshot.sourceStatus && typeof snapshot.sourceStatus === 'object'
            ? snapshot.sourceStatus
            : (state.sourceStatus || {});
        state.pendingApproval = snapshot.pendingApproval && typeof snapshot.pendingApproval === 'object'
            ? snapshot.pendingApproval
            : null;
        return snapshot;
    }

    function syncCurrentPluginAiThreadSnapshot(overrides = {}) {
        const state = getPluginAiState();
        const threadId = Number(overrides.threadId || state.threadId || 0) || null;
        if (!threadId) return null;
        return rememberPluginAiThreadUiSnapshot({
            plugin: String(overrides.plugin || state.plugin || '').trim(),
            threadId,
            isTheme: !!(overrides.isTheme ?? state.isTheme),
            messages: Array.isArray(overrides.messages) ? overrides.messages : state.messages,
            events: Array.isArray(overrides.events) ? overrides.events : state.events,
            liveActivity: Array.isArray(overrides.liveActivity) ? overrides.liveActivity : state.liveActivity,
            sending: Object.prototype.hasOwnProperty.call(overrides, 'sending') ? !!overrides.sending : !!state.sending,
            runStartedAt: Object.prototype.hasOwnProperty.call(overrides, 'runStartedAt') ? overrides.runStartedAt : state.runStartedAt,
            statusText: Object.prototype.hasOwnProperty.call(overrides, 'statusText') ? overrides.statusText : state.statusText,
            badgeText: Object.prototype.hasOwnProperty.call(overrides, 'badgeText') ? overrides.badgeText : state.badgeText,
            sourceStatus: overrides.sourceStatus || state.sourceStatus,
            pendingApproval: Object.prototype.hasOwnProperty.call(overrides, 'pendingApproval') ? overrides.pendingApproval : state.pendingApproval,
        });
    }

    function readPluginAiPendingSnapshot() {
        try {
            const raw = window.sessionStorage?.getItem(PLUGIN_AI_PENDING_STORAGE_KEY);
            if (!raw) return {};
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    function writePluginAiPendingSnapshotMap(map) {
        try {
            if (!map || typeof map !== 'object' || !window.sessionStorage) return;
            window.sessionStorage.setItem(PLUGIN_AI_PENDING_STORAGE_KEY, JSON.stringify(map));
        } catch (_error) {
            // ignore storage failures
        }
    }

    function readPluginAiEventsSnapshot() {
        try {
            const raw = window.sessionStorage?.getItem(PLUGIN_AI_EVENTS_STORAGE_KEY);
            if (!raw) return {};
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    function writePluginAiEventsSnapshotMap(map) {
        try {
            if (!map || typeof map !== 'object' || !window.sessionStorage) return;
            window.sessionStorage.setItem(PLUGIN_AI_EVENTS_STORAGE_KEY, JSON.stringify(map));
        } catch (_error) {
            // ignore storage failures
        }
    }

    function rememberPluginAiEventsSnapshot(snapshot = {}) {
        const state = getPluginAiState();
        const key = buildPluginAiPendingStorageKey(snapshot.plugin || state.plugin, snapshot.threadId || state.threadId, snapshot.isTheme ?? state.isTheme);
        if (!key.replace(/:/g, '').trim()) return null;
        const events = Array.isArray(snapshot.events) ? snapshot.events : [];
        const map = readPluginAiEventsSnapshot();
        map[key] = {
            plugin: String(snapshot.plugin || state.plugin || '').trim(),
            threadId: Number(snapshot.threadId || state.threadId || 0) || null,
            isTheme: !!(snapshot.isTheme ?? state.isTheme),
            events: events,
            createdAt: String(snapshot.createdAt || new Date().toISOString()),
        };
        writePluginAiEventsSnapshotMap(map);
        return map[key];
    }

    function getPluginAiEventsSnapshot(plugin, threadId, isTheme = false) {
        const key = buildPluginAiPendingStorageKey(plugin, threadId, isTheme);
        return readPluginAiEventsSnapshot()[key] || null;
    }

    function clearPluginAiEventsSnapshot(plugin, threadId, isTheme = false) {
        const key = buildPluginAiPendingStorageKey(plugin, threadId, isTheme);
        const map = readPluginAiEventsSnapshot();
        if (!Object.prototype.hasOwnProperty.call(map, key)) return;
        delete map[key];
        writePluginAiEventsSnapshotMap(map);
    }

    function rememberPluginAiPendingSnapshot(snapshot = {}) {
        const state = getPluginAiState();
        const key = buildPluginAiPendingStorageKey(snapshot.plugin || state.plugin, snapshot.threadId || state.threadId, snapshot.isTheme ?? state.isTheme);
        if (!key.replace(/:/g, '').trim()) return null;
        const map = readPluginAiPendingSnapshot();
        map[key] = {
            plugin: String(snapshot.plugin || state.plugin || '').trim(),
            threadId: Number(snapshot.threadId || state.threadId || 0) || null,
            isTheme: !!(snapshot.isTheme ?? state.isTheme),
            content: String(snapshot.content || '').trim(),
            createdAt: String(snapshot.createdAt || new Date().toISOString()),
        };
        writePluginAiPendingSnapshotMap(map);
        return map[key];
    }

    function getPluginAiPendingSnapshot(plugin, threadId, isTheme = false) {
        const key = buildPluginAiPendingStorageKey(plugin, threadId, isTheme);
        return readPluginAiPendingSnapshot()[key] || null;
    }

    function clearPluginAiPendingSnapshot(plugin, threadId, isTheme = false) {
        const key = buildPluginAiPendingStorageKey(plugin, threadId, isTheme);
        const map = readPluginAiPendingSnapshot();
        if (!Object.prototype.hasOwnProperty.call(map, key)) return;
        delete map[key];
        writePluginAiPendingSnapshotMap(map);
    }

    function beginPluginAiView(slug, isTheme = false) {
        const state = getPluginAiState();
        state.plugin = String(slug || '').trim();
        state.isTheme = !!isTheme;
        state.threadId = null;
        state.threads = [];
        state.messages = [];
        state.events = [];
        state.liveActivity = [];
        state.loading = false;
        state.sending = false;
        state.sourcePreparing = false;
        state.streamRequestId = null;
        state.streamThreadId = null;
        state.pendingSnapshotRetryInFlight = false;
        state.runStartedAt = '';
        state.statusText = '';
        state.badgeText = '';
        state.sourceStatus = {
            source_available: false,
            source_context_mode: 'metadata_only',
            source_path: '',
            workspace_path: '',
        };
        if (typeof window.stopPluginAiPendingRunPoll === 'function') {
            window.stopPluginAiPendingRunPoll();
        }
        if (typeof window.stopPluginAiThreadSyncPoll === 'function') {
            window.stopPluginAiThreadSyncPoll();
        }
        state.viewToken = (Number(state.viewToken) || 0) + 1;
        if (typeof window.updatePluginAiSessionUi === 'function') {
            window.updatePluginAiSessionUi();
        }
        return state.viewToken;
    }

    function currentPluginMatchesState(plugin, state) {
        const slug = String(plugin?.slug || '').trim();
        return state.plugin === slug && state.isTheme === !!plugin?.is_theme;
    }

    function isPluginAiViewCurrent(slug, token) {
        const state = getPluginAiState();
        return state.plugin === String(slug || '').trim() && state.viewToken === token;
    }

    function shouldIgnorePluginAiResponse(slug, viewToken, threadId) {
        const state = getPluginAiState();
        return !isPluginAiViewCurrent(slug, viewToken)
            || Number(state.threadId || 0) !== Number(threadId || 0);
    }

    function clearPluginAiTransientState(state) {
        state.messages = [];
        state.events = [];
        state.liveActivity = [];
        state.streamRequestId = null;
        state.streamThreadId = null;
        state.pendingSnapshotRetryInFlight = false;
        state.liveActivityOptions = {};
        state.ui = {
            activityExpanded: false,
            summaryExpanded: false,
            traceExpanded: false,
        };
    }

    function ensurePluginAiUiState() {
        const state = getPluginAiState();
        if (!state.ui || typeof state.ui !== 'object') {
            state.ui = {
                activityExpanded: false,
                summaryExpanded: false,
                traceExpanded: false,
            };
        }
        return state.ui;
    }

    function togglePluginAiUiFlag(key) {
        const ui = ensurePluginAiUiState();
        ui[key] = !ui[key];
        return ui[key];
    }

    function setPluginAiUiFlag(key, value) {
        const ui = ensurePluginAiUiState();
        ui[key] = !!value;
        return ui[key];
    }

    function setPluginAiLiveActivityOptions(options = {}) {
        const state = getPluginAiState();
        state.liveActivityOptions = options && typeof options === 'object' ? { ...options } : {};
        return state.liveActivityOptions;
    }

    function beginPluginAiStreamRequest(threadId = null) {
        const state = getPluginAiState();
        const nextId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        state.streamRequestId = nextId;
        state.streamThreadId = Number(threadId || state.threadId || 0) || null;
        return nextId;
    }

    function isCurrentPluginAiStreamRequest(requestId) {
        return String(getPluginAiState().streamRequestId || '') === String(requestId || '');
    }

    function endPluginAiStreamRequest(requestId) {
        const state = getPluginAiState();
        if (!requestId || isCurrentPluginAiStreamRequest(requestId)) {
            state.streamRequestId = null;
            state.streamThreadId = null;
        }
    }

    function resetPluginAiThreadState(plugin) {
        const state = getPluginAiState();
        state.plugin = String(plugin?.slug || '').trim();
        state.isTheme = !!plugin?.is_theme;
        state.threadId = null;
        state.threads = [];
        clearPluginAiTransientState(state);
        if (typeof window.updatePluginAiSessionUi === 'function') {
            window.updatePluginAiSessionUi();
        }
    }

    function startPluginAiView(plugin) {
        const token = beginPluginAiView(String(plugin?.slug || '').trim(), !!plugin?.is_theme);
        resetPluginAiThreadState(plugin);
        return token;
    }

    function buildPluginThreadRequest(plugin) {
        return {
            plugin_slug: String(plugin?.slug || '').trim(),
            is_theme: !!plugin?.is_theme,
            title: null,
            last_scan_session_id: getCurrentScanId() || null,
        };
    }

    function parsePluginAiJsonField(elementId, label, fallback = null) {
        const raw = String(document.getElementById(elementId)?.value || '').trim();
        if (!raw) return fallback;
        try {
            return JSON.parse(raw);
        } catch (_error) {
            throw new Error(`${label} must be valid JSON.`);
        }
    }

    function applyRetryPreset(tasks = [], preset = '') {
        const normalized = String(preset || '').trim();
        if (!normalized || !Array.isArray(tasks) || !tasks.length) return tasks;
        const presets = {
            light: { maxRetries: 1, retryDelayMs: 750, retryBackoff: 1.5 },
            normal: { maxRetries: 2, retryDelayMs: 1000, retryBackoff: 2 },
            aggressive: { maxRetries: 3, retryDelayMs: 1500, retryBackoff: 2 },
        };
        const chosen = presets[normalized];
        if (!chosen) return tasks;
        return tasks.map((task) => ({ ...task, ...chosen, ...(task && typeof task === 'object' ? task : {}) }));
    }

    function readPluginAiRuntimePrefsStorage() {
        try {
            const raw = window.localStorage?.getItem(PLUGIN_AI_RUNTIME_PREFS_STORAGE_KEY);
            if (!raw) return { ...DEFAULT_PLUGIN_AI_RUNTIME_PREFS };
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object'
                ? { ...DEFAULT_PLUGIN_AI_RUNTIME_PREFS, ...parsed }
                : { ...DEFAULT_PLUGIN_AI_RUNTIME_PREFS };
        } catch (_error) {
            return { ...DEFAULT_PLUGIN_AI_RUNTIME_PREFS };
        }
    }

    function collectPluginAiRuntimePrefsFromDom() {
        const strategy = normalizePluginAiStrategy(document.getElementById('plugin-ai-strategy')?.value || DEFAULT_PLUGIN_AI_RUNTIME_PREFS.strategy);
        const approval_mode = normalizePluginAiApprovalMode(
            document.getElementById('plugin-ai-approval-mode')?.value || DEFAULT_PLUGIN_AI_RUNTIME_PREFS.approval_mode,
            strategy,
        );
        return {
            strategy,
            loop_mode: String(document.getElementById('plugin-ai-loop-mode')?.value || DEFAULT_PLUGIN_AI_RUNTIME_PREFS.loop_mode).trim(),
            trace_enabled: !!document.getElementById('plugin-ai-trace-enabled')?.checked,
            structured_enabled: !!document.getElementById('plugin-ai-structured-enabled')?.checked,
            output_schema_text: String(document.getElementById('plugin-ai-output-schema')?.value || '').trim(),
            tasks_json_text: String(document.getElementById('plugin-ai-tasks-json')?.value || '').trim(),
            approval_mode,
            retry_preset: String(document.getElementById('plugin-ai-retry-preset')?.value || '').trim(),
            fanout_json_text: String(document.getElementById('plugin-ai-fanout-json')?.value || '').trim(),
            before_run_json_text: String(document.getElementById('plugin-ai-before-run-json')?.value || '').trim(),
            after_run_json_text: String(document.getElementById('plugin-ai-after-run-json')?.value || '').trim(),
        };
    }

    function persistPluginAiRuntimePrefs() {
        try {
            const prefs = collectPluginAiRuntimePrefsFromDom();
            window.localStorage?.setItem(PLUGIN_AI_RUNTIME_PREFS_STORAGE_KEY, JSON.stringify(prefs));
            return prefs;
        } catch (_error) {
            return null;
        }
    }

    function applyPluginAiRuntimePrefsToDom(prefs = null) {
        const safePrefs = prefs && typeof prefs === 'object'
            ? { ...DEFAULT_PLUGIN_AI_RUNTIME_PREFS, ...prefs }
            : readPluginAiRuntimePrefsStorage();
        safePrefs.strategy = normalizePluginAiStrategy(safePrefs.strategy || 'auto');
        safePrefs.approval_mode = normalizePluginAiApprovalMode(safePrefs.approval_mode || 'manual', safePrefs.strategy);
        const mappings = [
            ['plugin-ai-strategy', safePrefs.strategy],
            ['plugin-ai-loop-mode', safePrefs.loop_mode],
            ['plugin-ai-output-schema', safePrefs.output_schema_text],
            ['plugin-ai-tasks-json', safePrefs.tasks_json_text],
            ['plugin-ai-retry-preset', safePrefs.retry_preset],
            ['plugin-ai-fanout-json', safePrefs.fanout_json_text],
            ['plugin-ai-before-run-json', safePrefs.before_run_json_text],
            ['plugin-ai-after-run-json', safePrefs.after_run_json_text],
        ];
        mappings.forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (!element) return;
            element.value = value ?? '';
        });
        safePrefs.approval_mode = syncPluginAiApprovalModeUi(safePrefs.approval_mode || 'manual');
        const traceEl = document.getElementById('plugin-ai-trace-enabled');
        if (traceEl) traceEl.checked = !!safePrefs.trace_enabled;
        const structuredEl = document.getElementById('plugin-ai-structured-enabled');
        if (structuredEl) structuredEl.checked = !!safePrefs.structured_enabled;
        const state = getPluginAiState();
        state.runtimeOverrides = {
            strategy: safePrefs.strategy || 'auto',
            trace_enabled: !!safePrefs.trace_enabled,
            output_schema: null,
            tasks: [],
            fanout: null,
            loop_detection: safePrefs.loop_mode
                ? {
                    maxRepetitions: 3,
                    loopDetectionWindow: 5,
                    onLoopDetected: safePrefs.loop_mode,
                }
                : null,
            approval_mode: safePrefs.approval_mode || 'manual',
        };
        return safePrefs;
    }

    function hydratePluginAiRuntimePrefs() {
        const prefs = applyPluginAiRuntimePrefsToDom(readPluginAiRuntimePrefsStorage());
        if (typeof window.refreshPluginAiRuntimeSummary === 'function') {
            window.refreshPluginAiRuntimeSummary();
        }
        return prefs;
    }

    function readPluginAiRuntimeOverrides() {
        const strategy = normalizePluginAiStrategy(document.getElementById('plugin-ai-strategy')?.value || 'auto');
        const traceEnabled = !!document.getElementById('plugin-ai-trace-enabled')?.checked;
        const structuredEnabled = !!document.getElementById('plugin-ai-structured-enabled')?.checked;
        const loopMode = String(document.getElementById('plugin-ai-loop-mode')?.value || '').trim();
        const approvalMode = normalizePluginAiApprovalMode(document.getElementById('plugin-ai-approval-mode')?.value || 'manual', strategy);
        const retryPreset = String(document.getElementById('plugin-ai-retry-preset')?.value || '').trim();
        const outputSchema = structuredEnabled
            ? parsePluginAiJsonField('plugin-ai-output-schema', 'Output schema', { type: 'object', properties: { summary: { type: 'string' } } })
            : null;
        const rawTasks = parsePluginAiJsonField('plugin-ai-tasks-json', 'Tasks JSON', []);
        const tasks = applyRetryPreset(Array.isArray(rawTasks) ? rawTasks : [], retryPreset);
        const fanout = parsePluginAiJsonField('plugin-ai-fanout-json', 'Fanout JSON', null);
        const beforeRun = parsePluginAiJsonField('plugin-ai-before-run-json', 'Before-run hook JSON', null);
        const afterRun = parsePluginAiJsonField('plugin-ai-after-run-json', 'After-run hook JSON', null);
        const loopDetection = loopMode
            ? {
                maxRepetitions: 3,
                loopDetectionWindow: 5,
                onLoopDetected: loopMode,
            }
            : null;
        const runtimeOverrides = {
            strategy,
            trace_enabled: traceEnabled,
            output_schema: outputSchema,
            tasks,
            fanout: fanout && typeof fanout === 'object' ? fanout : null,
            loop_detection: loopDetection,
            approval_mode: approvalMode,
            before_run: beforeRun && typeof beforeRun === 'object' ? beforeRun : null,
            after_run: afterRun && typeof afterRun === 'object' ? afterRun : null,
        };
        const state = getPluginAiState();
        state.runtimeOverrides = runtimeOverrides;
        return runtimeOverrides;
    }

    function formatPluginAiStrategyLabel(value) {
        const normalized = String(value || 'auto').trim().toLowerCase();
        const labels = {
            auto: 'Auto',
            agent: 'Agent',
            team: 'Team',
            tasks: 'Tasks',
            fanout: 'Fan-out',
        };
        return labels[normalized] || 'Auto';
    }

    function formatPluginAiApprovalLabel(value) {
        const normalized = String(value || 'manual').trim().toLowerCase();
        const labels = {
            off: 'Off (YOLO • Dangerous)',
            auto_approve: 'Auto',
            manual: 'Manual',
        };
        return labels[normalized] || 'Manual';
    }

    function buildPluginAiStrategyTooltip(value) {
        const normalized = String(value || 'auto').trim().toLowerCase();
        const descriptions = {
            auto: 'Auto picks the best execution style for the prompt.',
            agent: 'Single agent uses one focused AI worker.',
            team: 'Team uses multiple collaborating AI roles.',
            tasks: 'Tasks runs a step-by-step task pipeline.',
            fanout: 'Fan-out runs parallel branches and combines results.',
        };
        return `Strategy: ${formatPluginAiStrategyLabel(normalized)}. ${descriptions[normalized] || descriptions.auto} Click to change.`;
    }

    function buildPluginAiApprovalTooltip(value, strategy = 'auto') {
        const normalized = String(value || 'manual').trim().toLowerCase();
        const normalizedStrategy = normalizePluginAiStrategy(strategy);
        const descriptions = {
            manual: 'The run pauses and asks for your approval before gated steps continue.',
            auto_approve: 'Approval checks are accepted automatically.',
            off: 'YOLO mode: no approval pause is used. This is dangerous because risky tool calls (write/edit/bash/network/delete) can run immediately without a human checkpoint.',
        };
        const suffix = normalizedStrategy === 'tasks'
            ? 'Click to change.'
            : 'Click to change. (Auto approve is available only for Task pipeline.)';
        return `Approval: ${formatPluginAiApprovalLabel(normalized)}. ${descriptions[normalized] || descriptions.manual} ${suffix}`;
    }

    function refreshPluginAiRuntimeSummary() {
        const strategyEl = document.getElementById('plugin-ai-strategy');
        const approvalEl = document.getElementById('plugin-ai-approval-mode');
        const strategyChip = document.getElementById('plugin-ai-runtime-strategy-chip');
        const approvalChip = document.getElementById('plugin-ai-runtime-approval-chip');
        const strategyValue = normalizePluginAiStrategy(strategyEl?.value || 'auto');
        const approvalValue = syncPluginAiApprovalModeUi(approvalEl?.value || 'manual');
        if (strategyChip) {
            strategyChip.textContent = formatPluginAiStrategyLabel(strategyValue);
            strategyChip.dataset.strategy = strategyValue;
            strategyChip.dataset.tooltip = buildPluginAiStrategyTooltip(strategyValue);
            strategyChip.setAttribute('aria-label', buildPluginAiStrategyTooltip(strategyValue));
        }
        if (approvalChip) {
            approvalChip.textContent = formatPluginAiApprovalLabel(approvalValue);
            approvalChip.dataset.approval = approvalValue;
            approvalChip.dataset.tooltip = buildPluginAiApprovalTooltip(approvalValue, strategyValue);
            approvalChip.setAttribute('aria-label', buildPluginAiApprovalTooltip(approvalValue, strategyValue));
        }
    }

    function cyclePluginAiStrategy() {
        const strategyEl = document.getElementById('plugin-ai-strategy');
        if (!strategyEl) return;
        const strategyOrder = ['auto', 'team', 'agent', 'tasks', 'fanout'];
        const currentStrategyIndex = Math.max(0, strategyOrder.indexOf(String(strategyEl.value || 'auto').trim()));
        strategyEl.value = strategyOrder[(currentStrategyIndex + 1) % strategyOrder.length];
        syncPluginAiApprovalModeUi();
        if (typeof window.persistPluginAiRuntimePrefs === 'function') {
            window.persistPluginAiRuntimePrefs();
        }
        refreshPluginAiRuntimeSummary();
        strategyEl.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function cyclePluginAiApprovalMode() {
        const strategyEl = document.getElementById('plugin-ai-strategy');
        const approvalEl = document.getElementById('plugin-ai-approval-mode');
        if (!approvalEl) return;
        const strategyValue = normalizePluginAiStrategy(strategyEl?.value || 'auto');
        const approvalOrder = getPluginAiAllowedApprovalModes(strategyValue);
        const currentApprovalIndex = Math.max(0, approvalOrder.indexOf(String(approvalEl.value || 'manual').trim()));
        approvalEl.value = approvalOrder[(currentApprovalIndex + 1) % approvalOrder.length];
        if (typeof window.persistPluginAiRuntimePrefs === 'function') {
            window.persistPluginAiRuntimePrefs();
        }
        refreshPluginAiRuntimeSummary();
        approvalEl.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function buildPluginAiMessagePayload({ threadId, content }) {
        const state = getPluginAiState();
        return {
            thread_id: threadId,
            content,
            last_scan_session_id: getCurrentScanId() || null,
            plugin_slug: String(state.plugin || '').trim() || undefined,
            is_theme: !!state.isTheme,
            profile_key: String(state.selectedProfileKey || '').trim() || undefined,
            model: String(state.selectedModel || '').trim() || undefined,
            ...readPluginAiRuntimeOverrides(),
        };
    }

    function resolvePreferredPluginAiThreadId(threads = []) {
        const first = Array.isArray(threads) ? threads[0] : null;
        return first && first.id ? first.id : null;
    }

    function rememberPluginAiThread(data = {}) {
        const state = getPluginAiState();
        state.threadId = data.id || null;
        state.isTheme = !!data.is_theme;
        state.sourceStatus = {
            source_available: !!data.source_available,
            source_context_mode: String(data.source_context_mode || 'metadata_only'),
            source_path: String(data.source_path || ''),
            workspace_path: String(data.workspace_path || ''),
        };
        rememberPluginAiSelectedThread(String(data.plugin_slug || state.plugin || '').trim(), state.threadId, !!state.isTheme);
    }

    function rememberPluginAiThreads(threads = []) {
        const state = getPluginAiState();
        state.threads = Array.isArray(threads) ? threads : [];
    }

    function extractCurrentAiConfig() {
        return window.currentAiConfig || {};
    }

    function syncPluginAiProfileSelections() {
        const state = getPluginAiState();
        const profiles = Array.isArray(state.profiles) ? state.profiles : [];
        const activeProfile = window.currentAiConfig || null;
        const preferredProfileKey = String(state.selectedProfileKey || activeProfile?.profile_key || profiles[0]?.profile_key || '').trim();
        const selectedProfile = profiles.find((item) => String(item.profile_key || '') === preferredProfileKey) || activeProfile || profiles[0] || null;
        state.selectedProfileKey = selectedProfile ? String(selectedProfile.profile_key || '').trim() : null;

        const models = Array.isArray(selectedProfile?.models) && selectedProfile.models.length
            ? selectedProfile.models
            : (selectedProfile?.model ? [String(selectedProfile.model)] : []);
        const preferredModel = String(state.selectedModel || selectedProfile?.model || models[0] || '').trim();
        state.selectedModel = models.includes(preferredModel) ? preferredModel : (models[0] || null);
        return { selectedProfile, models };
    }

    function renderPluginAiComposerProfiles() {
        const state = getPluginAiState();
        const combinedSelect = document.getElementById('plugin-ai-profile-model-select');
        if (!combinedSelect) return;

        const profiles = Array.isArray(state.profiles) ? state.profiles : [];
        const { selectedProfile, models } = syncPluginAiProfileSelections();
        const selectedProfileKey = String(state.selectedProfileKey || selectedProfile?.profile_key || '').trim();
        const selectedModel = String(state.selectedModel || '').trim();

        const options = [];
        profiles.forEach((profile) => {
            const profileKey = String(profile.profile_key || '').trim();
            const profileLabel = String(profile.display_name || profile.provider_label || profile.provider || profileKey || 'Profile');
            const profileModels = Array.isArray(profile.models) && profile.models.length
                ? profile.models
                : (profile?.model ? [String(profile.model)] : []);
            profileModels.forEach((model) => {
                const modelValue = String(model || '').trim();
                if (!profileKey || !modelValue) return;
                const value = `${profileKey}::${modelValue}`;
                const selected = profileKey === selectedProfileKey && modelValue === selectedModel ? ' selected' : '';
                options.push(`<option value="${escapeOption(value)}"${selected}>${escapeOption(modelValue)}</option>`);
            });
        });

        combinedSelect.innerHTML = options.length
            ? options.join('')
            : '<option value="">No models found</option>';

        const activeThreadStreaming = !!state.sending
            && Number(state.streamThreadId || 0) === Number(state.threadId || 0)
            && !!String(state.streamRequestId || '').trim();
        combinedSelect.disabled = options.length === 0 || state.loading || activeThreadStreaming;
    }

    function updatePluginAiComposerSelections(partial = {}) {
        const state = getPluginAiState();
        if (Object.prototype.hasOwnProperty.call(partial, 'profiles')) {
            state.profiles = Array.isArray(partial.profiles) ? partial.profiles : [];
        }
        if (Object.prototype.hasOwnProperty.call(partial, 'selectedProfileKey')) {
            state.selectedProfileKey = partial.selectedProfileKey ? String(partial.selectedProfileKey).trim() : null;
        }
        if (Object.prototype.hasOwnProperty.call(partial, 'selectedModel')) {
            state.selectedModel = partial.selectedModel ? String(partial.selectedModel).trim() : null;
        }
        renderPluginAiComposerProfiles();
    }

    window.getPluginAiState = getPluginAiState;
    window.beginPluginAiView = beginPluginAiView;
    window.currentPluginMatchesState = currentPluginMatchesState;
    window.isPluginAiViewCurrent = isPluginAiViewCurrent;
    window.shouldIgnorePluginAiResponse = shouldIgnorePluginAiResponse;
    window.clearPluginAiTransientState = clearPluginAiTransientState;
    window.beginPluginAiStreamRequest = beginPluginAiStreamRequest;
    window.isCurrentPluginAiStreamRequest = isCurrentPluginAiStreamRequest;
    window.endPluginAiStreamRequest = endPluginAiStreamRequest;
    window.setPluginAiLiveActivityOptions = setPluginAiLiveActivityOptions;
    window.ensurePluginAiUiState = ensurePluginAiUiState;
    window.togglePluginAiUiFlag = togglePluginAiUiFlag;
    window.setPluginAiUiFlag = setPluginAiUiFlag;
    window.rememberPluginAiEventsSnapshot = rememberPluginAiEventsSnapshot;
    window.getPluginAiEventsSnapshot = getPluginAiEventsSnapshot;
    window.clearPluginAiEventsSnapshot = clearPluginAiEventsSnapshot;
    window.rememberPluginAiPendingSnapshot = rememberPluginAiPendingSnapshot;
    window.getPluginAiPendingSnapshot = getPluginAiPendingSnapshot;
    window.clearPluginAiPendingSnapshot = clearPluginAiPendingSnapshot;
    window.rememberPluginAiSelectedThread = rememberPluginAiSelectedThread;
    window.getPluginAiSelectedThread = getPluginAiSelectedThread;
    window.rememberPluginAiThreadUiSnapshot = rememberPluginAiThreadUiSnapshot;
    window.getPluginAiThreadUiSnapshot = getPluginAiThreadUiSnapshot;
    window.hydratePluginAiThreadUiSnapshot = hydratePluginAiThreadUiSnapshot;
    window.syncCurrentPluginAiThreadSnapshot = syncCurrentPluginAiThreadSnapshot;
    window.resetPluginAiThreadState = resetPluginAiThreadState;
    window.startPluginAiView = startPluginAiView;
    window.buildPluginThreadRequest = buildPluginThreadRequest;
    window.readPluginAiRuntimeOverrides = readPluginAiRuntimeOverrides;
    window.persistPluginAiRuntimePrefs = persistPluginAiRuntimePrefs;
    window.hydratePluginAiRuntimePrefs = hydratePluginAiRuntimePrefs;
    window.applyPluginAiRuntimePrefsToDom = applyPluginAiRuntimePrefsToDom;
    window.refreshPluginAiRuntimeSummary = refreshPluginAiRuntimeSummary;
    window.syncPluginAiApprovalModeUi = syncPluginAiApprovalModeUi;
    window.cyclePluginAiStrategy = cyclePluginAiStrategy;
    window.cyclePluginAiApprovalMode = cyclePluginAiApprovalMode;
    window.buildPluginAiMessagePayload = buildPluginAiMessagePayload;
    window.resolvePreferredPluginAiThreadId = resolvePreferredPluginAiThreadId;
    window.rememberPluginAiThread = rememberPluginAiThread;
    window.rememberPluginAiThreads = rememberPluginAiThreads;
    window.extractCurrentAiConfig = extractCurrentAiConfig;
    window.syncPluginAiProfileSelections = syncPluginAiProfileSelections;
    window.renderPluginAiComposerProfiles = renderPluginAiComposerProfiles;
    window.updatePluginAiComposerSelections = updatePluginAiComposerSelections;
})();
