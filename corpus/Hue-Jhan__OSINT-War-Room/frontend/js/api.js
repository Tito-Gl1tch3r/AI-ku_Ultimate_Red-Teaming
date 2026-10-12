let appState = {
    refreshRate: 10000,
    paused: false,
    accounts: [],
    tweets: []
};

async function fetchVix() {
    try {
        const res = await fetch('/api/economy/vix');
        const result = await res.json();
        if (result.status === 'success') {
            const el = document.querySelector('.vix-overlay h1');
            const chEl = document.querySelector('.vix-overlay span');
            if (el) el.textContent = `$${result.price}`;
            if (chEl) {
                const up = result.change_pct >= 0;
                chEl.style.color = up ? '#4ade80' : '#ef4444';
                chEl.textContent = `${up ? '+' : ''}${result.change_pct}%`;
            }
        }
    } catch(e) {}
}

const channelNames = {
    "monitor_the_situation": "Situation Monitor",
    "aljazeeraglobal": "Al Jazeera",
    "OSINTWarfare": "OSINT Warfare",
    "terroralarm": "Terror Alarm",
    "ConflictsTracker": "Conflicts Tracker"
};

function timeSince(dateString) {
    const seconds = Math.floor((new Date() - new Date(dateString)) / 1000);
    let interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + "d";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + "h";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + "m";
    return "Just now";
}

