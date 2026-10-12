

const _sfx = (() => {
    let ctx = null;
    const get = () => { if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)(); return ctx; };

    const play = (fn) => { try { fn(get()); } catch(e) {} };

    return {
        click: () => play(ctx => {
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.frequency.setValueAtTime(900, ctx.currentTime);
            g.gain.setValueAtTime(0.15, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
            o.start(); o.stop(ctx.currentTime + 0.05);
        }),
        open: () => play(ctx => {
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine';
            o.frequency.setValueAtTime(200, ctx.currentTime);
            o.frequency.linearRampToValueAtTime(400, ctx.currentTime + 0.12);
            g.gain.setValueAtTime(0.1, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
            o.start(); o.stop(ctx.currentTime + 0.15);
        }),
        close: () => play(ctx => {
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine';
            o.frequency.setValueAtTime(400, ctx.currentTime);
            o.frequency.linearRampToValueAtTime(150, ctx.currentTime + 0.1);
            g.gain.setValueAtTime(0.08, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
            o.start(); o.stop(ctx.currentTime + 0.12);
        }),
        ping: () => play(ctx => {
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine'; o.frequency.value = 1200;
            g.gain.setValueAtTime(0.08, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
            o.start(); o.stop(ctx.currentTime + 0.3);
        }),
        alarm: () => play(ctx => {
            [0, 0.18, 0.36].forEach(delay => {
                const o = ctx.createOscillator(), g = ctx.createGain();
                o.connect(g); g.connect(ctx.destination);
                o.type = 'square'; o.frequency.value = 880;
                g.gain.setValueAtTime(0, ctx.currentTime + delay);
                g.gain.linearRampToValueAtTime(0.06, ctx.currentTime + delay + 0.04);
                g.gain.linearRampToValueAtTime(0, ctx.currentTime + delay + 0.14);
                o.start(ctx.currentTime + delay);
                o.stop(ctx.currentTime + delay + 0.15);
            });
        }),
        nuke: () => play(ctx => {
            // Low rumble build + burst
            const buf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
            const data = buf.getChannelData(0);
            for (let i = 0; i < data.length; i++) {
                data[i] = (Math.random() * 2 - 1) * (i / data.length) * 0.4;
            }
            const src = ctx.createBufferSource(), g = ctx.createGain();
            const filter = ctx.createBiquadFilter();
            filter.type = 'lowpass'; filter.frequency.value = 120;
            src.buffer = buf;
            src.connect(filter); filter.connect(g); g.connect(ctx.destination);
            g.gain.setValueAtTime(0, ctx.currentTime);
            g.gain.linearRampToValueAtTime(1.0, ctx.currentTime + 0.4);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 2.0);
            src.start(); src.stop(ctx.currentTime + 2.0);

            // High crack on top
            const o = ctx.createOscillator(), og = ctx.createGain();
            o.connect(og); og.connect(ctx.destination);
            o.frequency.setValueAtTime(80, ctx.currentTime + 0.1);
            o.frequency.exponentialRampToValueAtTime(20, ctx.currentTime + 0.5);
            og.gain.setValueAtTime(0.3, ctx.currentTime + 0.1);
            og.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
            o.start(ctx.currentTime + 0.1); o.stop(ctx.currentTime + 0.6);
        }),
        news: () => play(ctx => {
            const o = ctx.createOscillator(), g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine'; o.frequency.value = 600;
            g.gain.setValueAtTime(0.05, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
            o.start(); o.stop(ctx.currentTime + 0.08);
        }),
    };
})();
window._sfx = _sfx;


export function initMap() {
    let map;
    let isMeasuring = false;
    let measurePoints = [];
    let measureLayerGroup;

    map = L.map('map', {
        zoomSnap: 0.5,
        zoomDelta: 1,
        wheelPxPerZoomLevel: 120
    }).setView([20, 0], 3);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; CartoDB',
        maxZoom: 19
    }).addTo(map);

    measureLayerGroup = L.layerGroup().addTo(map);

    // Measure Tool
    const MeasureControl = L.Control.extend({
        options: { position: 'bottomright' },
        onAdd: function() {
            const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
            const btn = L.DomUtil.create('a', 'map-tool-btn', container);
            btn.innerHTML = '<i class="fa-solid fa-ruler"></i>';
            btn.title = "Measure Distance";
            btn.href = "#";
            btn.style.width = '30px'; btn.style.height = '30px'; btn.style.display = 'flex'; btn.style.justifyContent = 'center'; btn.style.alignItems = 'center'; btn.style.textDecoration = 'none'; btn.style.color = 'black';
            
            L.DomEvent.on(btn, 'click', function(e) {
                L.DomEvent.stop(e);
                window._sfx?.click();
                isMeasuring = !isMeasuring;
                btn.classList.toggle('active', isMeasuring);
                document.getElementById('map').style.cursor = isMeasuring ? 'crosshair' : 'grab';
                if (!isMeasuring) {
                    measureLayerGroup.clearLayers();
                    measurePoints = [];
                }
            });
            return container;
        }
    });
    map.addControl(new MeasureControl());

    L.control.scale({ imperial: false }).addTo(map);

    // Coordinates HUD
    const CoordinatesControl = L.Control.extend({
        options: { position: 'bottomright' },
        onAdd: function(map) {
            const container = L.DomUtil.create('div', 'leaflet-control-coordinates');
            map.on('mousemove', e => {
                container.innerHTML = `Lat: ${e.latlng.lat.toFixed(4)}, Lng: ${e.latlng.lng.toFixed(4)}`;
            });
            return container;
        }
    });
    map.addControl(new CoordinatesControl());

    // Add Marker Control
    const AddMarkerControl = L.Control.extend({
        options: { position: 'topleft' },
        onAdd: function() {
            const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
            const btn = L.DomUtil.create('a', 'map-tool-btn', container);
            btn.innerHTML = '<i class="fa-solid fa-plus"></i>';
            btn.title = "Add Tactical Marker";
            btn.href = "#";
            btn.style.width = '30px'; btn.style.height = '30px'; btn.style.display = 'flex'; btn.style.justifyContent = 'center'; btn.style.alignItems = 'center'; btn.style.textDecoration = 'none'; btn.style.color = 'black';
            
            L.DomEvent.on(btn, 'click', function(e) {
                L.DomEvent.stop(e);
                window._sfx?.click();
                document.getElementById('marker-modal').classList.remove('hidden');
            });
            return container;
        }
    });
    map.addControl(new AddMarkerControl());

    // Marker Modal Logic
    const confirmMarkerBtn = document.getElementById('confirm-add-marker');
    const closeMarkerModalBtn = document.getElementById('close-marker-modal');
    
    if (closeMarkerModalBtn) closeMarkerModalBtn.addEventListener('click', () => document.getElementById('marker-modal').classList.add('hidden'));

    if (confirmMarkerBtn) {
        confirmMarkerBtn.addEventListener('click', () => {
            const title = document.getElementById('marker-title-input').value || "Marker";
            const color = document.getElementById('marker-color-select').value;
            const icon = document.getElementById('marker-icon-select').value;
            
            document.getElementById('marker-modal').classList.add('hidden');
            document.getElementById('map').style.cursor = 'crosshair';

            map.once('click', function(e) {
                const marker = L.marker(e.latlng, {
                    icon: L.divIcon({
                        html: `<i class="fa-solid ${icon}" style="color:${color}; font-size:16px;"></i>`,
                        className: 'custom-map-icon clear-icon',
                        iconSize: [24, 24],
                        iconAnchor: [12, 12]
                    })
                }).addTo(map);
                
                marker.bindPopup(`<b>${title}</b>`);
                marker.on('contextmenu', () => map.removeLayer(marker));
                document.getElementById('map').style.cursor = 'grab';
            });
        });
    }

    // Measurement Logic
    map.on('click', function(e) {
        if (!isMeasuring) return;
        measurePoints.push(e.latlng);
        L.circleMarker(e.latlng, { radius: 3, color: '#f59e0b' }).addTo(measureLayerGroup);

        if (measurePoints.length === 2) {
            const line = L.polyline(measurePoints, { color: '#f59e0b' }).addTo(measureLayerGroup);
            const distance = measurePoints[0].distanceTo(measurePoints[1]) / 1000;
            line.bindTooltip(`${distance.toFixed(2)} km`, { permanent: true, direction: 'center' }).openTooltip();
            
            measurePoints = [];
            isMeasuring = false;
            document.querySelector('.map-tool-btn.active')?.classList.remove('active');
            document.getElementById('map').style.cursor = 'grab';
        }
    });

    map.on('contextmenu', function() {
        measureLayerGroup.clearLayers();
        measurePoints = [];
    });

    // Region Toggles
    const regionBtns = document.querySelectorAll('.region-btn');
    regionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            regionBtns.forEach(b => b.classList.remove('active-region'));
            btn.classList.add('active-region');
            const region = btn.textContent.trim();
            if (region === 'Global') map.flyTo([20, 0], 3);
            else if (region === 'Middle East') map.flyTo([31.5, 35.0], 5);
            else if (region === 'Ukraine') map.flyTo([49.0, 31.4], 5.5);
            else if (region === 'Taiwan') map.flyTo([23.7, 121.0], 7);
        });
    });

    loadTacticalData(map);
    
    // Handle resize events from Split.js
    window.addEventListener('resize', () => map.invalidateSize());
    loadLiveIntelligence(map);
    setInterval(() => loadUkraineAlarms(map, window._alarmLayerGroup), 60000);
    return map;
}

