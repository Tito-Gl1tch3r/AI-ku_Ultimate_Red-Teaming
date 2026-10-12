#!/usr/bin/env python3
"""
Blood-Web Monitoring Dashboard
Real-time web interface for honeypot monitoring.
"""

import http.server
import socketserver
import json
import os
import threading
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

DARK_THEME = """
<!DOCTYPE html>
<html>
<head>
    <title>Blood-Web Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            min-height: 100vh;
            font-size: 13px;
        }

        /* ── Toolbar ─────────────────────────────────────────── */
        .toolbar {
            background: #2d2d2d;
            border-bottom: 1px solid #3c3c3c;
            padding: 6px 16px;
            display: flex;
            align-items: center;
            gap: 16px;
            user-select: none;
        }
        .toolbar-brand {
            font-weight: 600;
            font-size: 14px;
            color: #e74c3c;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        .toolbar-sep {
            width: 1px;
            height: 20px;
            background: #3c3c3c;
        }
        .toolbar-stat {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #999;
        }
        .toolbar-stat .val {
            color: #e0e0e0;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
        }
        .toolbar-stat.critical .val { color: #e74c3c; }
        .toolbar-stat.high .val { color: #e67e22; }
        .toolbar-stat.medium .val { color: #f1c40f; }
        .toolbar-stat.low .val { color: #27ae60; }
        .toolbar-right {
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            color: #27ae60;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .live-dot {
            width: 7px;
            height: 7px;
            background: #27ae60;
            border-radius: 50%;
            animation: pulse 1.5s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        .refresh-btn {
            background: #3c3c3c;
            border: 1px solid #4c4c4c;
            color: #d4d4d4;
            padding: 4px 12px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            font-family: inherit;
            transition: background 0.15s;
        }
        .refresh-btn:hover { background: #4c4c4c; }

        /* ── Main layout ─────────────────────────────────────── */
        .main {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 37px);
        }

        /* ── Packet list (attack table) ──────────────────────── */
        .packet-pane {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }
        .packet-pane-header {
            background: #2d2d2d;
            border-bottom: 1px solid #3c3c3c;
            padding: 4px 12px;
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            justify-content: space-between;
        }
        .packet-table {
            flex: 1;
            overflow-y: auto;
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', 'Courier New', monospace;
            font-size: 12px;
        }
        .packet-table::-webkit-scrollbar { width: 8px; }
        .packet-table::-webkit-scrollbar-track { background: #1e1e1e; }
        .packet-table::-webkit-scrollbar-thumb { background: #3c3c3c; border-radius: 4px; }
        .packet-table::-webkit-scrollbar-thumb:hover { background: #4c4c4c; }

        .pkt-header {
            display: grid;
            grid-template-columns: 70px 130px 110px 80px 1fr 90px;
            background: #252526;
            border-bottom: 1px solid #3c3c3c;
            position: sticky;
            top: 0;
            z-index: 1;
        }
        .pkt-header span {
            padding: 5px 10px;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.3px;
            border-right: 1px solid #333;
            user-select: none;
        }
        .pkt-header span:last-child { border-right: none; }

        .pkt-row {
            display: grid;
            grid-template-columns: 70px 130px 110px 80px 1fr 90px;
            border-bottom: 1px solid #2a2a2a;
            cursor: default;
            transition: background 0.1s;
        }
        .pkt-row:hover { background: #2a2d2e; }
        .pkt-row.selected { background: #264f78; }
        .pkt-row span {
            padding: 4px 10px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            border-right: 1px solid #2a2a2a;
            line-height: 22px;
        }
        .pkt-row span:last-child { border-right: none; }
        .pkt-no { color: #666; }
        .pkt-time { color: #888; }
        .pkt-src { color: #d4d4d4; }
        .pkt-svc { color: #569cd6; }
        .pkt-tech { color: #d4d4d4; }
        .pkt-sev {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.3px;
        }
        .sev-critical { color: #e74c3c; }
        .sev-high { color: #e67e22; }
        .sev-medium { color: #f1c40f; }
        .sev-low { color: #27ae60; }

        .pkt-row-odd { background: #1e1e1e; }
        .pkt-row-even { background: #222222; }

        /* ── Bottom pane (details + stats) ───────────────────── */
        .bottom-pane {
            height: 200px;
            min-height: 150px;
            border-top: 3px solid #3c3c3c;
            display: grid;
            grid-template-columns: 1fr 300px;
            background: #1e1e1e;
        }

        /* Detail pane */
        .detail-pane {
            border-right: 1px solid #3c3c3c;
            overflow-y: auto;
        }
        .detail-header {
            background: #2d2d2d;
            border-bottom: 1px solid #3c3c3c;
            padding: 4px 12px;
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .detail-content {
            padding: 8px 12px;
            font-family: 'SF Mono', 'Consolas', monospace;
            font-size: 12px;
            line-height: 1.6;
        }
        .detail-content .field {
            display: flex;
            gap: 8px;
        }
        .detail-content .field-label {
            color: #569cd6;
            min-width: 140px;
        }
        .detail-content .field-value {
            color: #d4d4d4;
        }

        /* Stats pane */
        .stats-pane {
            overflow-y: auto;
        }
        .stats-header {
            background: #2d2d2d;
            border-bottom: 1px solid #3c3c3c;
            padding: 4px 12px;
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stats-content { padding: 8px 12px; }
        .svc-row {
            display: flex;
            justify-content: space-between;
            padding: 3px 0;
            font-size: 12px;
        }
        .svc-row .svc-name { color: #d4d4d4; }
        .svc-row .svc-count { color: #e74c3c; font-weight: 600; font-variant-numeric: tabular-nums; }
        .svc-bar {
            height: 3px;
            background: #333;
            border-radius: 2px;
            margin-top: 2px;
            overflow: hidden;
        }
        .svc-bar-fill {
            height: 100%;
            background: #e74c3c;
            border-radius: 2px;
            transition: width 0.3s;
        }
        .ip-row {
            display: flex;
            justify-content: space-between;
            padding: 3px 0;
            font-size: 12px;
            font-family: 'SF Mono', 'Consolas', monospace;
        }
        .ip-row .ip-addr { color: #d4d4d4; }
        .ip-row .ip-count { color: #e74c3c; font-weight: 600; }

        /* ── Empty state ─────────────────────────────────────── */
        .empty-state {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #555;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <!-- Toolbar -->
    <div class="toolbar">
        <span class="toolbar-brand">BLOOD-WEB</span>
        <div class="toolbar-sep"></div>
        <div class="toolbar-stat">Total <span class="val" id="total-attacks">0</span></div>
        <div class="toolbar-sep"></div>
        <div class="toolbar-stat critical">Critical <span class="val" id="critical-count">0</span></div>
        <div class="toolbar-stat high">High <span class="val" id="high-count">0</span></div>
        <div class="toolbar-stat medium">Medium <span class="val" id="medium-count">0</span></div>
        <div class="toolbar-stat low">Low <span class="val" id="low-count">0</span></div>
        <div class="toolbar-right">
            <span class="live-badge"><span class="live-dot"></span>CAPTURING</span>
            <button class="refresh-btn" onclick="fetchData()">Refresh</button>
        </div>
    </div>

    <div class="main">
        <!-- Attack table -->
        <div class="packet-pane">
            <div class="packet-pane-header">
                <span>Attack events</span>
                <span id="feed-count">0 events</span>
            </div>
            <div class="packet-table" id="attack-feed">
                <div class="pkt-header">
                    <span>No.</span>
                    <span>Time</span>
                    <span>Source</span>
                    <span>Service</span>
                    <span>Technique</span>
                    <span>Severity</span>
                </div>
                <div class="empty-state" id="empty-state">Waiting for connections...</div>
            </div>
        </div>

        <!-- Bottom pane -->
        <div class="bottom-pane">
            <div class="detail-pane">
                <div class="detail-header">Packet Details</div>
                <div class="detail-content" id="detail-content">
                    <div class="empty-state">Select an event to view details</div>
                </div>
            </div>
            <div class="stats-pane">
                <div class="stats-header">Statistics</div>
                <div class="stats-content">
                    <div style="margin-bottom: 10px;">
                        <div style="color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 4px;">By Service</div>
                        <div id="service-stats"></div>
                    </div>
                    <div>
                        <div style="color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 4px;">Top Sources</div>
                        <div id="top-ips"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let allAttacks = [];
        let selectedIdx = -1;

        async function fetchData() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                updateDashboard(data);
            } catch (e) {}
        }

        function updateDashboard(data) {
            if (!data || !data.attacks) return;

            document.getElementById('total-attacks').textContent = data.total || 0;
            document.getElementById('critical-count').textContent = data.severity?.CRITICAL || 0;
            document.getElementById('high-count').textContent = data.severity?.HIGH || 0;
            document.getElementById('medium-count').textContent = data.severity?.MEDIUM || 0;
            document.getElementById('low-count').textContent = data.severity?.LOW || 0;
            document.getElementById('feed-count').textContent = (data.attacks.length) + ' events';

            allAttacks = data.attacks.slice(-100).reverse();
            renderPacketList();
            renderServiceStats(data.by_service || {});
            renderTopIps(data.top_ips || []);
        }

        function renderPacketList() {
            const container = document.getElementById('attack-feed');
            const empty = document.getElementById('empty-state');
            if (allAttacks.length === 0) {
                empty.style.display = 'flex';
                return;
            }
            empty.style.display = 'none';

            let html = '<div class="pkt-header"><span>No.</span><span>Time</span><span>Source</span><span>Service</span><span>Technique</span><span>Severity</span></div>';
            allAttacks.forEach((atk, i) => {
                const time = new Date(atk.timestamp).toLocaleTimeString();
                const sev = (atk.severity || '').toLowerCase();
                const odd = i % 2 === 0 ? 'pkt-row-odd' : 'pkt-row-even';
                html += '<div class="pkt-row ' + odd + '" onclick="selectEvent(' + i + ')">' +
                    '<span class="pkt-no">' + (i + 1) + '</span>' +
                    '<span class="pkt-time">' + time + '</span>' +
                    '<span class="pkt-src">' + atk.source_ip + '</span>' +
                    '<span class="pkt-svc">' + (atk.service || '') + '</span>' +
                    '<span class="pkt-tech">' + (atk.technique || '') + '</span>' +
                    '<span class="pkt-sev sev-' + sev + '">' + sev + '</span>' +
                    '</div>';
            });
            container.innerHTML = html;
        }

        function selectEvent(idx) {
            selectedIdx = idx;
            const atk = allAttacks[idx];
            if (!atk) return;

            const rows = document.querySelectorAll('.pkt-row');
            rows.forEach((r, i) => r.classList.toggle('selected', i === idx));

            const detail = document.getElementById('detail-content');
            detail.innerHTML =
                '<div class="field"><span class="field-label">Timestamp</span><span class="field-value">' + atk.timestamp + '</span></div>' +
                '<div class="field"><span class="field-label">Source IP</span><span class="field-value">' + atk.source_ip + '</span></div>' +
                '<div class="field"><span class="field-label">Service</span><span class="field-value">' + (atk.service || 'N/A') + '</span></div>' +
                '<div class="field"><span class="field-label">Technique</span><span class="field-value">' + (atk.technique || 'N/A') + '</span></div>' +
                '<div class="field"><span class="field-label">Severity</span><span class="field-value sev-' + (atk.severity || '').toLowerCase() + '">' + (atk.severity || 'N/A') + '</span></div>' +
                '<div class="field"><span class="field-label">Payload</span><span class="field-value">' + (atk.payload || 'N/A') + '</span></div>';
        }

        function renderServiceStats(services) {
            const container = document.getElementById('service-stats');
            const total = Object.values(services).reduce((a, b) => a + b, 0) || 1;
            const order = ['ssh', 'ftp', 'http', 'telnet', 'smb', 'mysql', 'rdp'];
            let html = '';
            order.forEach(svc => {
                const count = services[svc] || 0;
                const pct = (count / total * 100).toFixed(0);
                html += '<div class="svc-row"><span class="svc-name">' + svc.toUpperCase() + '</span><span class="svc-count">' + count + '</span></div>' +
                    '<div class="svc-bar"><div class="svc-bar-fill" style="width:' + pct + '%"></div></div>';
            });
            container.innerHTML = html;
        }

        function renderTopIps(ips) {
            const container = document.getElementById('top-ips');
            if (ips.length === 0) {
                container.innerHTML = '<div style="color:#555;font-size:12px;">No data</div>';
                return;
            }
            container.innerHTML = ips.slice(0, 8).map(ip =>
                '<div class="ip-row"><span class="ip-addr">' + ip.ip + '</span><span class="ip-count">' + ip.count + '</span></div>'
            ).join('');
        }

        fetchData();
        setInterval(fetchData, 3000);
    </script>
</body>
</html>
"""


