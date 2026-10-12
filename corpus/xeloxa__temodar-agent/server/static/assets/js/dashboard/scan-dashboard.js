(function() {
    const runtime = window.temodarAgentRuntime;

window.initializeDashboardChartInteractions = function() {
    bindChartHover('dashboard-risk-bars', 'dashboard-risk-caption');
    bindChartHover('dashboard-trend-bars', 'dashboard-trend-caption');
    resetDashboardChartCaptions();
}

window.openDashboardScanFromChart = function(scanId, source = 'chart') {
    const parsed = Number(scanId);
    if (!Number.isFinite(parsed) || parsed <= 0) return;
    setChartCaption('dashboard-risk-caption', `Opening #${parsed} (${source})`);
    setChartCaption('dashboard-trend-caption', `Opening #${parsed} (${source})`);
    setTimeout(resetDashboardChartCaptions, 1200);
    viewScan(parsed);
};

function renderRecentScans(sessions) {
    const recentList = document.getElementById('dashboard-recent-list');
    const completedRate = document.getElementById('dashboard-completed-rate');
    if (!recentList) return;

    if (!sessions || sessions.length === 0) {
        recentList.innerHTML = '<div class="recent-empty">No scans yet</div>';
        if (completedRate) completedRate.textContent = '0% completed';
        return;
    }

    const completedCount = sessions.filter(s => String(s.status).toLowerCase() === 'completed').length;
    const percent = Math.round((completedCount / sessions.length) * 100);
    if (completedRate) completedRate.textContent = `${percent}% completed`;

    const maxPluginsFound = sessions.reduce((max, session) => {
        const sessionCount = parseInt(session.total_found || 0, 10) || 0;
        return Math.max(max, sessionCount);
    }, 1);

    recentList.innerHTML = sessions.slice(0, 3).map(s => {
        const id = parseInt(s.id, 10) || 0;
        const statusClass = String(s.status || 'unknown').toLowerCase();
        const statusLabel = statusClass === 'merged' ? 'MERGED' : statusClass.toUpperCase();
        const found = parseInt(s.total_found || 0, 10) || 0;
        const highRisk = parseInt(s.high_risk_count || 0, 10) || 0;
        const foundRatio = maxPluginsFound > 0 ? Math.min(100, Math.round((found / maxPluginsFound) * 100)) : 0;
        const foundLevel = foundRatio >= 70 ? 'high' : (foundRatio >= 35 ? 'medium' : 'low');
        const riskLevel = highRisk >= 20 ? 'high' : (highRisk >= 5 ? 'medium' : 'low');
        const riskRatio = found > 0 ? Math.min(100, Math.round((highRisk / found) * 100)) : 0;
        const date = new Date(s.created_at || s.start_time).toLocaleString();
        return `
            <div class="recent-row recent-history-row" tabindex="0" onclick="openDashboardScanFromChart(${id}, 'recent')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openDashboardScanFromChart(${id}, 'recent');}">
                <span class="recent-title recent-history-id">#${id}</span>
                <span class="status-badge ${escapeHtml(statusClass)}">${escapeHtml(statusLabel)}</span>
                <div class="history-found-cell" title="${found} plugins found (relative density ${foundRatio}%)">
                    <span class="history-found-count">${escapeHtml(String(found))}</span>
                    <span class="history-found-label">plugins</span>
                    <span class="history-found-track"><span class="history-found-fill ${foundLevel}" style="width: ${foundRatio}%;"></span></span>
                </div>
                <div class="history-risk-cell" title="${highRisk} high risk / ${found} total (${riskRatio}%)">
                    <span class="history-risk-pill ${riskLevel}">${escapeHtml(String(highRisk))}</span>
                    <span class="history-risk-meter"><span class="history-risk-fill ${riskLevel}" style="width: ${riskRatio}%;"></span></span>
                </div>
                <span class="recent-meta history-date-stamp recent-history-date">${escapeHtml(date)}</span>
                <button class="history-action-open dashboard-history-open" type="button" onclick="event.stopPropagation();openDashboardScanFromChart(${id}, 'recent')" title="Open Scan" aria-label="Open scan #${id}">
                    <span>OPEN</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                </button>
            </div>
        `;
    }).join('');
}

window.renderRecentFavorites = function(favorites) {
    const list = document.getElementById('dashboard-favorites-list');
    if (!list) return;

    if (!favorites || favorites.length === 0) {
        list.innerHTML = '<div class="recent-empty">No favorites yet</div>';
        return;
    }

    list.innerHTML = favorites.slice(0, 3).map(plugin => {
        const rawSlug = String(plugin.slug || 'unknown-plugin');
        const slug = escapeHtml(rawSlug);
        const slugJs = JSON.stringify(rawSlug);
        const score = parseInt(plugin.score || 0, 10) || 0;
        const riskLevel = score >= 40 ? 'high' : (score >= 20 ? 'medium' : 'low');
        const scoreRatio = Math.max(0, Math.min(100, score));
        const versionLabel = `v${String(plugin.version || 'n/a')}`;
        return `
            <div class="recent-row recent-favorites-row" tabindex="0" onclick='openPluginModalBySlug(${slugJs})' onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openPluginModalBySlug(${slugJs});}">
                <span class="recent-title recent-favorites-slug">${slug}</span>
                <span class="recent-meta history-date-stamp recent-favorites-version">${escapeHtml(versionLabel)}</span>
                <div class="history-risk-cell recent-favorites-risk" title="Risk score ${score}">
                    <span class="history-risk-pill ${riskLevel}">${score}</span>
                    <span class="history-risk-meter"><span class="history-risk-fill ${riskLevel}" style="width: ${scoreRatio}%;"></span></span>
                </div>
                <button class="history-action-open dashboard-history-open" type="button" onclick='event.stopPropagation();openPluginModalBySlug(${slugJs})' title="Open Favorite" aria-label="Open favorite ${slug}">
                    <span>OPEN</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                </button>
            </div>
        `;
    }).join('');
}

async function refreshDashboardFavorites() {
    try {
        const response = await fetch('/api/favorites');
        if (!response.ok) throw new Error(`Favorites fetch failed: ${response.status}`);
        const data = await response.json();
        renderRecentFavorites(data.favorites || []);
    } catch (error) {
        renderRecentFavorites([]);
    }
}

function renderRiskBars(sessions) {
    const riskBars = document.getElementById('dashboard-risk-bars');
    const riskCaption = document.getElementById('dashboard-risk-caption');
    if (!riskBars) return;

    if (!sessions || sessions.length === 0) {
        riskBars.innerHTML = '';
        if (riskCaption) riskCaption.textContent = 'No history';
        return;
    }

    const recent = sessions.slice(0, 8).reverse();
    const maxFound = Math.max(1, ...recent.map(s => parseInt(s.total_found || 0)));

    riskBars.innerHTML = recent.map((s) => {
        const id = parseInt(s.id);
        const found = parseInt(s.total_found || 0);
        const high = parseInt(s.high_risk_count || 0);
        const ratio = found > 0 ? high / found : 0;
        const height = Math.max(10, Math.round((found / maxFound) * 100));
        const level = ratio >= 0.35 ? 'high' : (ratio >= 0.15 ? 'medium' : 'low');
        const title = `Scan #${id} | Found ${found} | High ${high}`;
        const caption = `#${id} risk ${high}/${found}`;
        return `
            <button class="bar-item chart-point ${level}" type="button" data-scan-id="${id}" data-caption="${caption}" style="--h:${height}%" title="${title}" onclick="openDashboardScanFromChart(${id}, 'risk')"></button>
        `;
    }).join('');

    if (riskCaption) {
        const highSum = recent.reduce((acc, s) => acc + parseInt(s.high_risk_count || 0), 0);
        riskCaption.textContent = `${highSum} high-risk total - click a bar`;
    }
}

window.renderTrendBars = function() {
    const trendBars = document.getElementById('dashboard-trend-bars');
    const trendCaption = document.getElementById('dashboard-trend-caption');
    if (!trendBars) return;

    const dashboardTrendPoints = runtime.getDashboardTrendPoints();
    if (!dashboardTrendPoints.length) {
        trendBars.innerHTML = '';
        if (trendCaption) trendCaption.textContent = 'No trend data';
        return;
    }

    const maxVal = Math.max(1, ...dashboardTrendPoints.map(item => item.value));
    trendBars.innerHTML = dashboardTrendPoints.map((item) => {
        const value = Number(item.value || 0);
        const h = Math.max(8, Math.round((value / maxVal) * 100));
        const scanId = Number(item.scanId || 0);
        if (scanId > 0) {
            const title = `Scan #${scanId} | Found ${value}`;
            const caption = `#${scanId} found ${value}`;
            return `<button class="spark-item chart-point" type="button" data-scan-id="${scanId}" data-caption="${caption}" style="--h:${h}%" title="${title}" onclick="openDashboardScanFromChart(${scanId}, 'trend')"></button>`;
        }
        return `<div class="spark-item" style="--h:${h}%" title="Live found: ${value}"></div>`;
    }).join('');

    if (trendCaption) trendCaption.textContent = `Recent ${dashboardTrendPoints.length} sessions - click a bar`;
}

function renderTrendBarsFromSessions(sessions) {
    runtime.setDashboardTrendPoints((sessions || []).slice(0, 8).reverse().map((s) => ({
        value: parseInt(s.total_found || 0),
        scanId: parseInt(s.id || 0)
    })).slice(-8));
    window.renderTrendBars();
}

window.appendTrendPoint = function(value) {
    const parsed = parseInt(value || 0);
    if (!Number.isFinite(parsed)) return;
    const trendPoints = [...runtime.getDashboardTrendPoints()];
    trendPoints.push({
        value: parsed,
        scanId: Number(runtime.getCurrentScanIdForTrend()) || 0
    });
    runtime.setDashboardTrendPoints(trendPoints.slice(-8));
    window.renderTrendBars();
}

window.refreshScanDashboard = function(sessions) {
    const safeSessions = sessions || [];
    const totalScans = safeSessions.length;
    const highRiskTotal = safeSessions.reduce((acc, s) => acc + parseInt(s.high_risk_count || 0), 0);
    setDashboardMetric('dashboard-total-scans', totalScans);
    setDashboardMetric('dashboard-high-risk', highRiskTotal);
    renderRecentScans(safeSessions);
    refreshDashboardFavorites();
    renderRiskBars(safeSessions);
    renderTrendBarsFromSessions(safeSessions);
    resetDashboardChartCaptions();
}


})();