function formatTimeElapsed(timestamp) {
    const diff = Date.now() - timestamp;
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h`;
}

function renderFeed(data = null) {
    const container = document.getElementById('tweet-feed-container');
    if (!container) return;

    const tweetsToRender = data || appState.tweets;

    for (let i = tweetsToRender.length - 1; i >= 0; i--) {
        const tweet = tweetsToRender[i];
        if (document.getElementById(`msg-${tweet.id}`)) continue;
        
        // Add this color mapping logic inside the rendering loop for each item
        let dotColor = '#888888'; // Default grey
        if (tweet.channel === 'monitor_the_situation') dotColor = '#eab308'; // Glowing Yellow
        else if (tweet.channel === 'aljazeeraglobal') dotColor = '#ef4444'; // Glowing Red
        else if (tweet.channel === 'OSINTWarfare') dotColor = '#22c55e'; // Glowing Green
        else if (tweet.channel === 'terroralarm') dotColor = '#3b82f6'; // Glowing Blue
        else if (tweet.channel === 'ConflictsTracker') dotColor = '#a855f7'; // Glowing Purple
        const dotStyle = `background-color: ${dotColor}; color: ${dotColor}; box-shadow: 0 0 8px ${dotColor};`

        const displayName = channelNames[tweet.channel] || tweet.channel;
        const mediaIcon = tweet.has_media ? '<i class="fa-solid fa-camera"></i>' : '';

        const html = `
        <div class="tweet-card" id="msg-${tweet.id}">
            <div class="tweet-header">
                <div>
                    <div class="source-dot" style="${dotStyle}"></div>
                    <span class="tweet-user">${displayName}</span>
                </div>
                <a href="${tweet.url || '#'}" target="_blank" class="tweet-link" title="Open Post"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>
            </div>
            <div class="tweet-content">${tweet.text}</div>
            <div class="tweet-footer">
                <span>${mediaIcon}</span>
                <span class="time-ago" data-time="${tweet.timestamp}">${timeSince(tweet.timestamp)}</span>
            </div>
        </div>
        `;
        container.insertAdjacentHTML('afterbegin', html);
        window._sfx?.news();
    }
}

async function fetchLiveAlerts() {
    if (appState.paused) return;
    try {
        const response = await fetch('/api/news/feed');
        const result = await response.json();
        if (result.status === 'success') {
            renderFeed(result.data);
        }
    } catch (error) {
        console.error("Error fetching alerts:", error);
    }
}

async function fetchMarketData() {
    try {
        const res = await fetch('/api/economy/markets');
        const result = await res.json();
        if (result.status === 'success') {
            renderMarketData(result.data);
            // Update VIX gauge from the same response
            const vix = result.data.find(d => d.category === 'Fear');
            if (vix) {
                const el = document.querySelector('.vix-overlay h1');
                const chEl = document.querySelector('.vix-overlay span');
                if (el) el.textContent = vix.price;
                if (chEl) {
                    chEl.style.color = vix.type === 'up' ? '#4ade80' : '#ef4444';
                    chEl.textContent = vix.change;
                }
            }
        }
    } catch(e) { console.warn("Market fetch failed", e); }
}

function renderPizzaData(data) {
    const container = document.getElementById('pizza-content');
    if (!container) return;
    container.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.className = 'pizza-container';

    const yAxis = document.createElement('div');
    yAxis.className = 'pizza-y-axis';
    yAxis.textContent = 'ORDER VOLUME';
    wrapper.appendChild(yAxis);

    const chartArea = document.createElement('div');
    chartArea.className = 'pizza-chart-area';

    const barsContainer = document.createElement('div');
    barsContainer.className = 'pizza-chart';
    data.forEach(val => {
        const bar = document.createElement('div');
        bar.className = `pizza-bar ${val > 80 ? 'active' : ''}`;
        bar.style.height = `${val}%`;
        barsContainer.appendChild(bar);
    });
    chartArea.appendChild(barsContainer);

    const xAxis = document.createElement('div');
    xAxis.className = 'pizza-x-axis';
    xAxis.innerHTML = '<span>6a</span><span>9a</span><span>12p</span><span>3p</span><span>6p</span><span>9p</span><span>12a</span><span>3a</span>';
    chartArea.appendChild(xAxis);

    const legend = document.createElement('div');
    legend.className = 'pizza-legend';
    legend.innerHTML = '<span style="color:#333">■</span> Usual <span style="color:#f97316">■</span> Now';
    chartArea.appendChild(legend);

    wrapper.appendChild(chartArea);
    container.appendChild(wrapper);
}

function renderMarketData(data) {
    const container = document.getElementById('module-stocks');
    if (!container) return;
    container.innerHTML = '';

    const legend = document.createElement('div');
    legend.className = 'market-header-row';
    legend.innerHTML = '<span>SYMBOL</span><span>PRICE</span><span>CHG</span>';
    container.appendChild(legend);

    const table = document.createElement('div');
    table.className = 'market-table';
    let lastCategory = null;

    // Filter out VIX from the table — it's shown in the gauge, not the table
    data.filter(item => item.category !== 'Fear').forEach((item, index) => {
        if (item.category !== lastCategory && index > 0) {
            const sep = document.createElement('div');
            sep.className = 'market-separator';
            table.appendChild(sep);
        }
        lastCategory = item.category;

        const el = document.createElement('div');
        el.className = 'market-row';
        const arrow = item.type === 'up' ? '▲' : '▼';
        el.innerHTML = `
            <div class="market-symbol">${item.icon} ${item.symbol}</div>
            <div class="market-price">${item.price}</div>
            <div class="market-change"><span class="${item.type}">${arrow} ${item.change}</span></div>
        `;
        table.appendChild(el);
    });
    container.appendChild(table);
}

async function fetchPolymarketData() {
    try {
        const res = await fetch('/api/economy/polymarket');
        const result = await res.json();
        if (result.status === 'success') {
            renderPolymarketData(result.data, result.top_volume || []);
        }
    } catch(e) { console.warn("Polymarket fetch failed", e); }
}

function renderPolymarketData(markets, topVolume = []) {
    const container = document.getElementById('module-poly');
    if (!container) return;

    const formatVol = (v) => {
        if (v >= 1000000) return `$${(v/1000000).toFixed(1)}M`;
        if (v >= 1000) return `$${(v/1000).toFixed(0)}K`;
        return `$${v.toFixed(0)}`;
    };

    container.innerHTML = `
        <div class="card-title" style="color:#60a5fa; text-shadow:0 0 12px rgba(59,130,246,0.8); padding: 10px 10px 6px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="margin-right:6px;">
                <circle cx="12" cy="12" r="12" fill="#2563eb"/>
                <path d="M7 7h5a5 5 0 0 1 0 10H7V7z" stroke="white" stroke-width="2"/>
            </svg>
            Polymarket Bets
        </div>
        <div class="poly-container">
            ${markets.map(m => {
                const changeColor = m.change_pct >= 0 ? '#10b981' : '#ef4444';
                const changeArrow = m.change_pct >= 0 ? '📈' : '📉';
                const sparkPath = m.yes_prob > 50
                    ? `M0,14 L10,10 L20,11 L30,6 L40,${14 - (m.yes_prob / 10)}`
                    : `M0,4 L10,7 L20,10 L30,11 L40,${4 + ((100 - m.yes_prob) / 10)}`;
                return `
                <div class="poly-card">
                    <div class="poly-header">
                        <div class="poly-question">${m.question}</div>
                        <a href="${m.url}" target="_blank"><i class="fa-solid fa-arrow-up-right-from-square poly-link"></i></a>
                    </div>
                    <div class="poly-data-row">
                        <span class="poly-percent">${m.yes_prob}% Yes</span>
                        <svg class="poly-spark" viewBox="0 0 40 15" stroke="${m.yes_prob >= 50 ? '#10b981' : '#ef4444'}">
                            <path d="${sparkPath}" fill="none"/>
                        </svg>
                    </div>
                    <div class="poly-bar-container">
                        <div class="poly-bar-yes" style="width:${m.yes_prob}%"></div>
                        <div class="poly-bar-no" style="width:${m.no_prob}%"></div>
                    </div>
                    <div class="poly-meta">
                        <span>Vol: ${formatVol(m.volume24hr)}</span>
                        <span style="color:${changeColor}">${changeArrow} ${Math.abs(m.change_pct)}% change</span>
                    </div>
                </div>`;
            }).join('')}
        </div>
        ${topVolume.length ? `
        <div style="border-top:1px solid var(--border-panel); margin-top:8px; padding: 8px 10px 4px;">
            <div style="font-size:10px; color:#eab308; text-shadow:0 0 8px #eab30888; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; font-weight:700;">
                🏆 Top by Total Volume
            </div>
            ${topVolume.map(m => {
                const yc = m.yes_prob >= 50 ? '#10b981' : '#ef4444';
                const changeColor = m.change_pct >= 0 ? '#10b981' : '#ef4444';
                const changeArrow = m.change_pct >= 0 ? '📈' : '📉';
                return `
                <div class="poly-card" style="border-color:#eab30833; box-shadow: 0 0 8px #eab30818;">
                    <div class="poly-header">
                        <div class="poly-question">${m.question}</div>
                        <a href="${m.url}" target="_blank"><i class="fa-solid fa-arrow-up-right-from-square poly-link"></i></a>
                    </div>
                    <div class="poly-data-row">
                        <span class="poly-percent" style="color:${yc};">${m.yes_prob}% Yes</span>
                    </div>
                    <div class="poly-bar-container">
                        <div class="poly-bar-yes" style="width:${m.yes_prob}%; background:#eab308;"></div>
                        <div class="poly-bar-no" style="width:${m.no_prob}%; background:#44310a;"></div>
                    </div>
                    <div class="poly-meta">
                        <span>Total Vol: ${formatVol(m.total_volume)}</span>
                        <span style="color:${changeColor};">${changeArrow} ${Math.abs(m.change_pct)}% change</span>
                    </div>
                </div>`;
            }).join('')}
        </div>` : ''}`;
}


async function fetchTickerHeadlines() {
    try {
        const res = await fetch('/api/economy/ticker');
        const result = await res.json();
        if (result.status === 'success' && result.data.length) {
            updateTicker(result.data);
        }
    } catch(e) { console.warn("Ticker fetch failed", e); }
}

function updateTicker(headlines) {
    const content = document.getElementById('ticker-content');
    if (!content) return;
    
    const html = headlines.map(h =>
        `<a href="${h.url}" target="_blank" class="ticker-item">
            <span class="ticker-source">${h.source}</span>
            <span class="ticker-title">${h.title}</span>
        </a>`
    ).join('<span class="ticker-sep">◆</span>');
    
    content.innerHTML = html + '<span class="ticker-sep">◆</span>' + html; // duplicate for seamless loop
    
    // Recalculate animation duration based on content width
    // ~120px per second feels like broadcast TV
    const totalWidth = content.scrollWidth / 2;
    const duration = Math.max(totalWidth / 120, 20);
    content.style.animationDuration = `${duration}s`;
}

export function initDataPolling() {
    fetchMarketData();
    setInterval(fetchMarketData, 60000)

    fetchPolymarketData();
    setInterval(fetchPolymarketData, 300000); // refresh every 5 min

    fetchTickerHeadlines();
    setInterval(fetchTickerHeadlines, 120000); // refresh every 2 minutes

    async function fetchPizzaData() {
        try {
            const res = await fetch('/api/economy/pizza');
            const result = await res.json();
            if (result.status === 'success') renderPizzaModal(result.data);
        } catch(e) { console.warn("Pizza fetch failed", e); }
    }

    function renderPizzaModal(data) {
        const levelColors = { 1: '#ef4444', 2: '#f97316', 3: '#f59e0b', 4: '#10b981' };
        const levelLabels = { 1: 'CRITICAL', 2: 'HIGH', 3: 'ELEVATED', 4: 'NORMAL' };
        const color = levelColors[data.doughcon] || '#888';
        const label = levelLabels[data.doughcon] || 'UNKNOWN';

        const doughconEl = document.getElementById('pizza-doughcon-level');
        if (doughconEl) {
            doughconEl.innerHTML = `
                <span style="font-size:20px; font-weight:900; letter-spacing:2px; color:${color}; text-shadow:0 0 14px ${color};">
                    DOUGHCON ${data.doughcon}
                </span>
                <span class="pizza-badge" style="background:${color}22; border:1px solid ${color}; color:${color}; margin-left:8px;">
                    ${label}
                </span>`;
        }

        const statsEl = document.getElementById('pizza-stats');
        if (statsEl) {
            const waitText = data.avgWait > 0 ? `Avg wait: <b>${data.avgWait} min</b>` : 'Stores closed';
            statsEl.innerHTML = `${waitText} &nbsp;·&nbsp; <b>${data.storesOpen}/${data.totalStores}</b> stores open`;
        }

        // Render history bar chart
        const chartEl = document.getElementById('pizza-chart');
        if (chartEl) {
            if (!data.graph?.length) {
                // API failed — flat bars with error message
                chartEl.innerHTML = Array(12).fill(`<div class="pizza-bar" style="height:4%; background:#333;"></div>`).join('');
                const statsEl = document.getElementById('pizza-stats');
                if (statsEl) statsEl.innerHTML = `<span style="color:var(--status-offline);">⚠ Couldn't fetch data</span>`;
            } else {
                const alertColors = { low: '#555', elevated: '#f59e0b', high: '#f97316', critical: '#ef4444' };
                // Use absolute avgWait values; scale relative to max in the dataset
                // Use a fixed realistic max (45 min) so bars are proportional like the reference site
                const maxWait = Math.max(...data.graph.map(p => p.avgWait), 45);
                chartEl.innerHTML = data.graph.map(p => {
                    // Closed stores (avgWait=0) → tiny stub; open stores scale to actual wait time
                    const h = p.avgWait > 0 ? Math.max((p.avgWait / maxWait) * 100, 10) : 5;
                    const c = alertColors[p.alertLevel] || '#555';
                    const isActive = p.alertLevel !== 'low' && p.avgWait > 0;
                    return `<div class="pizza-bar ${isActive ? 'active' : ''}" 
                                style="height:${h}%; background:${c}; box-shadow:${isActive ? `0 0 6px ${c}88` : 'none'};"
                                title="${p.avgWait > 0 ? p.avgWait + ' min avg wait' : 'closed'}">
                            </div>`;
                }).join('');
            }
        }

        const timeEl = document.getElementById('pizza-timestamp');
        if (timeEl && data.timestamp) timeEl.textContent = 'Updated ' + timeSince(data.timestamp) + ' ago';
    }

    document.getElementById('pizza-btn')?.addEventListener('pointerdown', fetchPizzaData);

    fetchLiveAlerts();
    setInterval(fetchLiveAlerts, 10000);

    // Settings listeners for feed control
    const pauseCheckbox = document.getElementById('pause-news-updates');
    if (pauseCheckbox) {
        pauseCheckbox.addEventListener('change', (e) => {
            appState.paused = e.target.checked;
        });
    }

    // Listen for market settings changes from ui.js
    window.addEventListener('marketSettingsChanged', () => {
       // renderMarketData(MOCK_MARKET_DATA);
    });

    // Part 3: Frontend Settings Modal Sync
    let tgChannels = [];
    async function loadTgSettings() {
        try {
            const res = await fetch('/api/alerts/settings');
            const data = await res.json();
            tgChannels = data.telegram_channels;
            renderTgList();
        } catch (e) { console.error("Failed to load settings", e); }
    }
    function renderTgList() {
        const list = document.getElementById('accounts-list');
        if (!list) return;
        list.innerHTML = tgChannels.map((ch, i) => `
            <div class="setting-item" style="display:flex; justify-content:space-between; align-items:center; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px;">
                <span>${ch}</span>
                <i class="fa-solid fa-trash" style="cursor:pointer; color:#ef4444;" onclick="removeTgChannel(${i})"></i>
            </div>`).join('');
    }
    window.removeTgChannel = async (i) => {
        tgChannels.splice(i, 1);
        renderTgList();
        await fetch('/api/alerts/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({channels: tgChannels}) });
    };
    document.getElementById('add-account-btn')?.addEventListener('click', async () => {
        const input = document.getElementById('new-account'); // Reuse the input
        const val = input.value.trim().replace('@', '');
        if (val && !tgChannels.includes(val)) {
            tgChannels.push(val);
            input.value = '';
            renderTgList();
            await fetch('/api/alerts/settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({channels: tgChannels}) });
        }
    });
    loadTgSettings(); // Call on boot

    // 1. Run this every minute to update timestamps dynamically
    setInterval(() => {
        document.querySelectorAll('.time-ago').forEach(el => {
            el.innerText = timeSince(el.getAttribute('data-time'));
        });
    }, 60000);

    // 2. Search Filter
    document.getElementById('news-search')?.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.tweet-card').forEach(card => {
            card.style.display = card.innerText.toLowerCase().includes(term) ? 'block' : 'none';
        });
    });

}