function loadTacticalData(map) {
    const tacticalLocations = [
        { name: "Camp Lemonnier", type: "Military HQ", coords: [11.548, 43.149] },
        { name: "Al Asad Airbase", type: "Airport", coords: [33.78, 42.43] },
        { name: "Diego Garcia", type: "Airport", coords: [-7.31, 72.41] },
        { name: "King Abdullah Port", type: "Port", coords: [22.5, 39.1] },
        { name: "Ramat David Airbase", type: "Airport", coords: [32.66, 35.18] },
        { name: "Suez Canal", type: "Port", coords: [30.5, 32.3] },
        { name: "Strait of Hormuz", type: "Port", coords: [26.5, 56.5] },
        { name: "Bab el-Mandeb Strait", type: "Port", coords: [12.6, 43.4] },
        { name: "Ankara", type: "Govt", coords: [39.93, 32.85] },
        { name: "Riyadh", type: "Govt", coords: [24.71, 46.67] },
        { name: "Dimona Nuclear Research", type: "Nuclear", coords: [31.0011, 35.1456] },
        { name: "Natanz Nuclear Facility", type: "Nuclear", coords: [33.7233, 51.7272] },
        { name: "Bushehr Nuclear Plant", type: "Nuclear", coords: [28.8294, 50.8858] },
        { name: "Incirlik Air Base", type: "Airport", coords: [37.0019, 35.4258] },
        { name: "Al Udeid Air Base", type: "Airport", coords: [25.1167, 51.3150] },
        { name: "Nevatim Air Base", type: "Airport", coords: [31.2086, 35.0122] },
        { name: "Hmeimim Air Base", type: "Airport", coords: [35.4094, 35.9486] },
        { name: "King Khalid Military City", type: "Military HQ", coords: [27.9000, 45.5333] },
        { name: "Prince Sultan Air Base", type: "Airport", coords: [24.0606, 47.5692] },
        { name: "Ali Al Salem Air Base", type: "Airport", coords: [29.3467, 47.5211] },
        { name: "Isa Air Base", type: "Airport", coords: [25.9183, 50.5906] },
        { name: "Al Dhafra Air Base", type: "Airport", coords: [24.2481, 54.5478] },
        { name: "Port of Jebel Ali", type: "Port", coords: [24.9857, 55.0275] },
        { name: "Port of Bandar Abbas", type: "Port", coords: [27.1494, 56.0636] },
        { name: "Haifa Naval Base", type: "Port", coords: [32.8282, 34.9936] },
        { name: "Tartus Naval Base", type: "Port", coords: [34.9122, 35.8736] },
        { name: "IDF Headquarters (Kirya)", type: "Military HQ", coords: [32.0744, 34.7914] },
        { name: "Fifth Fleet HQ", type: "Military HQ", coords: [26.2154, 50.6078] },
        { name: "Knesset", type: "Govt", coords: [31.7767, 35.2053] },
        { name: "Pasture Palace", type: "Govt", coords: [35.7000, 51.4000] },
        { name: "Fordow Fuel Enrichment", type: "Nuclear", coords: [34.8842, 50.9958] },
        { name: "Parchin Military Complex", type: "Military HQ", coords: [35.5200, 51.7700] }
    ];

    const categoryStyles = {
        "Nuclear": { icon: "fa-radiation", color: "#ef4444" },
        "Airport": { icon: "fa-plane", color: "#3b82f6" },
        "Port": { icon: "fa-anchor", color: "#06b6d4" },
        "Military HQ": { icon: "fa-star", color: "#ef4444" },
        "Govt": { icon: "fa-building-columns", color: "#8b5cf6" }
    };
    
    tacticalLocations.forEach(loc => {
        const style = categoryStyles[loc.type] || { icon: "fa-map-pin", color: "#fff" };
        const marker = L.marker(loc.coords, {
            icon: L.divIcon({
                html: `<i class="fa-solid ${style.icon}" style="color:${style.color}; font-size:16px;"></i>`,
                className: 'custom-map-icon clear-icon',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            })
        }).addTo(map);
        marker.bindPopup(`<b>${loc.name}</b><br>${loc.type}`);
    });

    /*const legend = L.control({ position: 'bottomleft' });
    legend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = '<h4>LEGEND</h4>';
        Object.keys(categoryStyles).forEach(key => {
            const style = categoryStyles[key];
            div.innerHTML += `
                <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                    <i class="fa-solid ${style.icon}" style="color:${style.color};"></i>
                    <span>${key}</span>
                </div>
            `;
        });
        return div;
    };
    legend.addTo(map); */
}

