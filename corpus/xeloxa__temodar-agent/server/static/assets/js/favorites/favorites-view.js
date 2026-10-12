(function() {
    const runtime = window.temodarAgentRuntime;

    function getCurrentScanResults() {
        return Array.isArray(window.currentScanResults) ? window.currentScanResults : [];
    }

    function setCurrentScanResults(results) {
        window.currentScanResults = Array.isArray(results) ? results : [];
    }

    window.refreshFavoriteSlugs = async function() {
        try {
            const resp = await fetch('/api/favorites');
            if (!resp.ok) throw new Error(`Failed to fetch favorites: ${resp.status}`);
            const data = await resp.json();
            window.favoriteSlugs = new Set((data.favorites || []).map((p) => p.slug));
        } catch (e) {
            console.error('Failed to refresh favorites:', e);
            window.favoriteSlugs = new Set();
        }
    };

    window.isFavoriteSlug = function(slug) {
        return window.favoriteSlugs instanceof Set && window.favoriteSlugs.has(slug);
    };

    window.loadFavorites = async function() {
        const list = document.getElementById('favorites-list');
        if (!list) return;
        list.innerHTML = '<tr><td colspan="7">Loading...</td></tr>';

        try {
            const resp = await fetch('/api/favorites');
            const data = await resp.json();

            setCurrentScanResults(data.favorites || []);
            renderRecentFavorites(getCurrentScanResults());

            const maxInstalls = getCurrentScanResults().reduce((max, item) => {
                const installs = parseInt(item.installations || 0, 10) || 0;
                return Math.max(max, installs);
            }, 1);

            list.innerHTML = getCurrentScanResults().map((r, index) => {
                const slug = String(r.slug || 'unknown-plugin');
                const slugJs = JSON.stringify(slug);
                const score = parseInt(r.score || 0, 10) || 0;
                const scoreLevel = getRiskClassForResult(score);
                const scoreRatio = Math.max(0, Math.min(100, score));
                const installs = parseInt(r.installations || 0, 10) || 0;
                const installsRatio = maxInstalls > 0 ? Math.min(100, Math.round((installs / maxInstalls) * 100)) : 0;
                const days = parseDaysSinceUpdate(r.days_since_update);
                const updatedClass = getUpdatedChipClass(days);
                const updatedLabel = getUpdatedLabel(days);
                const version = String(r.version || 'n/a');
                const modeClass = r.is_theme ? 'theme' : 'plugin';
                const modeLabel = modeClass.toUpperCase();

                return `
                    <tr class="favorites-row" tabindex="0" onclick="openPluginModal(${index})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openPluginModal(${index});}">
                        <td class="favorites-col-slug"><div class="favorites-slug">${escapeHtml(slug)}</div></td>
                        <td class="favorites-col-version"><span class="favorites-version-chip">${escapeHtml(version)}</span></td>
                        <td class="favorites-col-installs"><div class="favorites-installs" title="${installs.toLocaleString()} installs"><span class="favorites-installs-count">${escapeHtml(formatInstallCount(installs))}</span><span class="favorites-installs-track"><span class="favorites-installs-fill" style="width: ${installsRatio}%;"></span></span></div></td>
                        <td class="favorites-col-score"><div class="favorites-score" title="Risk score ${score}"><span class="favorites-score-pill ${scoreLevel}">${score}</span><span class="favorites-score-meter"><span class="favorites-score-fill ${scoreLevel}" style="width: ${scoreRatio}%;"></span></span></div></td>
                        <td class="favorites-col-updated"><span class="favorites-updated-chip ${updatedClass}">${escapeHtml(updatedLabel)}</span></td>
                        <td class="favorites-col-mode"><span class="history-mode-chip ${modeClass}">${escapeHtml(modeLabel)}</span></td>
                        <td class="favorites-col-actions"><div class="favorites-actions"><span class="favorites-action-open" aria-hidden="true"><span>Open</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg></span><button onclick='event.stopPropagation(); removeFromFavorites(${slugJs})' class="action-btn favorites-action-delete" title="Remove Favorite" aria-label="Remove favorite ${escapeHtml(slug)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button></div></td>
                    </tr>
                `;
            }).join('');

            if (getCurrentScanResults().length === 0) {
                list.innerHTML = '<tr><td colspan="7" class="favorites-empty">No favorites yet</td></tr>';
            }
        } catch (e) {
            console.error(e);
            list.innerHTML = '<tr><td colspan="7" class="favorites-empty">Error loading favorites</td></tr>';
        }
    };

    window.removeFromFavorites = async function(slug) {
        const confirmed = await showConfirm('Remove from favorites?');
        if (!confirmed) return;
        const encodedSlug = encodeURIComponent(String(slug || ''));
        const response = await fetch(`/api/favorites/${encodedSlug}`, { method: 'DELETE' });
        if (!response.ok) {
            showToast('Failed to remove favorite', 'error');
            return;
        }
        window.favoriteSlugs.delete(slug);
        if (typeof window.refreshDashboardFavorites === 'function') {
            window.refreshDashboardFavorites();
        }
        window.loadFavorites();
    };

    window.toggleFavorite = async function(slug) {
        const plugin = getCurrentScanResults().find((p) => p.slug === slug);
        if (!plugin) return;

        await window.refreshFavoriteSlugs();
        const isAlreadyFavorite = window.isFavoriteSlug(slug);

        if (!isAlreadyFavorite) {
            const response = await fetch('/api/favorites', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(plugin)
            });

            let res = { success: false };
            try {
                res = await response.json();
            } catch (_) {}

            if (res.success) {
                window.favoriteSlugs.add(slug);
                showToast('Plugin added to favorites', 'success');
            } else {
                await window.refreshFavoriteSlugs();
                if (window.isFavoriteSlug(slug)) {
                    showToast('Plugin is already in favorites', 'info');
                } else {
                    showToast('Failed to add favorite', 'error');
                }
            }
        } else {
            const confirmed = await showConfirm('Remove from favorites?');
            if (!confirmed) return;
            const encodedSlug = encodeURIComponent(String(slug || ''));
            const response = await fetch(`/api/favorites/${encodedSlug}`, { method: 'DELETE' });
            if (!response.ok) {
                showToast('Failed to remove favorite', 'error');
                return;
            }
            window.favoriteSlugs.delete(slug);
            showToast('Plugin removed from favorites', 'info');
        }

        const state = getUrlState();
        if (state.view === 'plugin-detail') {
            const favBtn = document.getElementById('plugin-fav-btn');
            if (favBtn) {
                favBtn.classList.toggle('active', window.isFavoriteSlug(slug));
                favBtn.title = window.isFavoriteSlug(slug) ? 'In Favorites' : 'Add to Favorites';
                favBtn.setAttribute('aria-label', `${window.isFavoriteSlug(slug) ? 'Remove from' : 'Add to'} favorites`);
            }
        } else if (runtime.getCurrentScanId()) {
            viewScan(runtime.getCurrentScanId());
        }

        if (typeof window.refreshDashboardFavorites === 'function') {
            window.refreshDashboardFavorites();
        }
    };
})();
