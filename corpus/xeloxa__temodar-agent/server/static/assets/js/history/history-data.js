(function() {
    const runtime = window.temodarAgentRuntime;
    const historySemgrepStatsCache = new Map();

    function getHistorySemgrepState(stats, isThemeSession = false) {
        if (isThemeSession) {
            return {
                cls: 'na',
                state: 'N/A',
                count: '--',
                progress: 0,
                title: 'Semgrep is not available for theme sessions.'
            };
        }

        if (!stats) {
            return {
                cls: 'empty',
                state: 'WAIT',
                count: '--/--',
                progress: 0,
                title: 'Semgrep data is not available for this session yet.'
            };
        }

        const scannedCount = parseInt(stats.scanned_count || 0, 10) || 0;
        const totalPlugins = parseInt(stats.total_plugins || 0, 10) || 0;
        const totalFindings = parseInt(stats.total_findings || 0, 10) || 0;
        const progress = Math.max(0, Math.min(100, parseInt(stats.progress || 0, 10) || 0));
        const safeTotal = totalPlugins > 0 ? totalPlugins : Math.max(scannedCount, 0);
        const pair = safeTotal > 0 ? `${scannedCount}/${safeTotal}` : '--/--';

        if (stats.is_running) {
            return {
                cls: 'running',
                state: 'RUN',
                count: pair,
                progress,
                title: `Semgrep scanning in progress (${progress}% - ${pair}).`
            };
        }

        if (scannedCount === 0) {
            return {
                cls: 'empty',
                state: 'WAIT',
                count: safeTotal > 0 ? `0/${safeTotal}` : '0/0',
                progress: 0,
                title: 'Semgrep has not run for this session yet.'
            };
        }

        if (progress >= 100 || (safeTotal > 0 && scannedCount >= safeTotal)) {
            if (totalFindings > 0) {
                return {
                    cls: 'alert',
                    state: 'ISSUE',
                    count: String(totalFindings),
                    progress: 100,
                    title: `${totalFindings} findings detected (${pair} analyzed).`
                };
            }
            return {
                cls: 'complete',
                state: 'CLEAN',
                count: pair,
                progress: 100,
                title: `Semgrep completed clean (${pair} analyzed).`
            };
        }

        return {
            cls: 'partial',
            state: 'PART',
            count: pair,
            progress,
            title: `Partial semgrep progress (${pair}, ${totalFindings} findings).`
        };
    }

    function applyHistorySemgrepBadge(sessionId, stats, isThemeSession = false) {
        const cell = document.getElementById(`history-semgrep-${sessionId}`);
        const stateEl = document.getElementById(`history-semgrep-state-${sessionId}`);
        const countEl = document.getElementById(`history-semgrep-count-${sessionId}`);
        const fillEl = document.getElementById(`history-semgrep-fill-${sessionId}`);
        if (!cell || !stateEl || !countEl || !fillEl) return;

        const state = getHistorySemgrepState(stats, isThemeSession);
        cell.className = `history-semgrep-cell ${state.cls}`;
        cell.title = state.title;
        stateEl.textContent = state.state;
        countEl.textContent = state.count;
        fillEl.style.width = `${state.progress}%`;
    }

    window.hydrateHistorySemgrepBadges = async function(sessions) {
        const pending = (sessions || []).map(async (session) => {
            const sessionId = parseInt(session.id, 10);
            if (!Number.isFinite(sessionId) || sessionId <= 0) return;

            const config = session.config || {};
            const isThemeSession = Boolean(config.themes);
            if (isThemeSession) {
                applyHistorySemgrepBadge(sessionId, null, true);
                return;
            }

            const cached = historySemgrepStatsCache.get(sessionId);
            if (cached) {
                applyHistorySemgrepBadge(sessionId, cached, false);
                return;
            }

            try {
                const response = await fetch(apiNoCacheUrl(`/api/semgrep/bulk/${sessionId}/stats`));
                if (!response.ok) {
                    applyHistorySemgrepBadge(sessionId, null, false);
                    return;
                }
                const stats = await response.json();
                historySemgrepStatsCache.set(sessionId, stats);
                applyHistorySemgrepBadge(sessionId, stats, false);
            } catch (error) {
                applyHistorySemgrepBadge(sessionId, null, false);
            }
        });

        await Promise.allSettled(pending);
    };

    window.loadHistory = async function() {
        try {
            historySemgrepStatsCache.clear();
            const response = await fetch(apiNoCacheUrl('/api/scans'));
            const data = await response.json();
            const sessions = (data.sessions || []).sort((a, b) => new Date(b.created_at || b.start_time) - new Date(a.created_at || a.start_time));
            runtime.setHistorySessionsCache(sessions);
            refreshScanDashboard(sessions);
            initializeHistoryFilters();
            applyHistoryFilters();
        } catch (error) {
            const list = document.getElementById('history-list');
            runtime.setHistorySessionsCache([]);
            if (list) list.innerHTML = '<tr><td colspan="8">Error loading history</td></tr>';
            refreshScanDashboard([]);
        }
    };

    window.deleteScan = async function(id) {
        const confirmed = await showConfirm('Are you sure you want to delete this scan session? This will remove all associated results from the database.');
        if (!confirmed) return;
        try {
            const response = await fetch(`/api/scans/${id}`, { method: 'DELETE' });
            if (response.ok) {
                loadHistory();
            } else {
                const err = await response.json();
                showToast('Failed to delete scan: ' + (err.detail || 'Unknown error'), 'error');
            }
        } catch (error) {
            showToast('Error deleting scan: ' + error.message, 'error');
        }
    };
})();