// Layer groups exposed globally so interval can refresh them
window._alarmLayerGroup    = null;
window._basesLayerGroup    = null;
window._conflictLayerGroup = null;

function loadLiveIntelligence(map) {
    window._alarmLayerGroup    = L.layerGroup().addTo(map);
    window._basesLayerGroup    = L.layerGroup().addTo(map);
    window._conflictLayerGroup = L.layerGroup().addTo(map);

    // Progress overlay
    const overlay = document.getElementById('map-loading-overlay');
    const bar     = document.getElementById('map-loading-bar');
    const label   = document.getElementById('map-loading-label');
    const setProgress = (pct, text) => {
        if (bar) bar.style.width = pct + '%';
        if (label) label.textContent = text;
    };
    const hideOverlay = () => {
        if (overlay) { overlay.style.opacity = '0'; setTimeout(() => overlay.style.display = 'none', 500); }
    };

    setProgress(10, 'Air raid alarms...');
    loadUkraineAlarms(map, window._alarmLayerGroup).then(() => {
        setProgress(40, 'Military bases (OSM)...');
        loadOsmBases(map, window._basesLayerGroup).then(() => {
            setProgress(75, 'Conflict events (GDELT)...');
            loadConflictEvents(map, window._conflictLayerGroup).then(() => {
                setProgress(100, 'Done');
                setTimeout(hideOverlay, 600);
            });
        });
    });

    updateLegend(map);
}

// Air raid alarms (yellow pulsing dots)
async function loadUkraineAlarms(map, layerGroup) {
    layerGroup.clearLayers();
    try {
        const res = await fetch('/api/radar/alarms');
        const result = await res.json();
        if (result.status !== 'success') return;

        result.data.forEach(alert => {
            const circle = L.circleMarker(alert.coords, {
                radius: 10,
                color: '#f59e0b',
                fillColor: '#f59e0b',
                fillOpacity: 0.35,
                weight: 2,
                className: 'alarm-pulse'
            }).addTo(layerGroup);

            circle.bindPopup(`
                <b>⚠️ AIR RAID ALARM</b><br>
                <b>${alert.region}</b><br>
                Type: ${alert.type || 'Air'}<br>
                Since: ${alert.started ? new Date(alert.started).toLocaleTimeString() : 'Active'}
            `);
        });
        // if (alerts.length > 0) _sfx.alarm();
    if (result.data.length > 0) window._sfx?.alarm();
    } catch(e) { console.warn("Alarms fetch failed", e); }
}

// ── OSM military bases (orange triangle dots) ─────────────────────────────────
async function loadOsmBases(map, layerGroup) {
    layerGroup.clearLayers();
    const CACHE_KEY = 'osm_bases_v2';
    const typeIcons = {
        airfield:   { icon: 'fa-plane',                color: '#38bdf8' },
        naval_base: { icon: 'fa-anchor',               color: '#06b6d4' },
        barracks:   { icon: 'fa-person-military-rifle', color: '#f97316' },
        checkpoint: { icon: 'fa-shield-halved',        color: '#94a3b8' },
        base:       { icon: 'fa-tower-observation',    color: '#f97316' },
        range:      { icon: 'fa-bullseye',             color: '#f59e0b' },
    };
    function renderElements(elements) {
        const seen = new Set();
        elements.forEach(el => {
            const tags = el.tags || {};
            const name = tags.name || tags['name:en'] || tags.operator || 'Military Site';
            const milType = tags.military || 'base';
            const lat = el.type === 'node' ? el.lat : el.center?.lat;
            const lon = el.type === 'node' ? el.lon : el.center?.lon;
            if (!lat || !lon) return;
            const key = `${Math.round(lat*100)},${Math.round(lon*100)}`;
            if (seen.has(key)) return;
            seen.add(key);
            const style = typeIcons[milType] || typeIcons['base'];
            const marker = L.marker([lat, lon], {
                icon: L.divIcon({
                    html: `<i class="fa-solid ${style.icon}" style="color:${style.color};font-size:13px;"></i>`,
                    className: 'custom-map-icon clear-icon',
                    iconSize: [20, 20], iconAnchor: [10, 10]
                })
            }).addTo(layerGroup);
            marker.bindPopup(`<b>${name}</b><br>Type: ${milType}`);
        });
        console.log(`[OSM] Rendered ${seen.size} military sites`);
    }
    try {
        const cached = sessionStorage.getItem(CACHE_KEY);
        if (cached) { console.log('[OSM] Using cache'); renderElements(JSON.parse(cached)); return; }
    } catch(e) {}
    try {
        const query = `[out:json][timeout:25];(
          node["military"~"base|airfield|naval_base|barracks"](12.0,29.0,38.0,60.0);
          way["military"~"base|airfield|naval_base|barracks"](12.0,29.0,38.0,60.0);
          node["military"~"base|airfield|naval_base|barracks"](44.0,22.0,52.5,40.5);
          way["military"~"base|airfield|naval_base|barracks"](44.0,22.0,52.5,40.5);
          node["military"~"base|airfield|naval_base|barracks"](21.5,118.0,27.0,123.5);
          way["military"~"base|airfield|naval_base|barracks"](21.5,118.0,27.0,123.5);
        );out center 300;`;
        let elements = [];
        for (let attempt = 1; attempt <= 3; attempt++) {
            try {
                const res = await fetch('https://overpass-api.de/api/interpreter', {
                    method: 'POST', body: new URLSearchParams({ data: query })
                });
                const text = await res.text();
                if (!text.trim().startsWith('{')) {
                    console.warn(`[OSM] attempt ${attempt} got non-JSON, retrying...`);
                    await new Promise(r => setTimeout(r, 3000 * attempt));
                    continue;
                }
                elements = JSON.parse(text).elements || [];
                break;
            } catch(e) {
                console.warn(`[OSM] attempt ${attempt} failed:`, e);
                await new Promise(r => setTimeout(r, 3000 * attempt));
            }
        }
        if (elements.length > 0) {
            try { sessionStorage.setItem(CACHE_KEY, JSON.stringify(elements)); } catch(e) {}
        }
        renderElements(elements);
    } catch(e) { console.warn('[OSM] fetch failed', e); }
}

// ── ACLED conflict events (red/orange dots) ───────────────────────────────────
async function loadConflictEvents(map, layerGroup) {
    layerGroup.clearLayers();
    try {
        const res = await fetch('/api/radar/conflicts');
        const result = await res.json();
        if (result.status === 'no_key' || result.status === 'error') return;
        if (!result.data?.length) return;

        const dotColors = {
            strike:    '#ef4444',
            missile:   '#f97316',
            explosion: '#fbbf24',
        };

        result.data.forEach(ev => {
            const color = dotColors[ev.dot_type] || '#ef4444';

            // divIcon = real HTML div = CSS animations actually work
            const marker = L.marker(ev.coords, {
                icon: L.divIcon({
                    html: `<div class="event-dot-wrap">
                               <div class="event-dot-ring" style="border-color:${color}"></div>
                               <div class="event-dot-core" style="background:${color};box-shadow:0 0 6px ${color}"></div>
                           </div>`,
                    className: '',
                    iconSize:   [22, 22],
                    iconAnchor: [11, 11]
                }),
                zIndexOffset: 300
            }).addTo(layerGroup);

            marker.bindPopup(`
                <div style="min-width:180px">
                    <b>💥 ${ev.subtype}</b><br>
                    <b>${ev.name}</b>, ${ev.country}<br>
                    <span style="color:#94a3b8;font-size:11px">${ev.date} · ${ev.actor}</span><br>
                    <i style="font-size:11px;color:#cbd5e1">${ev.notes}</i>
                </div>
            `);
        });

        console.log(`[Map] Loaded ${result.data.length} conflict events`, result.data[0]);
    } catch(e) { console.warn('Conflicts fetch failed', e); }
}

