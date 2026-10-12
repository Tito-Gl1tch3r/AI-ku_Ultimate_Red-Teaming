(function() {
    let currentScanId = null;
    let socket = null;
    let detailsPollingInterval = null;
    let detailsBulkPollingInterval = null;
    let modalReturnHash = 'history';
    let systemStatusTimer = null;
    let lastSystemErrorMessage = '';
    let lastSystemUpdateMessage = '';
    let announcedUpdateVersion = '';

    let historySessionsCache = [];
    let historyFilteredCache = [];
    let historyCurrentPage = 1;
    const HISTORY_PAGE_SIZE = 10;

    let detailsResultsCache = [];
    let detailsSourceCache = [];
    let detailsFiltersInitialized = false;
    let detailsCurrentPage = 1;
    const DETAILS_PAGE_SIZE = 10;

    let catalogPluginsCache = [];
    let catalogFilteredCache = [];
    let catalogFiltersInitialized = false;
    let catalogCurrentPage = 1;
    const CATALOG_PAGE_SIZE = 10;

    let dashboardTrendPoints = [];

    const SYSTEM_STATUS_POLL_INTERVAL = 15000;
    const TAB_TO_VIEW = {
        scan: 'new-scan',
        catalog: 'database',
        history: 'history',
        favorites: 'favorites',
        semgrep: 'semgrep-rules',
        'ai-settings': 'ai-settings',
        details: 'details',
        'plugin-detail': 'plugin-detail',
    };
    const VIEW_TO_TAB = {
        'new-scan': 'scan',
        database: 'catalog',
        history: 'history',
        favorites: 'favorites',
        'semgrep-rules': 'semgrep',
        'ai-settings': 'ai-settings',
        details: 'details',
        'plugin-detail': 'plugin-detail',
    };

    window.currentScanResults = Array.isArray(window.currentScanResults) ? window.currentScanResults : [];
    window.favoriteSlugs = window.favoriteSlugs instanceof Set ? window.favoriteSlugs : new Set();
    window.systemStatus = window.systemStatus ?? null;
    window.currentAiConfig = window.currentAiConfig ?? null;
    window.currentPluginAi = window.currentPluginAi || {
        plugin: null,
        isTheme: false,
        threadId: null,
        threads: [],
        loading: false,
        sending: false,
        messages: [],
        events: [],
        viewToken: 0,
        settingsLoading: false,
        profiles: [],
        selectedProfileKey: null,
        selectedModel: null,
        streamThreadId: null,
        pendingRunPollTimer: null,
        pendingRunPollKey: null,
        threadSyncPollTimer: null,
        threadSyncPollKey: null,
        pendingSnapshotRetryInFlight: false,
        runStartedAt: null,
        runningIndicatorTimer: null,
        runtimeOverrides: {
            strategy: 'auto',
            trace_enabled: false,
            output_schema: null,
            tasks: [],
            fanout: null,
            loop_detection: null,
            approval_mode: 'manual',
        },
        pendingApproval: null,
    };

    window.getCurrentScanId = function() {
        return currentScanId;
    };

    let globalTooltipEl = null;
    let globalTooltipTarget = null;

    function ensureGlobalTooltip() {
        if (globalTooltipEl && document.body?.contains(globalTooltipEl)) return globalTooltipEl;
        globalTooltipEl = document.createElement('div');
        globalTooltipEl.className = 'global-tooltip';
        globalTooltipEl.setAttribute('role', 'tooltip');
        document.body.appendChild(globalTooltipEl);
        return globalTooltipEl;
    }

    function positionGlobalTooltip(target) {
        const tooltip = ensureGlobalTooltip();
        const text = target?.getAttribute('data-tooltip');
        if (!text) return;
        tooltip.textContent = text;
        tooltip.classList.add('is-visible');
        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const margin = 12;
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        left = Math.max(margin, Math.min(left, window.innerWidth - tooltipRect.width - margin));
        let top = rect.top - tooltipRect.height - 10;
        if (top < margin) {
            top = rect.bottom + 10;
        }
        top = Math.max(margin, Math.min(top, window.innerHeight - tooltipRect.height - margin));
        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
    }

    function hideGlobalTooltip() {
        if (!globalTooltipEl) return;
        globalTooltipEl.classList.remove('is-visible');
    }

    function bindGlobalTooltips() {
        if (document.body?.dataset.globalTooltipBound === '1') return;
        const tooltipSelector = '.info-icon[data-tooltip], .plugin-ai-runtime-chip[data-tooltip]';
        document.body?.addEventListener('mouseover', (event) => {
            const target = event.target instanceof Element ? event.target.closest(tooltipSelector) : null;
            if (!target) return;
            globalTooltipTarget = target;
            positionGlobalTooltip(target);
        });
        document.body?.addEventListener('mouseout', (event) => {
            const target = event.target instanceof Element ? event.target.closest(tooltipSelector) : null;
            if (!target) return;
            if (globalTooltipTarget === target) {
                globalTooltipTarget = null;
                hideGlobalTooltip();
            }
        });
        document.body?.addEventListener('focusin', (event) => {
            const target = event.target instanceof Element ? event.target.closest(tooltipSelector) : null;
            if (!target) return;
            globalTooltipTarget = target;
            positionGlobalTooltip(target);
        });
        document.body?.addEventListener('focusout', (event) => {
            const target = event.target instanceof Element ? event.target.closest(tooltipSelector) : null;
            if (!target) return;
            if (globalTooltipTarget === target) {
                globalTooltipTarget = null;
                hideGlobalTooltip();
            }
        });
        window.addEventListener('scroll', () => {
            if (globalTooltipTarget) positionGlobalTooltip(globalTooltipTarget);
        }, true);
        window.addEventListener('resize', () => {
            if (globalTooltipTarget) positionGlobalTooltip(globalTooltipTarget);
        });
        if (document.body) {
            document.body.dataset.globalTooltipBound = '1';
        }
    }

    bindGlobalTooltips();

    window.temodarAgentRuntime = {
        getCurrentScanId: () => currentScanId,
        setCurrentScanId: (value) => { currentScanId = value; },
        clearCurrentScanId: () => { currentScanId = null; },
        getSocket: () => socket,
        setSocket: (value) => { socket = value; },
        getDetailsPollingInterval: () => detailsPollingInterval,
        setDetailsPollingInterval: (value) => { detailsPollingInterval = value; },
        getModalReturnHash: () => modalReturnHash,
        setModalReturnHash: (value) => { modalReturnHash = value; },
        getSystemStatus: () => window.systemStatus,
        setSystemStatus: (value) => { window.systemStatus = value; },
        getLastSystemErrorMessage: () => lastSystemErrorMessage,
        setLastSystemErrorMessage: (value) => { lastSystemErrorMessage = value; },
        getLastSystemUpdateMessage: () => lastSystemUpdateMessage,
        setLastSystemUpdateMessage: (value) => { lastSystemUpdateMessage = value; },
        getAnnouncedUpdateVersion: () => announcedUpdateVersion,
        setAnnouncedUpdateVersion: (value) => { announcedUpdateVersion = value; },
        getSystemStatusTimer: () => systemStatusTimer,
        setSystemStatusTimer: (value) => { systemStatusTimer = value; },
        clearDetailsPolling: () => {
            if (detailsPollingInterval) {
                clearInterval(detailsPollingInterval);
                detailsPollingInterval = null;
            }
            if (detailsBulkPollingInterval) {
                clearInterval(detailsBulkPollingInterval);
                detailsBulkPollingInterval = null;
            }
        },
        getTabToView: () => TAB_TO_VIEW,
        getViewToTab: () => VIEW_TO_TAB,
        getSystemPollInterval: () => SYSTEM_STATUS_POLL_INTERVAL,
        getHistorySessionsCache: () => historySessionsCache,
        setHistorySessionsCache: (value) => { historySessionsCache = Array.isArray(value) ? value : []; },
        getHistoryFilteredCache: () => historyFilteredCache,
        setHistoryFilteredCache: (value) => { historyFilteredCache = Array.isArray(value) ? value : []; },
        getHistoryCurrentPage: () => historyCurrentPage,
        setHistoryCurrentPage: (value) => { historyCurrentPage = value; },
        getHistoryPageSize: () => HISTORY_PAGE_SIZE,
        getCurrentScanIdForTrend: () => currentScanId,
        getDashboardTrendPoints: () => dashboardTrendPoints,
        setDashboardTrendPoints: (value) => { dashboardTrendPoints = Array.isArray(value) ? value : []; },
        getCatalogPluginsCache: () => catalogPluginsCache,
        setCatalogPluginsCache: (value) => { catalogPluginsCache = Array.isArray(value) ? value : []; },
        getCatalogFilteredCache: () => catalogFilteredCache,
        setCatalogFilteredCache: (value) => { catalogFilteredCache = Array.isArray(value) ? value : []; },
        getCatalogCurrentPage: () => catalogCurrentPage,
        setCatalogCurrentPage: (value) => { catalogCurrentPage = value; },
        getCatalogPageSize: () => CATALOG_PAGE_SIZE,
        getCatalogFiltersInitialized: () => catalogFiltersInitialized,
        setCatalogFiltersInitialized: (value) => { catalogFiltersInitialized = Boolean(value); },
        getDetailsResultsCache: () => detailsResultsCache,
        setDetailsResultsCache: (value) => { detailsResultsCache = Array.isArray(value) ? value : []; },
        getDetailsSourceCache: () => detailsSourceCache,
        setDetailsSourceCache: (value) => { detailsSourceCache = Array.isArray(value) ? value : []; },
        getDetailsCurrentPage: () => detailsCurrentPage,
        setDetailsCurrentPage: (value) => { detailsCurrentPage = value; },
        getDetailsPageSize: () => DETAILS_PAGE_SIZE,
        getDetailsFiltersInitialized: () => detailsFiltersInitialized,
        setDetailsFiltersInitialized: (value) => { detailsFiltersInitialized = Boolean(value); },
        getDetailsBulkPollingInterval: () => detailsBulkPollingInterval,
        setDetailsBulkPollingInterval: (value) => { detailsBulkPollingInterval = value; },
    };
})();
