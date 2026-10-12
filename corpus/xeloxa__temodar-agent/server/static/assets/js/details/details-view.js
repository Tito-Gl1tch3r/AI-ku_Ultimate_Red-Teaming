(function() {
    const runtime = window.temodarAgentRuntime;

    window.changeDetailsPage = function(delta) {
        const totalPages = Math.max(1, Math.ceil((runtime.getDetailsResultsCache().length || 0) / runtime.getDetailsPageSize()));
        runtime.setDetailsCurrentPage(Math.min(Math.max(1, runtime.getDetailsCurrentPage() + delta), totalPages));
        window.renderDetailsRows(runtime.getDetailsResultsCache());
    };

    function setDetailsBulkRunLabel(runBtn, label) {
        runBtn.innerHTML = `<span class="semgrep-logo-icon" aria-hidden="true"></span><span class="semgrep-btn-label">${escapeHtml(label)}</span>`;
    }

    window.setDetailsBulkControls = function(state, meta = {}) {
        const runBtn = document.getElementById('details-bulk-run');
        const stopBtn = document.getElementById('details-bulk-stop');
        if (!runBtn || !stopBtn) return;

        if (state === 'running') {
            const scanned = Number(meta.scanned || 0);
            const total = Number(meta.total || 0);
            const currentSlug = String(meta.currentSlug || '').trim();
            runBtn.disabled = true;
            setDetailsBulkRunLabel(runBtn, 'Scanning...');
            runBtn.title = currentSlug ? `Scanning ${scanned}/${total}: ${currentSlug}` : `Scanning ${scanned}/${total}`;
            stopBtn.style.display = 'inline-flex';
            stopBtn.disabled = false;
            return;
        }

        if (state === 'paused') {
            runBtn.disabled = false;
            setDetailsBulkRunLabel(runBtn, 'Resume Scan All');
            runBtn.title = 'Bulk Semgrep paused';
            stopBtn.style.display = 'none';
            return;
        }

        if (state === 'completed') {
            runBtn.disabled = false;
            setDetailsBulkRunLabel(runBtn, 'Scan All (Semgrep)');
            const findings = Number(meta.findings || 0);
            runBtn.title = `Completed${Number.isFinite(findings) ? `: ${findings} findings` : ''}`;
            stopBtn.style.display = 'none';
            return;
        }

        runBtn.disabled = false;
        setDetailsBulkRunLabel(runBtn, 'Scan All (Semgrep)');
        runBtn.title = '';
        stopBtn.style.display = 'none';
    };

    function getDetailsFilterState() {
        const queryEl = document.getElementById('details-filter-query');
        const installsEl = document.getElementById('details-filter-installs');
        const sortEl = document.getElementById('details-filter-sort');
        const updatedSortEl = document.getElementById('details-filter-updated-sort');

        return {
            query: String(queryEl ? queryEl.value : '').trim().toLowerCase(),
            installs: String(installsEl ? installsEl.value : 'default').toLowerCase(),
            sort: String(sortEl ? sortEl.value : 'default').toLowerCase(),
            updatedSort: String(updatedSortEl ? updatedSortEl.value : 'default').toLowerCase()
        };
    }

    function getDetailsSemgrepState(result) {
        const semgrep = result && result.semgrep ? result.semgrep : null;
        if (!semgrep) return 'wait';

        const status = String(semgrep.status || '').toLowerCase();
        if (status === 'running' || status === 'pending') return 'run';
        if (status === 'failed') return 'fail';
        if (status === 'completed') {
            const findings = parseInt(semgrep.findings_count || 0, 10) || 0;
            return findings > 0 ? 'issue' : 'clean';
        }
        return 'wait';
    }

    function getDetailsSemgrepIssueCount(result) {
        if (!result || !result.semgrep) return 0;
        const status = String(result.semgrep.status || '').toLowerCase();
        if (status !== 'completed') return 0;
        return parseInt(result.semgrep.findings_count || 0, 10) || 0;
    }

    function getDetailsUpdatedDays(result) {
        const days = parseDaysSinceUpdate(result && result.days_since_update);
        return days == null ? Number.POSITIVE_INFINITY : days;
    }

    window.renderDetailsDashboard = function(results) {
        const dashboard = document.getElementById('details-dashboard');
        if (!dashboard) return;

        const rows = Array.isArray(results) ? results : [];
        const total = rows.length;
        if (total === 0) {
            dashboard.innerHTML = '';
            return;
        }

        const highCount = rows.filter(r => (parseInt(r && r.score || 0, 10) || 0) >= 40).length;
        const midCount = rows.filter(r => {
            const score = parseInt(r && r.score || 0, 10) || 0;
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
            <div class="details-stat-card details-stat-card-total"><div class="details-stat-label">Scan inventory</div><div class="details-stat-value">${total}</div><div class="details-stat-sub">Total plugins/themes in this scan</div><div class="details-stat-track"><span class="details-stat-fill details-fill-blue" style="width:100%"></span></div></div>
            <div class="details-stat-card details-stat-card-progress"><div class="details-stat-label">Semgrep progress</div><div class="details-stat-value">${scannedCount} / ${total}</div><div class="details-stat-sub">Processed / Total • ${remainingCount} remaining</div><div class="details-stat-track"><span class="details-stat-fill details-fill-primary" style="width:${toPct(scannedCount, total)}%"></span><span class="details-stat-fill details-fill-wait" style="width:${toPct(remainingCount, total)}%"></span></div></div>
            <div class="details-stat-card"><div class="details-stat-label">Risk split</div><div class="details-stat-value">${highCount} / ${midCount} / ${lowCount}</div><div class="details-stat-sub">High / Medium / Low</div><div class="details-stat-track"><span class="details-stat-fill details-fill-high" style="width:${toPct(highCount, total)}%"></span><span class="details-stat-fill details-fill-mid" style="width:${toPct(midCount, total)}%"></span><span class="details-stat-fill details-fill-low" style="width:${toPct(lowCount, total)}%"></span></div></div>
            <div class="details-stat-card"><div class="details-stat-label">Semgrep</div><div class="details-stat-value">${issueCount} / ${cleanCount} / ${runningCount}</div><div class="details-stat-sub">Issue / Clean / Running</div><div class="details-stat-track"><span class="details-stat-fill details-fill-issue" style="width:${toPct(issueCount, total)}%"></span><span class="details-stat-fill details-fill-clean" style="width:${toPct(cleanCount, total)}%"></span><span class="details-stat-fill details-fill-wait" style="width:${toPct(waitingCount, total)}%"></span><span class="details-stat-fill details-fill-fail" style="width:${toPct(failedCount, total)}%"></span></div></div>
        `;
    };

    function sortDetailsResults(results, sortState) {
        const safeResults = Array.isArray(results) ? [...results] : [];
        const state = sortState || {};
        const comparators = [];

        if (state.sort === 'semgrep_desc') {
            comparators.push((a, b) => getDetailsSemgrepIssueCount(b) - getDetailsSemgrepIssueCount(a));
            comparators.push((a, b) => (parseInt(b && b.score || 0, 10) || 0) - (parseInt(a && a.score || 0, 10) || 0));
        } else if (state.sort === 'semgrep_asc') {
            comparators.push((a, b) => getDetailsSemgrepIssueCount(a) - getDetailsSemgrepIssueCount(b));
            comparators.push((a, b) => (parseInt(b && b.score || 0, 10) || 0) - (parseInt(a && a.score || 0, 10) || 0));
        } else if (state.sort === 'score_desc') {
            comparators.push((a, b) => (parseInt(b && b.score || 0, 10) || 0) - (parseInt(a && a.score || 0, 10) || 0));
        } else if (state.sort === 'score_asc') {
            comparators.push((a, b) => (parseInt(a && a.score || 0, 10) || 0) - (parseInt(b && b.score || 0, 10) || 0));
        }

        if (state.installs === 'installs_desc') {
            comparators.push((a, b) => (parseInt(b && b.installations || 0, 10) || 0) - (parseInt(a && a.installations || 0, 10) || 0));
        } else if (state.installs === 'installs_asc') {
            comparators.push((a, b) => (parseInt(a && a.installations || 0, 10) || 0) - (parseInt(b && b.installations || 0, 10) || 0));
        }

        if (state.updatedSort === 'updated_newest') {
            comparators.push((a, b) => getDetailsUpdatedDays(a) - getDetailsUpdatedDays(b));
        } else if (state.updatedSort === 'updated_oldest') {
            comparators.push((a, b) => getDetailsUpdatedDays(b) - getDetailsUpdatedDays(a));
        }

        if (comparators.length === 0) return safeResults;

        safeResults.sort((a, b) => {
            for (const comparator of comparators) {
                const diff = comparator(a, b);
                if (diff !== 0) return diff;
            }
            return 0;
        });

        return safeResults;
    }

    function filterDetailsResults(results, filterState) {
        const state = filterState || getDetailsFilterState();

        const filtered = (results || []).filter((result) => {
            const slug = String((result && result.slug) || '').toLowerCase();
            const version = String((result && result.version) || '').toLowerCase();
            const semgrepState = getDetailsSemgrepState(result);
            const semgrepIssues = getDetailsSemgrepIssueCount(result);
            const risk = getRiskClassForResult(parseInt((result && result.score) || 0, 10) || 0);
            const installs = parseInt((result && result.installations) || 0, 10) || 0;
            const updatedDays = getDetailsUpdatedDays(result);

            if (state.query) {
                const haystack = `${slug} ${version} ${semgrepState} ${risk} ${semgrepIssues} ${installs} ${updatedDays}`;
                if (!haystack.includes(state.query)) return false;
            }

            return true;
        });

        return sortDetailsResults(filtered, state);
    }

    window.applyDetailsFilters = function() {
        runtime.setDetailsCurrentPage(1);
        const filtered = filterDetailsResults(runtime.getDetailsSourceCache(), getDetailsFilterState());
        window.renderDetailsRows(filtered);
    };

    window.renderDetailsRows = function(results) {
        const list = document.getElementById('details-list');
        if (!list) return;

        const safeResults = results || [];
        runtime.setDetailsResultsCache(safeResults);

        const totalPages = Math.max(1, Math.ceil(safeResults.length / runtime.getDetailsPageSize()));
        runtime.setDetailsCurrentPage(Math.min(Math.max(1, runtime.getDetailsCurrentPage()), totalPages));
        const pageStart = (runtime.getDetailsCurrentPage() - 1) * runtime.getDetailsPageSize();
        const pagedResults = safeResults.slice(pageStart, pageStart + runtime.getDetailsPageSize());

        window.updateTablePagination('details', safeResults.length, runtime.getDetailsCurrentPage(), runtime.getDetailsPageSize());

        if (safeResults.length === 0) {
            list.innerHTML = '<tr><td colspan="7" class="favorites-empty">No plugins match the current filters</td></tr>';
            return;
        }

        const maxInstalls = safeResults.reduce((max, item) => {
            const installs = parseInt(item.installations || 0, 10) || 0;
            return Math.max(max, installs);
        }, 1);

        list.innerHTML = pagedResults.map((result) => renderDetailsRow(result, maxInstalls)).join('');
    };

    function getDetailsInstallsMeta(result, maxInstalls) {
        const installs = parseInt(result.installations || 0, 10) || 0;
        const installsRatio = maxInstalls > 0 ? Math.min(100, Math.round((installs / maxInstalls) * 100)) : 0;
        const installsLevel = installsRatio >= 70 ? 'high' : (installsRatio >= 35 ? 'medium' : 'low');
        return { installs, installsRatio, installsLevel };
    }

    function getDetailsSemgrepMeta(result, slug) {
        let semgrepTone = 'empty';
        let semgrepCount = '--';
        let semgrepState = 'WAIT';
        let semgrepProgress = 0;
        let semgrepTitle = 'Semgrep has not run for this plugin yet.';

        if (result.semgrep) {
            if (result.semgrep.status === 'completed') {
                const issues = parseInt(result.semgrep.findings_count || 0, 10) || 0;
                semgrepTone = issues > 0 ? 'alert' : 'complete';
                semgrepCount = String(issues);
                semgrepState = issues > 0 ? 'ISSUE' : 'CLEAN';
                semgrepProgress = 100;
                semgrepTitle = issues > 0 ? `${issues} finding(s) detected for ${slug}.` : `No findings detected for ${slug}.`;
            } else if (result.semgrep.status === 'running' || result.semgrep.status === 'pending') {
                semgrepTone = 'running';
                semgrepCount = '--';
                semgrepState = 'SCANNING';
                semgrepProgress = 35;
                semgrepTitle = `Semgrep scan is running for ${slug}.`;
            } else if (result.semgrep.status === 'failed') {
                semgrepTone = 'alert';
                semgrepCount = 'ERR';
                semgrepState = 'FAIL';
                semgrepProgress = 100;
                semgrepTitle = `Semgrep scan failed for ${slug}.`;
            }
        }

        return { semgrepTone, semgrepCount, semgrepState, semgrepProgress, semgrepTitle };
    }

    function renderDetailsRow(result, maxInstalls) {
        const index = window.currentScanResults.indexOf(result);
        const slug = String(result.slug || 'unknown-plugin');
        const slugJs = JSON.stringify(slug);
        const score = parseInt(result.score || 0, 10) || 0;
        const scoreRatio = Math.max(0, Math.min(100, score));
        const riskClass = getRiskClassForResult(score);
        const { installs, installsRatio, installsLevel } = getDetailsInstallsMeta(result, maxInstalls);
        const modeClass = result.is_theme ? 'theme' : 'plugin';
        const modeLabel = modeClass.toUpperCase();
        const { semgrepTone, semgrepCount, semgrepState, semgrepProgress, semgrepTitle } = getDetailsSemgrepMeta(result, slug);
        const days = parseDaysSinceUpdate(result.days_since_update);
        const updatedLabel = getUpdatedLabel(days);
        const isFav = isFavoriteSlug(slug);
        const wpLink = result.wp_org_link || (result.is_theme ? `https://wordpress.org/themes/${slug}/` : `https://wordpress.org/plugins/${slug}/`);

        return `
            <tr class="history-row details-results-row" tabindex="0" onclick="openPluginModal(${index})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openPluginModal(${index});}">
                <td class="details-col-slug"><span class="details-slug">${escapeHtml(slug)}</span>${result.is_duplicate ? '<span class="details-dup-chip">Seen Before · DB</span>' : ''}</td>
                <td class="details-col-version"><span class="history-semgrep-pill">${escapeHtml(String(result.version || 'n/a'))}</span></td>
                <td class="details-col-score"><div class="history-risk-cell" title="Risk score ${score}"><span class="history-risk-pill ${riskClass}">${score}</span><span class="history-risk-meter"><span class="history-risk-fill ${riskClass}" style="width:${scoreRatio}%;"></span></span></div></td>
                <td class="details-col-updated"><span class="history-date-stamp">${escapeHtml(updatedLabel)}</span></td>
                <td class="details-col-installs"><div class="history-found-cell" title="${installs.toLocaleString()} installs"><span class="history-found-count">${escapeHtml(formatInstallCount(installs))}</span><span class="history-found-label">installs</span><span class="history-found-track"><span class="history-found-fill ${installsLevel}" style="width: ${installsRatio}%;"></span></span></div></td>
                <td class="details-col-semgrep"><div class="history-semgrep-cell ${semgrepTone}" title="${escapeHtml(semgrepTitle)}"><span class="history-semgrep-pill">${escapeHtml(semgrepCount)}</span><span class="history-semgrep-meter"><span class="history-semgrep-fill" style="width: ${semgrepProgress}%;"></span></span><span class="history-semgrep-state">${escapeHtml(semgrepState)}</span></div></td>
                <td class="details-col-actions"><div class="details-row-actions"><span class="history-mode-chip ${modeClass}">${escapeHtml(modeLabel)}</span><button onclick='event.stopPropagation(); toggleFavorite(${slugJs})' class="action-btn details-fav-btn${isFav ? ' active' : ''}" title="${isFav ? 'In Favorites' : 'Add to Favorites'}" aria-label="Toggle favorite ${escapeHtml(slug)}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg></button><a href="${escapeHtml(wpLink)}" target="_blank" rel="noreferrer noopener" onclick="event.stopPropagation();" class="action-btn details-wp-btn" aria-label="Open on WordPress.org" title="Open on WordPress.org"><span class="wp-logo-icon" aria-hidden="true"></span></a><button onclick="event.stopPropagation(); openPluginModal(${index})" class="action-btn details-open-btn">Details</button></div></td>
            </tr>
        `;
    }

    function refreshDetailsRowsPreservePage() {
        const filtered = filterDetailsResults(runtime.getDetailsSourceCache(), getDetailsFilterState());
        const totalPages = Math.max(1, Math.ceil((filtered.length || 0) / runtime.getDetailsPageSize()));
        runtime.setDetailsCurrentPage(Math.min(Math.max(1, runtime.getDetailsCurrentPage()), totalPages));
        window.renderDetailsRows(filtered);
    }

    function autoAdvanceDetailsPageIfNeeded() {
        const totalPages = Math.max(1, Math.ceil((runtime.getDetailsResultsCache().length || 0) / runtime.getDetailsPageSize()));
        if (runtime.getDetailsCurrentPage() >= totalPages) return;

        const start = (runtime.getDetailsCurrentPage() - 1) * runtime.getDetailsPageSize();
        const pageRows = (runtime.getDetailsResultsCache() || []).slice(start, start + runtime.getDetailsPageSize());
        if (pageRows.length === 0) return;

        const hasWaiting = pageRows.some((r) => !r.semgrep || !r.semgrep.status || ['pending'].includes(String(r.semgrep.status).toLowerCase()));
        const hasRunning = pageRows.some((r) => r.semgrep && ['running'].includes(String(r.semgrep.status).toLowerCase()));

        if (!hasWaiting && !hasRunning) {
            runtime.setDetailsCurrentPage(Math.min(runtime.getDetailsCurrentPage() + 1, totalPages));
            window.renderDetailsRows(runtime.getDetailsResultsCache());
        }
    }

    function resolveBulkControlsState(stats, currentSlug) {
        const runningCount = Number(stats.running_count || 0);
        const pendingCount = Number(stats.pending_count || 0);
        const total = Number(stats.total_plugins || 0);
        const scanned = Number(stats.scanned_count || 0);
        const findings = stats.total_findings || 0;

        if (stats.is_running) {
            return {
                state: 'running',
                meta: { scanned, total, currentSlug },
                shouldAutoAdvance: true,
            };
        }
        if (runningCount === 0 && pendingCount === 0 && scanned > 0) {
            return { state: 'completed', meta: { findings }, shouldAutoAdvance: false };
        }
        if ((runningCount > 0 || pendingCount > 0) && scanned > 0) {
            return { state: 'paused', meta: {}, shouldAutoAdvance: false };
        }
        if (total > 0 && scanned >= total) {
            return { state: 'completed', meta: { findings }, shouldAutoAdvance: false };
        }
        return { state: 'idle', meta: {}, shouldAutoAdvance: false };
    }

    window.refreshDetailsBulkStatus = async function(sessionId) {
        const statsResp = await fetch(`/api/semgrep/bulk/${sessionId}/stats`);
        const stats = await statsResp.json();

        const resultsResp = await fetch(apiNoCacheUrl(`/api/scans/${sessionId}/results?limit=500`));
        const resultsData = await resultsResp.json();
        window.currentScanResults = resultsData.results || [];
        runtime.setDetailsSourceCache(window.currentScanResults);

        let currentSlug = '';
        const runningItem = window.currentScanResults.find((r) => r.semgrep && ['running', 'pending'].includes(String(r.semgrep.status || '').toLowerCase()));
        if (runningItem) currentSlug = String(runningItem.slug || '');

        window.renderDetailsDashboard(window.currentScanResults);
        refreshDetailsRowsPreservePage();

        const bulkControlState = resolveBulkControlsState(stats, currentSlug);
        window.setDetailsBulkControls(bulkControlState.state, bulkControlState.meta);
        if (bulkControlState.shouldAutoAdvance) {
            autoAdvanceDetailsPageIfNeeded();
        }

        return stats;
    }

    window.startDetailsBulkSemgrep = async function() {
        if (!runtime.getCurrentScanId()) return;

        try {
            const rulesResponse = await fetch('/api/semgrep/rules');
            const rulesData = await rulesResponse.json();
            const activeRulesets = (rulesData.rulesets || []).filter(r => r.enabled).length;
            const activeCustomRules = (rulesData.custom_rules || []).filter(r => r.enabled).length;
            if (activeRulesets === 0 && activeCustomRules === 0) {
                showToast('Semgrep is disabled. Enable at least one ruleset first.', 'warn');
                switchTab('semgrep');
                return;
            }
        } catch (e) {
            showToast('Failed to check Semgrep configuration.', 'error');
            return;
        }

        const confirmed = await showConfirm('Start Semgrep scan for all plugins in this scan?');
        if (!confirmed) return;

        try {
            const response = await fetch(`/api/semgrep/bulk/${runtime.getCurrentScanId()}`, { method: 'POST' });
            const data = await response.json();
            if (!data.success) {
                showToast('Failed to start bulk scan: ' + (data.detail || 'Unknown error'), 'error');
                return;
            }

            window.setDetailsBulkControls('running', { scanned: 0, total: data.count || 0 });

            const existing = runtime.getDetailsBulkPollingInterval();
            if (existing) clearInterval(existing);
            const timer = setInterval(async () => {
                try {
                    const stats = await window.refreshDetailsBulkStatus(runtime.getCurrentScanId());
                    if (!stats.is_running) {
                        clearInterval(timer);
                        runtime.setDetailsBulkPollingInterval(null);
                    }
                } catch (err) {
                    console.error('Details bulk polling error', err);
                }
            }, 1500);
            runtime.setDetailsBulkPollingInterval(timer);
        } catch (e) {
            showToast('Error: ' + e.message, 'error');
        }
    };

    window.stopDetailsBulkSemgrep = async function() {
        if (!runtime.getCurrentScanId()) return;
        const confirmed = await showConfirm('Stop bulk Semgrep scan?');
        if (!confirmed) return;

        try {
            const response = await fetch(`/api/semgrep/bulk/${runtime.getCurrentScanId()}/stop`, { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                window.setDetailsBulkControls('paused');
            }
        } catch (e) {
            showToast('Error: ' + e.message, 'error');
        }
    };

    window.initializeDetailsFilters = function() {
        if (runtime.getDetailsFiltersInitialized()) return;
        const queryEl = document.getElementById('details-filter-query');
        const installsEl = document.getElementById('details-filter-installs');
        const sortEl = document.getElementById('details-filter-sort');
        const updatedSortEl = document.getElementById('details-filter-updated-sort');

        const controls = [queryEl, installsEl, sortEl, updatedSortEl].filter(Boolean);
        if (controls.length === 0) return;

        controls.forEach((control) => {
            const eventName = control.tagName === 'SELECT' ? 'change' : 'input';
            control.addEventListener(eventName, window.applyDetailsFilters);
        });

        runtime.setDetailsFiltersInitialized(true);
    };
})();