// Update legend to include live layers
function updateLegend(map) {
    // Remove old legend
    if (document.querySelector('.map-legend')) return;

    const legend = L.control({ position: 'bottomleft' });
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = `
            <h4>LEGEND</h4>
            <div style="margin-bottom:6px; color:#64748b; font-size:10px; text-transform:uppercase; letter-spacing:0.5px;">Tactical</div>
            <div class="legend-row"><i class="fa-solid fa-radiation" style="color:#ef4444;"></i> Nuclear Site</div>
            <div class="legend-row"><i class="fa-solid fa-plane" style="color:#3b82f6;"></i> Air Base</div>
            <div class="legend-row"><i class="fa-solid fa-anchor" style="color:#06b6d4;"></i> Naval / Port</div>
            <div class="legend-row"><i class="fa-solid fa-star" style="color:#ef4444;"></i> Military HQ</div>
            <div class="legend-row"><i class="fa-solid fa-building-columns" style="color:#8b5cf6;"></i> Government</div>
            <div style="margin:6px 0; border-top:1px solid #2a2f3a;"></div>
            <div style="margin-bottom:4px; color:#64748b; font-size:10px; text-transform:uppercase; letter-spacing:0.5px;">Live Intel</div>
            <div class="legend-row">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f59e0b;box-shadow:0 0 6px #f59e0b;"></span>
                Air Raid Alarm
            </div>
            <div class="legend-row">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ef4444;box-shadow:0 0 6px #ef4444;"></span>
                Strike / Explosion
            </div>
            <div class="legend-row">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#f97316;box-shadow:0 0 6px #f97316;"></span>
                Missile Attack
            </div>
            <div class="legend-row"><i class="fa-solid fa-tower-observation" style="color:#f97316;"></i> OSM Military Base</div>
        `;
        return div;
    };
    legend.addTo(map);
}

window._aircraftLayer  = null;
window._maritimeLayer  = null;
window._aircraftActive = false;
window._maritimeActive = false;
window._aisSocket      = null;
window._shipPositions  = {};   // mmsi → {lat,lon,name,heading,type}

const AISSTREAM_KEY = 'xxx';

// ── Fetch aircraft from OpenSky via backend ───────────────────────────────────
async function fetchAircraft(map) {
    try {
        const b = map.getBounds();
        const url = `/api/radar/aircraft?lamin=${b.getSouth().toFixed(2)}&lomin=${b.getWest().toFixed(2)}&lamax=${b.getNorth().toFixed(2)}&lomax=${b.getEast().toFixed(2)}`;
        const res = await fetch(url);
        const result = await res.json();
        if (result.status !== 'success') return;

        window._aircraftLayer.clearLayers();

        result.data.forEach(ac => {
            const hdg = ac.heading || 0;
            const marker = L.marker([ac.lat, ac.lon], {
                icon: L.divIcon({
                    html: `<div class="aircraft-icon" style="transform:rotate(${hdg}deg)">
                               <i class="fa-solid fa-location-arrow" style="color:#38bdf8;font-size:11px;"></i>
                           </div>`,
                    className: '',
                    iconSize: [16, 16],
                    iconAnchor: [8, 8]
                }),
                zIndexOffset: 500
            }).addTo(window._aircraftLayer);

            marker.bindPopup(`
                <div style="min-width:150px;font-size:12px">
                    <b>✈️ ${ac.callsign}</b><br>
                    <span style="color:#94a3b8">${ac.country}</span><br>
                    Alt: <b>${ac.altitude.toLocaleString()} ft</b><br>
                    Speed: <b>${ac.speed} kts</b><br>
                    Heading: ${hdg}°
                </div>
            `);
        });

        console.log(`[Air] ${result.data.length} aircraft rendered`);
    } catch(e) { console.warn('[Air] fetch error', e); }
}

// AISStream WebSocket for ships
function startAISWebSocket(map, progressEl) {
    window._shipPositions = {};
    const ws = new WebSocket('wss://stream.aisstream.io/v0/stream');
    window._aisSocket = ws;
    const connTimeout = setTimeout(() => {
        if (ws.readyState !== 1) { ws.close(); progressEl?.classList.add('hidden'); }
    }, 12000);
    ws.onopen = () => {
        clearTimeout(connTimeout);
        console.log('[AIS] Connected');
        ws.send(JSON.stringify({
            Apikey: 'xxx',
            BoundingBoxes: [
                [[10.0, 20.0],  [45.0, 65.0]],
                [[-10.0, 50.0], [30.0, 80.0]],
                [[15.0, 110.0], [40.0, 135.0]],
                [[35.0, -20.0], [65.0, 15.0]],
            ],
            FilterMessageTypes: ['PositionReport', 'ShipStaticData']
        }));
    };
    let renderTimer = null;
    ws.onmessage = (event) => {
        progressEl?.classList.add('hidden');
        try {
            const msg = JSON.parse(event.data);
            const meta = msg.MetaData;
            if (!meta?.latitude || !meta?.longitude) return;
            const mmsi = String(meta.MMSI || meta.MMSI_String || '');
            if (!mmsi) return;
            if (msg.MessageType === 'PositionReport') {
                const pos = msg.Message?.PositionReport || {};
                const hdg = (pos.TrueHeading >= 0 && pos.TrueHeading < 511) ? pos.TrueHeading : (pos.Cog || 0);
                window._shipPositions[mmsi] = {
                    lat: meta.latitude, lon: meta.longitude,
                    name: meta.ShipName?.trim() || mmsi,
                    heading: hdg, speed: pos.Sog || 0,
                    type: window._shipPositions[mmsi]?.type || 'cargo',
                };
            } else if (msg.MessageType === 'ShipStaticData') {
                const sd = msg.Message?.ShipStaticData || {};
                if (window._shipPositions[mmsi]) {
                    if (sd.Name?.trim()) window._shipPositions[mmsi].name = sd.Name.trim();
                    window._shipPositions[mmsi].type = classifyShip(sd.Type || 0);
                }
            }
            if (!renderTimer) renderTimer = setTimeout(() => { renderShips(); renderTimer = null; }, 2000);
        } catch(e) {}
    };
    ws.onerror = (e) => { console.warn('[AIS] error', e); progressEl?.classList.add('hidden'); };
    ws.onclose = (e) => { console.log(`[AIS] closed code=${e.code}`); window._aisSocket = null; };
}

