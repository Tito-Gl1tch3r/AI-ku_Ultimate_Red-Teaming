(function() {
    const runtime = window.temodarAgentRuntime;

function getUrlState() {
    const url = new URL(window.location.href);
    const params = url.searchParams;

    let view = String(params.get('view') || '').trim().toLowerCase();
    let plugin = String(params.get('plugin') || '').trim();
    const scanRaw = params.get('scan');
    let scanId = scanRaw != null ? parseInt(scanRaw, 10) : null;
    if (!Number.isFinite(scanId)) scanId = null;

    // Backward compatibility: migrate legacy hash URLs.
    const hash = window.location.hash.replace('#', '').trim();
    if (!view && hash) {
        const legacy = hash.toLowerCase();
        if (legacy.startsWith('details/')) {
            view = 'details';
            const parts = legacy.split('/');
            const parsed = parseInt(parts[1], 10);
            if (Number.isFinite(parsed)) scanId = parsed;
        } else if (legacy.startsWith('plugin/')) {
            const parts = hash.split('/');
            plugin = String(parts[1] || '').trim();
            const parsed = parseInt(parts[2], 10);
            if (Number.isFinite(parsed)) scanId = parsed;
            view = scanId ? 'details' : 'history';
        } else {
            const asTab = String(hash || '').toLowerCase();
            if (['scan', 'catalog', 'history', 'favorites', 'semgrep', 'ai-settings'].includes(asTab)) {
                view = runtime.getTabToView()[asTab] || 'new-scan';
            }
        }
    }

    return { view, scanId, plugin };
}

function setUrlState(state = {}, options = {}) {
    const { replace = false } = options;
    const current = getUrlState();
    const merged = {
        view: state.view !== undefined ? state.view : current.view,
        scanId: state.scanId !== undefined ? state.scanId : current.scanId,
        plugin: state.plugin !== undefined ? state.plugin : current.plugin,
    };

    const url = new URL(window.location.href);
    url.searchParams.delete('view');
    url.searchParams.delete('scan');
    url.searchParams.delete('plugin');

    if (merged.view) url.searchParams.set('view', String(merged.view));
    if (Number.isFinite(Number(merged.scanId)) && Number(merged.scanId) > 0) {
        url.searchParams.set('scan', String(merged.scanId));
    }
    if (merged.plugin) url.searchParams.set('plugin', String(merged.plugin));

    // Remove hash style URLs completely.
    url.hash = '';

    const nextUrl = `${url.pathname}${url.search}`;
    if (replace) {
        window.history.replaceState({}, '', nextUrl);
    } else {
        window.history.pushState({}, '', nextUrl);
    }
}

function restoreViewFromUrl() {
    const state = getUrlState();

    if (!state.view) {
        setUrlState({ view: 'new-scan' }, { replace: true });
        switchTab('scan');
        return;
    }

    if (state.view !== 'details' && state.view !== 'plugin-detail') {
        runtime.setModalReturnHash(state.view);
    }

    if (state.view === 'plugin-detail' && state.plugin) {
        if (state.scanId) runtime.setCurrentScanId(state.scanId);
        setTimeout(() => openPluginModalBySlug(state.plugin, { syncUrl: false }), 0);
        setUrlState(
            { view: 'plugin-detail', scanId: state.scanId || null, plugin: state.plugin },
            { replace: true }
        );
        return;
    }

    if (state.view === 'details' && state.scanId) {
        viewScan(state.scanId, { syncUrl: false });
        setUrlState({ view: 'details', scanId: state.scanId, plugin: '' }, { replace: true });
        return;
    }

    const tabId = runtime.getViewToTab()[state.view] || 'scan';
    switchTab(tabId, { syncUrl: false });

    setUrlState({ view: runtime.getTabToView()[tabId] || 'new-scan', plugin: '' }, { replace: true });
}

function findPluginIndex(results, slug) {
    return Array.isArray(results) ? results.findIndex((plugin) => plugin.slug === slug) : -1;
}

function openPluginFromResults(results, slug, options = {}) {
    const index = findPluginIndex(results, slug);
    if (index === -1) return false;
    window.currentScanResults = results;
    openPluginModal(index, options);
    return true;
}

async function fetchFavoriteBySlug(slug) {
    const resp = await fetch('/api/favorites');
    const data = await resp.json();
    return Array.isArray(data.favorites)
        ? data.favorites.find((plugin) => plugin.slug === slug) || null
        : null;
}

async function fetchScanResults(scanId) {
    const resp = await fetch(`/api/scans/${scanId}/results?limit=500`);
    const data = await resp.json();
    return Array.isArray(data.results) ? data.results : [];
}

async function fetchSortedSessions() {
    const resp = await fetch('/api/scans');
    const data = await resp.json();
    const sessions = Array.isArray(data.sessions) ? data.sessions : [];
    return sessions.sort(
        (a, b) => new Date(b.created_at || b.start_time) - new Date(a.created_at || a.start_time)
    );
}

async function openPluginModalBySlug(slug, options = {}) {
    if (openPluginFromResults(window.currentScanResults, slug, options)) {
        return;
    }

    try {
        const favorite = await fetchFavoriteBySlug(slug);
        if (favorite && openPluginFromResults([favorite], slug, options)) {
            return;
        }
    } catch (error) {
        console.error('Failed to load from favorites:', error);
    }

    if (runtime.getCurrentScanId()) {
        try {
            const currentResults = await fetchScanResults(runtime.getCurrentScanId());
            if (openPluginFromResults(currentResults, slug, options)) {
                return;
            }
        } catch (error) {
            console.error('Failed to load from current scan:', error);
        }
    }

    try {
        const sessions = await fetchSortedSessions();
        for (const session of sessions) {
            try {
                const results = await fetchScanResults(session.id);
                const found = openPluginFromResults(results, slug, options);
                if (!found) continue;
                runtime.setCurrentScanId(session.id);
                return;
            } catch (error) {
                console.error(`Failed to load scan ${session.id} results:`, error);
            }
        }
    } catch (error) {
        console.error('Failed to load scans:', error);
    }

    showToast('Plugin not found. It may have been removed.', 'error');
    setUrlState({ view: 'history', plugin: '', scanId: null }, { replace: false });
    switchTab('history', { syncUrl: false });
}

window.switchTab = function(tabId, options = {}) {
    const { syncUrl = true } = options;
    // Hide all views
    document.getElementById('scan-view').style.display = 'none';
    document.getElementById('history-view').style.display = 'none';
    document.getElementById('favorites-view').style.display = 'none';
    const catalogView = document.getElementById('catalog-view');
    if (catalogView) catalogView.style.display = 'none';
    const detailsView = document.getElementById('scan-details-view');
    if (detailsView) detailsView.style.display = 'none';
    const semgrepView = document.getElementById('semgrep-view');
    if (semgrepView) semgrepView.style.display = 'none';
    const aiSettingsView = document.getElementById('ai-settings-view');
    if (aiSettingsView) aiSettingsView.style.display = 'none';
    const pluginDetailView = document.getElementById('plugin-detail-view');
    if (pluginDetailView) pluginDetailView.style.display = 'none';

    // Reset nav active state
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    // Show selected view and set active
    if (tabId === 'scan') {
        document.getElementById('scan-view').style.display = 'block';
        document.getElementById('nav-scan').classList.add('active');
        resetDashboardChartCaptions();
    } else if (tabId === 'history') {
        document.getElementById('history-view').style.display = 'block';
        document.getElementById('nav-history').classList.add('active');
        loadHistory();
    } else if (tabId === 'favorites') {
        document.getElementById('favorites-view').style.display = 'block';
        document.getElementById('nav-favorites').classList.add('active');
        loadFavorites();
    } else if (tabId === 'catalog') {
        if (catalogView) catalogView.style.display = 'block';
        const navCatalog = document.getElementById('nav-catalog');
        if (navCatalog) navCatalog.classList.add('active');
        loadCatalog();
    } else if (tabId === 'semgrep') {
        if (semgrepView) semgrepView.style.display = 'block';
        document.getElementById('nav-semgrep').classList.add('active');
        loadSemgrepRules();
    } else if (tabId === 'ai-settings') {
        if (aiSettingsView) aiSettingsView.style.display = 'block';
        const navAiSettings = document.getElementById('nav-ai-settings');
        if (navAiSettings) navAiSettings.classList.add('active');
        if (typeof window.loadAiSettingsDashboard === 'function') {
            window.loadAiSettingsDashboard();
        }
    } else if (tabId === 'details') {
        if (detailsView) detailsView.style.display = 'block';
    } else if (tabId === 'plugin-detail') {
        if (pluginDetailView) pluginDetailView.style.display = 'block';
    }

    // Stop details polling when leaving details view
    if (tabId !== 'details') {
        runtime.clearDetailsPolling();
        if (tabId !== 'plugin-detail') {
            runtime.clearCurrentScanId();
        }
    }

    // Update URL state for persistence on refresh (except details, handled by viewScan)
    if (syncUrl && tabId !== 'details' && tabId !== 'plugin-detail') {
        setUrlState({ view: runtime.getTabToView()[tabId] || 'new-scan', scanId: null, plugin: '' }, { replace: false });
    }
}


    window.getUrlState = getUrlState;
    window.setUrlState = setUrlState;
    window.restoreViewFromUrl = restoreViewFromUrl;
    window.openPluginModalBySlug = openPluginModalBySlug;
})();