class AttackTracker:
    """Tracks attacks from log files"""
    
    def __init__(self, log_dir: str = 'logs'):
        self.log_dir = log_dir
        self.attacks: List[Dict] = []
        self._parse_logs()
        
    def _parse_logs(self):
        """Parse existing log files"""
        if not os.path.exists(self.log_dir):
            return
            
        for filename in sorted(os.listdir(self.log_dir)):
            if filename.startswith('attacks_') and filename.endswith('.log'):
                filepath = os.path.join(self.log_dir, filename)
                self._parse_log_file(filepath)
                
    def _parse_log_file(self, filepath: str):
        """Parse a single log file"""
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    parts = line.strip().split(' | ')
                    if len(parts) >= 4:
                        timestamp = parts[0]
                        source = parts[1].split(' -> ')
                        service = source[1] if len(source) > 1 else 'unknown'
                        source_ip = source[0].split(':')[0] if source else 'unknown'
                        technique = parts[2]
                        severity = parts[3].replace('Severity: ', '')
                        
                        self.attacks.append({
                            'timestamp': timestamp,
                            'source_ip': source_ip,
                            'service': service.lower(),
                            'technique': technique,
                            'severity': severity
                        })
        except Exception as e:
            pass
            
    def get_stats(self) -> Dict:
        """Get attack statistics"""
        severity_counts = defaultdict(int)
        service_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        
        for attack in self.attacks:
            severity_counts[attack['severity']] += 1
            service_counts[attack['service']] += 1
            ip_counts[attack['source_ip']] += 1
            
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total': len(self.attacks),
            'severity': dict(severity_counts),
            'by_service': dict(service_counts),
            'top_ips': [{'ip': ip, 'count': count} for ip, count in top_ips],
            'attacks': self.attacks[-100:]
        }
        
    def refresh(self):
        """Refresh data from log files"""
        self.attacks = []
        self._parse_logs()


class MonitorHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for monitoring dashboard"""
    
    tracker: AttackTracker = None
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(DARK_THEME.encode())
            
        elif self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            stats = self.tracker.get_stats()
            self.wfile.write(json.dumps(stats, indent=2).encode())
            
        elif self.path == '/api/refresh':
            self.tracker.refresh()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            
        else:
            super().do_GET()
            
    def log_message(self, format, *args):
        pass


class MonitoringServer:
    """Monitoring web server"""
    
    def __init__(self, port: int = 8081, log_dir: str = 'logs'):
        self.port = port
        self.log_dir = log_dir
        self.tracker = AttackTracker(log_dir)
        self.server = None
        
    def start(self):
        """Start the monitoring server"""
        MonitorHandler.tracker = self.tracker
        
        self.server = socketserver.TCPServer(('', self.port), MonitorHandler)
        self.server.allow_reuse_address = True
        
        print(f"""
╔══════════════════════════════════════════════════════════╗
║           Blood-Web Monitoring Dashboard                  ║
╚══════════════════════════════════════════════════════════╝
  [+] Dashboard URL: http://localhost:{self.port}
  [+] API Endpoint:  http://localhost:{self.port}/api/stats
  [+] Refresh:       http://localhost:{self.port}/api/refresh
  
  Press Ctrl+C to stop the dashboard
""")
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n[-] Shutting down dashboard...")
            self.server.shutdown()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Blood-Web Monitoring Dashboard')
    parser.add_argument('--port', type=int, default=8081, help='Dashboard port (default: 8081)')
    parser.add_argument('--log-dir', default='logs', help='Log directory')
    
    args = parser.parse_args()
    
    server = MonitoringServer(port=args.port, log_dir=args.log_dir)
    server.start()


if __name__ == '__main__':
    main()