function renderShips() {
    if (!window._maritimeActive) return;
    window._maritimeLayer.clearLayers();

    const SHIP_COLORS = {
        tanker:    '#f97316',
        cargo:     '#38bdf8',
        military:  '#ef4444',
        passenger: '#a78bfa',
        tug:       '#fbbf24',
        other:     '#94a3b8',
    };

    Object.values(window._shipPositions).forEach(ship => {
        const color = SHIP_COLORS[ship.type] || SHIP_COLORS.other;
        const hdg   = ship.heading > 360 ? 0 : ship.heading;

        const marker = L.marker([ship.lat, ship.lon], {
            icon: L.divIcon({
                html: `<div class="ship-icon" style="transform:rotate(${hdg}deg)">
                           <i class="fa-solid fa-location-arrow" style="color:${color};font-size:10px;"></i>
                       </div>`,
                className: '',
                iconSize: [14, 14],
                iconAnchor: [7, 7]
            }),
            zIndexOffset: 400
        }).addTo(window._maritimeLayer);

        marker.bindPopup(`
            <div style="min-width:140px;font-size:12px">
                <b>🚢 ${ship.name}</b><br>
                <span style="color:#94a3b8;text-transform:capitalize">${ship.type}</span><br>
                Speed: <b>${ship.speed.toFixed(1)} kts</b><br>
                Heading: ${hdg}°
            </div>
        `);
    });

    console.log(`[Ships] Rendered ${Object.keys(window._shipPositions).length} vessels`);
}

function classifyShip(typeCode) {
    if (typeCode >= 80 && typeCode <= 89) return 'tanker';
    if (typeCode >= 70 && typeCode <= 79) return 'cargo';
    if (typeCode >= 60 && typeCode <= 69) return 'passenger';
    if (typeCode >= 30 && typeCode <= 32) return 'tug';
    if (typeCode === 35) return 'military';
    return 'other';
}

export function initTrafficLayers(map) {
    window._aircraftLayer = L.layerGroup();
    window._maritimeLayer = L.layerGroup();

    // ── Air traffic button ────────────────────────────────────────
    const airBtn  = document.getElementById('air-traffic-btn');
    const airProg = document.getElementById('air-progress');

    airBtn?.addEventListener('pointerdown', async () => {
        window._sfx?.click();
        _sfx.click();
        if (window._aircraftActive) {
            // Toggle OFF
            window._aircraftActive = false;
            airBtn.classList.remove('active');
            window._aircraftLayer.clearLayers();
            map.removeLayer(window._aircraftLayer);
            return;
        }
        // Toggle ON
        window._aircraftActive = true;
        airBtn.classList.add('active');
        airProg?.classList.remove('hidden');

        map.addLayer(window._aircraftLayer);
        await fetchAircraft(map);

        airProg?.classList.add('hidden');

        // Refresh every 30s while active
        window._aircraftInterval = setInterval(async () => {
            if (!window._aircraftActive) { clearInterval(window._aircraftInterval); return; }
            await fetchAircraft(map);
        }, 30000);
    });

    // Maritime button
    const shipBtn  = document.getElementById('maritime-btn');
    const shipProg = document.getElementById('maritime-progress');

    shipBtn?.addEventListener('pointerdown', () => {
        window._sfx?.click();
        _sfx.click();
        if (window._maritimeActive) {
            // Toggle OFF
            window._maritimeActive = false;
            shipBtn.classList.remove('active');
            window._maritimeLayer.clearLayers();
            map.removeLayer(window._maritimeLayer);
            if (window._aisSocket) {
                window._aisSocket.close();
                window._aisSocket = null;
            }
            return;
        }
        // Toggle ON
        window._maritimeActive = true;
        shipBtn.classList.add('active');
        shipProg?.classList.remove('hidden');
        map.addLayer(window._maritimeLayer);
        startAISWebSocket(map, shipProg);
    });
}


const NUKE_ZONES = [
    { label: 'Fireball',         pct: 1.00, color: '#ffffff', fillColor: '#ff4400', opacity: 0.9 },
    { label: 'Heavy Blast 20psi',pct: 0.75, color: '#ff6600', fillColor: '#ff6600', opacity: 0.6 },
    { label: 'Moderate 5psi',    pct: 0.60, color: '#ffaa00', fillColor: '#ffaa00', opacity: 0.4 },
    { label: 'Thermal Burns',    pct: 0.45, color: '#ffdd00', fillColor: '#ffdd00', opacity: 0.25 },
    { label: 'Light Blast 1psi', pct: 0.30, color: '#3b82f6', fillColor: '#3b82f6', opacity: 0.12 },
];

// Glasstone & Dolan cube-root scaling (km)
function nukeRadius(kt) {
    const cbrt = Math.pow(kt, 1/3);
    return {
        fireball: 0.07  * cbrt,
        heavy:    0.28  * cbrt,
        moderate: 0.65  * cbrt,
        thermal:  1.40  * cbrt,
        light:    2.20  * cbrt,
    };
}

window._nukeLayerGroup  = null;
window._nukeActive      = false;
window._nukeDetonations = [];

export function initNukeSimulator(map) {
    window._nukeLayerGroup = L.layerGroup().addTo(map);

    const btn       = document.getElementById('nuke-btn');
    const panel     = document.getElementById('nuke-panel');
    const closeBtn  = document.getElementById('nuke-panel-close');
    const clearBtn  = document.getElementById('nuke-clear-btn');

    btn?.addEventListener('pointerdown', () => {
        _sfx.click();
        const isOpen = !panel.classList.contains('hidden');
        panel.classList.toggle('hidden', isOpen);
        btn.classList.toggle('active', !isOpen);
        window._nukeActive = !isOpen;
        map.getContainer().style.cursor = !isOpen ? 'crosshair' : '';
    });

    closeBtn?.addEventListener('pointerdown', () => {
        panel.classList.add('hidden');
        btn.classList.remove('active');
        window._nukeActive = false;
        map.getContainer().style.cursor = '';
    });

    clearBtn?.addEventListener('pointerdown', () => {
        window._nukeLayerGroup.clearLayers();
        window._nukeDetonations = [];
        document.getElementById('nuke-stats').style.display = 'none';
    });

    // Legend toggle
    document.getElementById('legend-btn')?.addEventListener('pointerdown', () => {
        window._sfx?.click();
        const legendEl = document.querySelector('.map-legend');
        const btn = document.getElementById('legend-btn');
        if (!legendEl) return;
        const isVisible = legendEl.style.display !== 'none';
        legendEl.style.display = isVisible ? 'none' : '';
        btn.classList.toggle('active', !isVisible);
    });

    map.on('click', (e) => {
        if (!window._nukeActive) return;
        const kt = parseFloat(document.getElementById('nuke-weapon-select').value);
        const weaponName = document.getElementById('nuke-weapon-select').selectedOptions[0].text;
        _sfx.nuke();
        detonateNuke(map, e.latlng, kt, weaponName);
    });
}

