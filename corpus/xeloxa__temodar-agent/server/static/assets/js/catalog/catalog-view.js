(function() {
    const runtime = window.temodarAgentRuntime;

    window.changeCatalogPage = function(delta) {
        const totalPages = Math.max(1, Math.ceil((runtime.getCatalogFilteredCache().length || 0) / runtime.getCatalogPageSize()));
        runtime.setCatalogCurrentPage(Math.min(Math.max(1, runtime.getCatalogCurrentPage() + delta), totalPages));
        window.renderCatalogRows(runtime.getCatalogFilteredCache());
    };

    function getCatalogFilterState() {
        const queryEl = document.getElementById('catalog-filter-query');
        const sortEl = document.getElementById('catalog-filter-sort');
        const typeEl = document.getElementById('catalog-filter-type');
        const orderEl = document.getElementById('catalog-filter-order');

        return {
            query: String(queryEl ? queryEl.value : '').trim().toLowerCase(),
            sort: String(sortEl ? sortEl.value : 'last_seen').toLowerCase(),
            type: String(typeEl ? typeEl.value : 'all').toLowerCase(),
            order: String(orderEl ? orderEl.value : 'desc').toLowerCase(),
        };
    }

    function getCatalogSortValue(item, sortKey) {
        if (sortKey === 'seen_count') return parseInt(item.seen_count || 0, 10) || 0;
        if (sortKey === 'max_score') return parseInt(item.max_score_ever || 0, 10) || 0;
        if (sortKey === 'installs') return parseInt(item.latest_installations || 0, 10) || 0;
        if (sortKey === 'updated_days') {
            const days = parseInt(item.latest_days_since_update, 10);
            return Number.isFinite(days) ? days : Number.POSITIVE_INFINITY;
        }
        if (sortKey === 'slug') return String(item.slug || '').toLowerCase();
        const ts = Date.parse(item.last_seen_at || '');
        return Number.isFinite(ts) ? ts : 0;
    }

    function filterCatalogPlugins(items, filterState) {
        const state = filterState || getCatalogFilterState();
        const filtered = (items || []).filter((item) => {
            const itemType = item && item.is_theme ? 'theme' : 'plugin';
            if (state.type !== 'all' && itemType !== state.type) return false;
            if (!state.query) return true;
            const haystack = `${String(item.slug || '').toLowerCase()} ${itemType}`;
            return haystack.includes(state.query);
        });

        filtered.sort((a, b) => {
            const av = getCatalogSortValue(a, state.sort);
            const bv = getCatalogSortValue(b, state.sort);
            let diff = 0;
            if (typeof av === 'string' || typeof bv === 'string') diff = String(av).localeCompare(String(bv));
            else diff = Number(av) - Number(bv);
            if (state.order === 'desc') diff *= -1;
            if (diff !== 0) return diff;
            return String(a.slug || '').toLowerCase().localeCompare(String(b.slug || '').toLowerCase());
        });

        return filtered;
    }

    window.renderCatalogDashboard = function(items) {
        const dashboard = document.getElementById('catalog-dashboard');
        if (!dashboard) return;

        const rows = Array.isArray(items) ? items : [];
        const total = rows.length;
        if (total === 0) {
            dashboard.innerHTML = '';
            return;
        }

        const highCount = rows.filter(r => (parseInt(r && (r.latest_score ?? r.max_score_ever) || 0, 10) || 0) >= 40).length;
        const midCount = rows.filter(r => {
            const score = parseInt(r && (r.latest_score ?? r.max_score_ever) || 0, 10) || 0;
            return score >= 20 && score < 40;
        }).length;
        const lowCount = Math.max(0, total - highCount - midCount);

        let issueCount = 0;
        let cleanCount = 0;
        let waitingCount = 0;
        let failedCount = 0;
        let runningCount = 0;

        rows.forEach((r) => {
            const semgrep = r && r.semgrep ? r.semgrep : null;
            if (!semgrep) {
                waitingCount += 1;
                return;
            }

            const status = String(semgrep.status || '').toLowerCase();
            if (status === 'completed') {
                const findings = parseInt(semgrep.findings_count || 0, 10) || 0;
                if (findings > 0) issueCount += 1;
                else cleanCount += 1;
                return;
            }
            if (status === 'failed') {
                failedCount += 1;
                return;
            }
            if (status === 'running' || status === 'pending') {
                runningCount += 1;
                return;
            }

            waitingCount += 1;
        });

        const scannedCount = issueCount + cleanCount + failedCount;
        const remainingCount = Math.max(0, total - scannedCount);
        const toPct = (value, sum) => {
            if (!sum || sum <= 0) return 0;
            return Math.max(0, Math.min(100, Math.round((value / sum) * 100)));
        };

        dashboard.innerHTML = `
            <div class="details-stat-card details-stat-card-total">
                <div class="details-stat-label">Catalog inventory</div>
                <div class="details-stat-value">${total}</div>
                <div class="details-stat-sub">Unique plugins/themes in database</div>
                <div class="details-stat-track"><span class="details-stat-fill details-fill-blue" style="width:100%"></span></div>
            </div>
            <div class="details-stat-card details-stat-card-progress">
                <div class="details-stat-label">Semgrep progress</div>
                <div class="details-stat-value">${scannedCount} / ${total}</div>
                <div class="details-stat-sub">Processed / Total • ${remainingCount} remaining</div>
                <div class="details-stat-track">
                    <span class="details-stat-fill details-fill-primary" style="width:${toPct(scannedCount, total)}%"></span>
                    <span class="details-stat-fill details-fill-wait" style="width:${toPct(remainingCount, total)}%"></span>
                </div>
            </div>
            <div class="details-stat-card">
                <div class="details-stat-label">Risk split</div>
                <div class="details-stat-value">${highCount} / ${midCount} / ${lowCount}</div>
                <div class="details-stat-sub">High / Medium / Low</div>
                <div class="details-stat-track">
                    <span class="details-stat-fill details-fill-high" style="width:${toPct(highCount, total)}%"></span>
                    <span class="details-stat-fill details-fill-mid" style="width:${toPct(midCount, total)}%"></span>
                    <span class="details-stat-fill details-fill-low" style="width:${toPct(lowCount, total)}%"></span>
                </div>
            </div>
            <div class="details-stat-card">
                <div class="details-stat-label">Semgrep</div>
                <div class="details-stat-value">${issueCount} / ${cleanCount} / ${runningCount}</div>
                <div class="details-stat-sub">Issue / Clean / Running</div>
                <div class="details-stat-track">
                    <span class="details-stat-fill details-fill-issue" style="width:${toPct(issueCount, total)}%"></span>
                    <span class="details-stat-fill details-fill-clean" style="width:${toPct(cleanCount, total)}%"></span>
                    <span class="details-stat-fill details-fill-wait" style="width:${toPct(waitingCount, total)}%"></span>
                    <span class="details-stat-fill details-fill-fail" style="width:${toPct(failedCount, total)}%"></span>
                </div>
            </div>
        `;
    };

    window.renderCatalogRows = function(items) {
        const list = document.getElementById('catalog-list');
        if (!list) return;

        const safeItems = items || [];
        runtime.setCatalogFilteredCache(safeItems);

        const totalPages = Math.max(1, Math.ceil(safeItems.length / runtime.getCatalogPageSize()));
        runtime.setCatalogCurrentPage(Math.min(Math.max(1, runtime.getCatalogCurrentPage()), totalPages));
        const pageStart = (runtime.getCatalogCurrentPage() - 1) * runtime.getCatalogPageSize();
        const pagedItems = safeItems.slice(pageStart, pageStart + runtime.getCatalogPageSize());

        window.updateTablePagination('catalog', safeItems.length, runtime.getCatalogCurrentPage(), runtime.getCatalogPageSize());

        if (safeItems.length === 0) {
            list.innerHTML = '<tr><td colspan="7" class="favorites-empty">No plugins in store</td></tr>';
            return;
        }

        const maxInstalls = pagedItems.reduce((max, item) => {
            const installs = parseInt(item.latest_installations || 0, 10) || 0;
            return Math.max(max, installs);
        }, 1);

        list.innerHTML = pagedItems.map((item) => {
            const slug = String(item.slug || 'unknown-plugin');
            const isTheme = !!item.is_theme;
            const modeClass = isTheme ? 'theme' : 'plugin';
            const modeLabel = isTheme ? 'THEME' : 'PLUGIN';
            const latestScore = parseInt(item.latest_score || 0, 10) || 0;
            const maxScore = parseInt(item.max_score_ever || 0, 10) || 0;
            const score = Math.max(latestScore, maxScore);
            const scoreClass = getRiskClassForResult(score);
            const scoreRatio = Math.max(0, Math.min(100, score));
            const installs = parseInt(item.latest_installations || 0, 10) || 0;
            const rawInstallsRatio = maxInstalls > 0 ? Math.min(100, Math.round((installs / maxInstalls) * 100)) : 0;
            const installsRatio = installs > 0 ? Math.max(4, rawInstallsRatio) : 0;
            const installsLevel = installsRatio >= 70 ? 'high' : (installsRatio >= 35 ? 'medium' : 'low');
            const updatedLabel = getUpdatedLabel(parseDaysSinceUpdate(item.latest_days_since_update));

            const semgrep = item.semgrep || null;
            const semgrepCount = semgrep ? (parseInt(semgrep.findings_count || 0, 10) || 0) : (parseInt(item.latest_semgrep_findings || 0, 10) || 0);
            const semgrepStatus = semgrep ? String(semgrep.status || '').toLowerCase() : '';
            let semgrepTone = 'empty';
            let semgrepState = 'WAIT';
            let semgrepProgress = 0;
            if (semgrepStatus === 'completed') {
                semgrepTone = semgrepCount > 0 ? 'alert' : 'complete';
                semgrepState = semgrepCount > 0 ? 'ISSUE' : 'CLEAN';
                semgrepProgress = 100;
            } else if (semgrepStatus === 'running' || semgrepStatus === 'pending') {
                semgrepTone = 'running';
                semgrepState = 'SCANNING';
                semgrepProgress = 35;
            } else if (semgrepStatus === 'failed') {
                semgrepTone = 'alert';
                semgrepState = 'FAIL';
                semgrepProgress = 100;
            }

            const latestSession = parseInt(item.last_seen_session_id || 0, 10) || 0;
            const wpLink = isTheme ? `https://wordpress.org/themes/${slug}/` : `https://wordpress.org/plugins/${slug}/`;
            const lastSeen = item.last_seen_at ? new Date(item.last_seen_at).toLocaleString() : '';

            const pluginJson = JSON.stringify({
                slug,
                name: slug,
                version: item.latest_version || 'n/a',
                score,
                installations: installs,
                days_since_update: parseInt(item.latest_days_since_update || 0, 10) || 0,
                is_theme: isTheme,
                wp_org_link: wpLink,
                trac_link: isTheme ? `https://themes.trac.wordpress.org/log/${slug}/` : `https://plugins.trac.wordpress.org/log/${slug}/`,
            });

            return `
                <tr class="history-row details-results-row" tabindex="0" onclick='openCatalogPlugin(${pluginJson}, ${latestSession})' onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openCatalogPlugin(${pluginJson}, ${latestSession});}">
                    <td class="details-col-slug"><span class="details-slug">${escapeHtml(slug)}</span></td>
                    <td class="details-col-version"><span class="history-semgrep-pill">${escapeHtml(String(item.latest_version || 'n/a'))}</span></td>
                    <td class="details-col-score"><div class="history-risk-cell" title="Risk ${score} (latest ${latestScore}, max ${maxScore})"><span class="history-risk-pill ${scoreClass}">${score}</span><span class="history-risk-meter"><span class="history-risk-fill ${scoreClass}" style="width:${scoreRatio}%;"></span></span></div></td>
                    <td class="details-col-updated"><span class="history-date-stamp">${escapeHtml(updatedLabel)}</span></td>
                    <td class="details-col-installs"><div class="history-found-cell" title="${installs.toLocaleString()} installs / last seen ${escapeHtml(lastSeen)}"><span class="history-found-count">${escapeHtml(formatInstallCount(installs))}</span><span class="history-found-label">installs</span><span class="history-found-track"><span class="history-found-fill ${installsLevel}" style="width:${installsRatio}%;"></span></span></div></td>
                    <td class="details-col-semgrep"><div class="history-semgrep-cell ${semgrepTone}"><span class="history-semgrep-pill">${escapeHtml(String(semgrepCount || '--'))}</span><span class="history-semgrep-meter"><span class="history-semgrep-fill" style="width:${semgrepProgress}%;"></span></span><span class="history-semgrep-state">${escapeHtml(semgrepState)}</span></div></td>
                    <td class="details-col-actions"><div class="details-row-actions"><span class="history-mode-chip ${modeClass}">${escapeHtml(modeLabel)}</span><a href="${escapeHtml(wpLink)}" target="_blank" rel="noreferrer noopener" onclick="event.stopPropagation();" class="action-btn details-wp-btn" aria-label="Open on WordPress.org" title="Open on WordPress.org"><span class="wp-logo-icon" aria-hidden="true"></span></a><button onclick='event.stopPropagation(); openCatalogPlugin(${pluginJson}, ${latestSession})' class="action-btn details-open-btn">Details</button></div></td>
                </tr>
            `;
        }).join('');
    };

    window.applyCatalogFilters = function() {
        runtime.setCatalogCurrentPage(1);
        const filtered = filterCatalogPlugins(runtime.getCatalogPluginsCache(), getCatalogFilterState());
        window.renderCatalogDashboard(filtered);
        window.renderCatalogRows(filtered);
    };

    window.initializeCatalogFilters = function() {
        if (runtime.getCatalogFiltersInitialized()) return;
        const queryEl = document.getElementById('catalog-filter-query');
        const sortEl = document.getElementById('catalog-filter-sort');
        const typeEl = document.getElementById('catalog-filter-type');
        const orderEl = document.getElementById('catalog-filter-order');

        const controls = [queryEl, sortEl, typeEl, orderEl].filter(Boolean);
        if (controls.length === 0) return;

        controls.forEach((control) => {
            const eventName = control.tagName === 'SELECT' ? 'change' : 'input';
            control.addEventListener(eventName, window.applyCatalogFilters);
        });

        runtime.setCatalogFiltersInitialized(true);
    };

    window.loadCatalog = async function() {
        const list = document.getElementById('catalog-list');
        if (!list) return;
        window.renderCatalogDashboard([]);
        list.innerHTML = '<tr><td colspan="7" class="favorites-empty">Loading plugin store...</td></tr>';

        try {
            const pageSize = 1000;
            let offset = 0;
            let total = null;
            const mergedItems = [];

            while (total === null || mergedItems.length < total) {
                const response = await fetch(`/api/catalog/plugins?limit=${pageSize}&offset=${offset}&sort_by=last_seen&order=desc`);
                const data = await response.json();
                const items = data.items || [];

                if (total === null) total = parseInt(data.total || 0, 10) || 0;
                mergedItems.push(...items);

                if (items.length === 0) break;
                offset += items.length;
                if (offset > 200000) break;
            }

            runtime.setCatalogPluginsCache(mergedItems);
            window.initializeCatalogFilters();
            window.applyCatalogFilters();
        } catch (error) {
            console.error(error);
            window.renderCatalogDashboard([]);
            list.innerHTML = '<tr><td colspan="7" class="favorites-empty">Failed to load plugin store</td></tr>';
        }
    };

    window.openCatalogPlugin = function(plugin, sessionId = 0) {
        if (!plugin || !plugin.slug) return;
        if (sessionId) runtime.setCurrentScanId(sessionId);
        window.currentScanResults = [plugin];
        openPluginModal(0);
    };
})();
