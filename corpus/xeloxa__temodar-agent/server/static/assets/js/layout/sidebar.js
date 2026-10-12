(function() {
const SIDEBAR_PREF_KEY = 'temodar-agent-sidebar-collapsed';
const STAR_STRIP_PREF_KEY = 'temodar-agent-star-strip-hidden';

function applySidebarState(collapsed) {
    const layout = document.querySelector('.layout');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const isMobile = window.matchMedia('(max-width: 800px)').matches;

    if (!layout || !toggleBtn) return;

    if (isMobile) {
        layout.classList.remove('sidebar-collapsed');
        toggleBtn.setAttribute('aria-expanded', 'true');
        toggleBtn.setAttribute('aria-label', 'Collapse sidebar');
        toggleBtn.title = 'Collapse sidebar';
        return;
    }

    layout.classList.toggle('sidebar-collapsed', collapsed);
    toggleBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    toggleBtn.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    toggleBtn.title = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
}

window.toggleSidebarCollapse = function() {
    const layout = document.querySelector('.layout');
    if (!layout) return;

    const isMobile = window.matchMedia('(max-width: 800px)').matches;
    if (isMobile) {
        applySidebarState(false);
        localStorage.setItem(SIDEBAR_PREF_KEY, '0');
        return;
    }

    const willCollapse = !layout.classList.contains('sidebar-collapsed');
    applySidebarState(willCollapse);
    localStorage.setItem(SIDEBAR_PREF_KEY, willCollapse ? '1' : '0');
};

function initializeSidebarToggle() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (!toggleBtn) return;

    toggleBtn.addEventListener('click', window.toggleSidebarCollapse);

    const savedCollapsed = localStorage.getItem(SIDEBAR_PREF_KEY) === '1';
    applySidebarState(savedCollapsed);

    window.addEventListener('resize', () => {
        const shouldCollapse = window.matchMedia('(max-width: 800px)').matches
            ? false
            : localStorage.getItem(SIDEBAR_PREF_KEY) === '1';
        applySidebarState(shouldCollapse);
    });
}

function initializeStarStripDismiss() {
    const starStrip = document.querySelector('.star-strip');
    const closeBtn = document.getElementById('star-strip-close');
    if (!starStrip || !closeBtn) return;

    const setStarStripHidden = (hidden) => {
        starStrip.classList.toggle('is-hidden', hidden);
        document.body.classList.toggle('star-strip-hidden', hidden);
    };

    const hidden = localStorage.getItem(STAR_STRIP_PREF_KEY) === '1';
    setStarStripHidden(hidden);

    closeBtn.addEventListener('click', () => {
        setStarStripHidden(true);
        localStorage.setItem(STAR_STRIP_PREF_KEY, '1');
    });
}

// Prevent stale API responses that force manual F5
const _nativeFetch = window.fetch.bind(window);
window.fetch = function(resource, options = {}) {
    const isApiCall = typeof resource === 'string' && resource.startsWith('/api/');
    if (!isApiCall) return _nativeFetch(resource, options);

    const headers = { ...(options.headers || {}) };
    if (!headers['Cache-Control']) headers['Cache-Control'] = 'no-cache';
    if (!headers['Pragma']) headers['Pragma'] = 'no-cache';

    return _nativeFetch(resource, {
        ...options,
        cache: 'no-store',
        headers
    });
};

function isDetailsViewActive() {
    const detailsView = document.getElementById('scan-details-view');
    return !!detailsView && detailsView.style.display !== 'none';
}

function apiNoCacheUrl(path) {
    const sep = path.includes('?') ? '&' : '?';
    return `${path}${sep}_ts=${Date.now()}`;
}


    window.initializeSidebarToggle = initializeSidebarToggle;
    window.initializeStarStripDismiss = initializeStarStripDismiss;
    window.isDetailsViewActive = isDetailsViewActive;
    window.apiNoCacheUrl = apiNoCacheUrl;
})();