function detonateNuke(map, latlng, kt, name) {
    const radii = nukeRadius(kt);
    const zones = [
        { r: radii.light,    color: '#3b82f6', fill: '#3b82f6', fo: 0.12, label: 'Light Blast (1 psi)' },
        { r: radii.thermal,  color: '#facc15', fill: '#facc15', fo: 0.20, label: 'Thermal Radiation' },
        { r: radii.moderate, color: '#f97316', fill: '#f97316', fo: 0.30, label: 'Moderate Blast (5 psi)' },
        { r: radii.heavy,    color: '#ef4444', fill: '#ef4444', fo: 0.45, label: 'Heavy Blast (20 psi)' },
        { r: radii.fireball, color: '#ffffff', fill: '#ff4400', fo: 0.85, label: 'Fireball' },
    ];

    zones.forEach((z, i) => {
        setTimeout(() => {
            const circle = L.circle(latlng, {
                radius:      z.r * 1000, // km → m
                color:       z.color,
                fillColor:   z.fill,
                fillOpacity: 0,
                weight:      1.5,
                opacity:     0,
                className:   'nuke-ring'
            }).addTo(window._nukeLayerGroup);

            circle.bindPopup(`
                <div style="font-size:12px;min-width:160px">
                    <b>☢ ${name}</b><br>
                    <span style="color:#ef4444">${z.label}</span><br>
                    Radius: <b>${z.r.toFixed(1)} km</b>
                </div>
            `);

            // Animate expand
            let opacity = 0;
            let fillOpacity = 0;
            const targetFill = z.fo;
            const steps = 20;
            const interval = setInterval(() => {
                opacity     = Math.min(1,   opacity     + 1/steps);
                fillOpacity = Math.min(targetFill, fillOpacity + targetFill/steps);
                circle.setStyle({ opacity, fillOpacity });
                if (opacity >= 1) clearInterval(interval);
            }, 30);

        }, i * 80);
    });

    // Flash marker at ground zero
    const flash = L.circleMarker(latlng, {
        radius: 6, color: '#fff', fillColor: '#fff',
        fillOpacity: 1, weight: 2
    }).addTo(window._nukeLayerGroup);
    flash.bindPopup(`<b>☢ Ground Zero</b><br>${name}<br>${kt >= 1000 ? (kt/1000).toFixed(1)+' Mt' : kt+' kt'}`);

    window._nukeDetonations.push({ latlng, kt, name });

    // Update stats
    const stats = document.getElementById('nuke-stats');
    const statsText = document.getElementById('nuke-stats-text');
    stats.style.display = 'block';
    const totalKt = window._nukeDetonations.reduce((s, d) => s + d.kt, 0);
    statsText.innerHTML = `
        Detonations: <b>${window._nukeDetonations.length}</b><br>
        Total yield: <b>${totalKt >= 1000 ? (totalKt/1000).toFixed(1)+' Mt' : totalKt+' kt'}</b><br>
        Light blast: <b>${(nukeRadius(kt).light).toFixed(1)} km</b>
    `;
}


//  CYBER INTEL 
export function initCyberPanel(map) {
    const btn   = document.getElementById('cyber-btn');
    const panel = document.getElementById('cyber-panel');
    const close = document.getElementById('cyber-panel-close');

    // Draggable
    const header = panel?.querySelector('.modal-header');
    if (header) {
        let dragging = false, ox = 0, oy = 0;
        header.addEventListener('pointerdown', e => {
            dragging = true; ox = e.clientX - panel.offsetLeft; oy = e.clientY - panel.offsetTop;
            header.setPointerCapture(e.pointerId);
        });
        header.addEventListener('pointermove', e => {
            if (!dragging) return;
            panel.style.left = (e.clientX - ox) + 'px';
            panel.style.top  = (e.clientY - oy) + 'px';
        });
        header.addEventListener('pointerup', () => dragging = false);
    }

    // Map layer for cyber dots
    window._cyberLayer = L.layerGroup().addTo(map);
    window._cyberVisible = false;

    btn?.addEventListener('pointerdown', () => {
        const isOpen = !panel.classList.contains('hidden');
        isOpen ? _sfx.close() : _sfx.open();
        panel.classList.toggle('hidden', isOpen);
        btn.classList.toggle('active', !isOpen);
        if (!isOpen) loadCyberFeed('all');
    });

    close?.addEventListener('pointerdown', () => {
        panel.classList.add('hidden');
        btn.classList.remove('active');
    });

    document.querySelectorAll('.cyber-filter-btn').forEach(b => {
        b.addEventListener('pointerdown', () => {
            document.querySelectorAll('.cyber-filter-btn').forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            loadCyberFeed(b.dataset.type);
        });
    });
}

// Country name = approximate coords for cyber dot placement
const COUNTRY_COORDS = {
    'Microsoft': [47.6, -122.3], 'Apple': [37.3, -122.0], 'Google': [37.4, -122.1],
    'Apache': [37.4, -122.1], 'Cisco': [37.4, -121.9], 'VMware': [37.4, -122.1],
    'Fortinet': [37.5, -122.0], 'Ivanti': [40.7, -111.9], 'Palo Alto': [37.4, -122.1],
    'SolarWinds': [30.3, -97.7], 'Citrix': [26.1, -80.1], 'F5': [47.6, -122.3],
    'Oracle': [37.5, -122.2], 'SAP': [49.3, 8.6], 'MOVEit': [42.4, -71.1],
};
// Fallback scatter so dots don't all pile up
function cyberCoords(vendor, index) {
    for (const [k, c] of Object.entries(COUNTRY_COORDS)) {
        if (vendor.includes(k)) return [c[0] + (Math.random()-0.5)*2, c[1] + (Math.random()-0.5)*2];
    }
    // Scatter around tech hubs
    const hubs = [[37.4,-122.1],[47.6,-122.3],[40.7,-74.0],[51.5,-0.1],[35.7,139.7],[48.9,2.3],[1.3,103.8]];
    const h = hubs[index % hubs.length];
    return [h[0] + (Math.random()-0.5)*5, h[1] + (Math.random()-0.5)*5];
}

let _cyberCache = null;
async function loadCyberFeed(filter = 'all') {
    const feed = document.getElementById('cyber-feed');
    if (!feed) return;
    feed.innerHTML = '<div style="color:#64748b;padding:8px 0;">Loading...</div>';
    try {
        if (!_cyberCache) {
            const res = await fetch('/api/radar/cyber');
            const result = await res.json();
            _cyberCache = result.data || [];
            renderCyberDots(_cyberCache);
        }
        const items = filter === 'all' ? _cyberCache : _cyberCache.filter(e => e.type === filter);
        if (!items.length) { feed.innerHTML = '<div style="color:#64748b;padding:8px 0;">No events</div>'; return; }

        const TYPE_COLORS = { exploit: '#ef4444', ddos: '#f97316', malware: '#a78bfa', breach: '#06b6d4' };
        feed.innerHTML = items.map(e => `
            <a href="${e.url}" target="_blank" style="display:block;padding:7px 0;border-bottom:1px solid #1a1e29;text-decoration:none;color:inherit;">
                <div style="display:flex;align-items:center;gap:5px;margin-bottom:2px;">
                    <span style="background:${TYPE_COLORS[e.type]||'#64748b'};color:#000;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;text-transform:uppercase;">${e.type}</span>
                    <span style="color:#94a3b8;font-size:10px;">${e.id}</span>
                    <span style="color:#64748b;font-size:9px;margin-left:auto;">${e.date}</span>
                </div>
                <div style="color:#e2e8f0;font-size:11px;font-weight:600;">${e.title}</div>
                <div style="color:#64748b;font-size:10px;">${e.vendor} · ${e.product}</div>
            </a>
        `).join('');
    } catch(e) {
        feed.innerHTML = '<div style="color:#ef4444;padding:8px 0;">Failed to load</div>';
    }
}

function renderCyberDots(events) {
    if (!window._cyberLayer) return;
    window._cyberLayer.clearLayers();
    events.forEach((ev, i) => {
        const [lat, lon] = cyberCoords(ev.vendor || '', i);
        const marker = L.marker([lat, lon], {
            icon: L.divIcon({
                html: `<div class="event-dot-wrap">
                    <div class="event-dot-ring" style="border-color:#06b6d4"></div>
                    <div class="event-dot-core" style="background:#06b6d4;box-shadow:0 0 6px #06b6d4"></div>
                </div>`,
                className: '', iconSize: [22,22], iconAnchor: [11,11]
            }),
            zIndexOffset: 200
        }).addTo(window._cyberLayer);
        marker.bindPopup(`
            <div style="min-width:160px;font-size:12px">
                <b>🛡 ${ev.title}</b><br>
                <span style="color:#06b6d4">${ev.id}</span><br>
                ${ev.vendor} · ${ev.product}<br>
                <span style="color:#64748b;font-size:10px">${ev.date}</span>
            </div>
        `);
    });
}


//  THREAT LEVEL METER
export function initThreatMeter() {
    const DEFCON_LEVELS = [
        { level:1, label:'NUCLEAR WAR', color:'#ef4444', pct:100 },
        { level:2, label:'ARMED ATTACK', color:'#f97316', pct:80 },
        { level:3, label:'ELEVATED',    color:'#f59e0b', pct:60 },
        { level:4, label:'INCREASED',   color:'#eab308', pct:40 },
        { level:5, label:'PEACE',       color:'#10b981', pct:20 },
    ];

    function updateMeter() {
        const alarms   = window._alarmLayerGroup?._layers  ? Object.keys(window._alarmLayerGroup._layers).length  : 0;
        const conflicts= window._conflictLayerGroup?._layers? Object.keys(window._conflictLayerGroup._layers).length: 0;
        const vixEl    = document.querySelector('[data-symbol="VIX"] .change') ;

        // Score: alarms heavy, conflicts medium
        let score = Math.min(100, (alarms * 4) + (conflicts * 0.08));

        const idx   = score > 80 ? 0 : score > 60 ? 1 : score > 40 ? 2 : score > 20 ? 3 : 4;
        const def   = DEFCON_LEVELS[idx];

        const lvlEl  = document.getElementById('defcon-level');
        const lblEl  = document.getElementById('defcon-label');
        const fillEl = document.getElementById('defcon-fill');
        const meterEl= document.getElementById('threat-meter');

        if (lvlEl)  { lvlEl.textContent  = def.level; lvlEl.style.color  = def.color; }
        if (lblEl)  { lblEl.textContent  = def.label; lblEl.style.color  = def.color; }
        if (fillEl) { fillEl.style.width = def.pct + '%'; fillEl.style.background = def.color; }
        if (meterEl){ meterEl.style.borderColor = def.color + '88'; }
    }

    // Update after layers load + every 60s
    setTimeout(updateMeter, 5000);
    setInterval(updateMeter, 60000);
}


//  BODY COUNT TICKER
export function initBodyCount() {
    // Inject widget into map overlay area
    const container = document.getElementById('map');
    if (!container) return;
    const el = document.createElement('div');
    el.id = 'body-count-widget';
    el.style.cssText = `
        position:absolute;top:10px;right:10px;z-index:450;
        background:rgba(10,0,0,0.85);border:1px solid #7f1d1d;
        border-radius:6px;padding:8px 12px;font-family:monospace;
        font-size:11px;min-width:160px;pointer-events:none;
        box-shadow:0 0 12px rgba(239,68,68,0.2);
    `;
    el.innerHTML = `
        <div style="color:#ef4444;font-weight:700;letter-spacing:2px;font-size:10px;margin-bottom:4px;">☠ CONFLICT TRACKER</div>
        <div style="display:flex;justify-content:space-between;gap:16px;">
            <div><div style="color:#64748b;font-size:9px;">KIA</div><div id="bc-killed" style="color:#ef4444;font-size:16px;font-weight:900;">—</div></div>
            <div><div style="color:#64748b;font-size:9px;">WIA</div><div id="bc-wounded" style="color:#f97316;font-size:16px;font-weight:900;">—</div></div>
            <div><div style="color:#64748b;font-size:9px;">EVENTS</div><div id="bc-events" style="color:#fbbf24;font-size:16px;font-weight:900;">—</div></div>
        </div>
        <div id="bc-date" style="color:#2a2f3a;font-size:9px;margin-top:4px;text-align:right;">GDELT 24h</div>
    `;
    container.style.position = 'relative';
    container.appendChild(el);

    async function updateBodyCount() {
        try {
            const res = await fetch('/api/radar/conflicts');
            const result = await res.json();
            if (!result.data?.length) return;
            const killed  = result.data.reduce((s, e) => s + (e.killed  || 0), 0);
            const wounded = result.data.reduce((s, e) => s + (e.wounded || 0), 0);
            const events  = result.data.length;
            document.getElementById('bc-killed') .textContent = killed  > 0 ? killed.toLocaleString()  : 'N/A';
            document.getElementById('bc-wounded').textContent = wounded > 0 ? wounded.toLocaleString() : 'N/A';
            document.getElementById('bc-events') .textContent = events.toLocaleString();
            document.getElementById('bc-date')   .textContent = result.data[0]?.date || 'GDELT 24h';
        } catch(e) {}
    }
    setTimeout(updateBodyCount, 6000);
    setInterval(updateBodyCount, 300000); // refresh every 5min
}


//  RADIO INTERCEPT WIDGET
const RADIO_TRANSCRIPTS = {
    centcom: [
        "ALPHA TWO this is EAGLE SIX, sector clear, over.",
        "Confirm grid 38S MB 123 456, unknown vehicle spotted.",
        "FLASH FLASH FLASH — air asset inbound from bearing 270.",
        "All stations CENTCOM net, comms check, over.",
        "Drone feed shows two pax, light infantry, moving north.",
    ],
    nato: [
        "BRAVO element, hold position at checkpoint KILO.",
        "Artillery assets standing by, awaiting fire mission.",
        "QRF is 15 mikes out from your position.",
        "Intel reports armored column 20 klicks east.",
        "All NATO callsigns authenticate WHISKEY TANGO.",
    ],
    pacific: [
        "SEVENTH FLEET, TAIWAN CTRL, multiple contacts bearing 090.",
        "P-8 on station, tracking surface group, speed 18 knots.",
        "DEFCON status remains at 3, all units maintain readiness.",
        "Carrier strike group 60 miles west of the strait.",
        "Radar contact lost... reacquiring... now showing 12 contacts.",
    ],
    kiev: [
        "Повітряна тривога! Ракетна атака з півночі.",
        "KYIV CTRL, all birds scramble, repeat, all birds scramble.",
        "Artillery fire mission, target grid confirmed.",
        "Drone swarm detected, heading 180, 40 klicks out.",
        "Armored column destroyed, sector 7 clear.",
    ],
    norad: [
        "SANTA TRACK active... just kidding. Or are we.",
        "Ballistic trajectory confirmed — computing intercept.",
        "ICBM launch detected, origin unknown, time to impact 28 min.",
        "Cheyenne Mountain NORAD, all stations authenticate FOXTROT.",
        "Space track update: object 2025-001A decaying orbit.",
    ],
};

let _radioCtx = null, _radioNodes = [], _radioRunning = false, _radioRafId = null;

export function initRadio() {
    const radioBtn  = document.getElementById('radio-btn');
    const widget    = document.getElementById('radio-widget');
    const closeBtn  = document.getElementById('radio-close');
    const playBtn   = document.getElementById('radio-play-btn');
    const canvas    = document.getElementById('radio-canvas');
    const statusEl  = document.getElementById('radio-status');
    const transcriptEl = document.getElementById('radio-transcript');

    // Toggle widget visibility
    radioBtn?.addEventListener('click', () => {
        const open = widget.classList.toggle('hidden');
        widget.classList.toggle('hidden', !widget.classList.contains('hidden') ? false : true);
        // simpler:
        if (widget.style.display === 'none' || widget.classList.contains('hidden')) {
            widget.classList.remove('hidden');
            widget.style.display = '';
            radioBtn.style.display = 'none';
        }
    });
    // Actually simplest approach:
    radioBtn?.addEventListener('pointerdown', () => {
        widget.classList.remove('hidden');
        radioBtn.style.opacity = '0';
        radioBtn.style.pointerEvents = 'none';
        _sfx?.open();
    });
    closeBtn?.addEventListener('pointerdown', () => {
        widget.classList.add('hidden');
        radioBtn.style.opacity = '1';
        radioBtn.style.pointerEvents = '';
        stopRadio();
        _sfx?.close();
    });

    // Draggable
    const header = widget.querySelector('.modal-header');
    if (header) {
        let drag = false, ox = 0, oy = 0;
        header.addEventListener('pointerdown', e => {
            drag = true; ox = e.clientX - widget.offsetLeft; oy = e.clientY - widget.offsetTop;
            header.setPointerCapture(e.pointerId);
        });
        header.addEventListener('pointermove', e => {
            if (!drag) return;
            widget.style.left   = (e.clientX - ox) + 'px';
            widget.style.top    = (e.clientY - oy) + 'px';
            widget.style.bottom = 'auto';
            widget.style.right  = 'auto';
        });
        header.addEventListener('pointerup', () => drag = false);
    }

    playBtn?.addEventListener('pointerdown', () => {
        if (_radioRunning) { stopRadio(); playBtn.textContent = '▶ TUNE'; statusEl.textContent = 'STANDBY...'; }
        else               { startRadio(canvas, statusEl, transcriptEl); playBtn.textContent = '■ SQUELCH'; }
        _sfx?.click();
    });
}

function startRadio(canvas, statusEl, transcriptEl) {
    _radioRunning = true;
    _radioCtx = new (window.AudioContext || window.webkitAudioContext)();

    // White noise source
    const bufSize = _radioCtx.sampleRate * 2;
    const buf = _radioCtx.createBuffer(1, bufSize, _radioCtx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1;

    const noise = _radioCtx.createBufferSource();
    noise.buffer = buf; noise.loop = true;

    // Bandpass filter — gives it that radio mid-range sound
    const bp = _radioCtx.createBiquadFilter();
    bp.type = 'bandpass'; bp.frequency.value = 1800; bp.Q.value = 0.8;

    // Gain with random squelch breaks
    const gainNode = _radioCtx.createGain();
    gainNode.gain.value = 0.08;

    noise.connect(bp); bp.connect(gainNode); gainNode.connect(_radioCtx.destination);
    noise.start();
    _radioNodes = [noise, gainNode];

    // Analyser for waveform canvas
    const analyser = _radioCtx.createAnalyser();
    analyser.fftSize = 256;
    gainNode.connect(analyser);
    const freqData = new Uint8Array(analyser.frequencyBinCount);
    const ctx2d = canvas.getContext('2d');

    function drawWave() {
        if (!_radioRunning) return;
        analyser.getByteFrequencyData(freqData);
        ctx2d.clearRect(0, 0, canvas.width, canvas.height);
        ctx2d.strokeStyle = '#22c55e';
        ctx2d.lineWidth = 1;
        ctx2d.beginPath();
        const step = canvas.width / freqData.length;
        for (let i = 0; i < freqData.length; i++) {
            const y = canvas.height - (freqData[i] / 255) * canvas.height;
            i === 0 ? ctx2d.moveTo(0, y) : ctx2d.lineTo(i * step, y);
        }
        ctx2d.stroke();
        _radioRafId = requestAnimationFrame(drawWave);
    }
    drawWave();

    // Random squelch + transcript
    const station = document.getElementById('radio-station')?.value || 'centcom';
    const lines = RADIO_TRANSCRIPTS[station] || RADIO_TRANSCRIPTS.centcom;
    let lineIdx = 0;

    function squelchCycle() {
        if (!_radioRunning) return;
        const onTime  = 1500 + Math.random() * 3000;
        const offTime = 500  + Math.random() * 2000;
        statusEl.textContent = '● RECEIVING...';
        statusEl.style.color = '#22c55e';
        gainNode.gain.setTargetAtTime(0.1, _radioCtx.currentTime, 0.05);

        // Show transcript line
        transcriptEl.textContent = lines[lineIdx % lines.length];
        lineIdx++;

        setTimeout(() => {
            if (!_radioRunning) return;
            statusEl.textContent = '— SQUELCH';
            statusEl.style.color = '#166534';
            gainNode.gain.setTargetAtTime(0.015, _radioCtx.currentTime, 0.05);
            transcriptEl.textContent = '';
            setTimeout(squelchCycle, offTime);
        }, onTime);
    }
    setTimeout(squelchCycle, 500);
}

function stopRadio() {
    _radioRunning = false;
    if (_radioRafId) cancelAnimationFrame(_radioRafId);
    _radioNodes.forEach(n => { try { n.stop?.(); n.disconnect?.(); } catch(e){} });
    if (_radioCtx) { _radioCtx.close(); _radioCtx = null; }
    _radioNodes = [];
}

