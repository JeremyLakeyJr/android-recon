#!/usr/bin/env python3
"""
Linux Recon - Web Dashboard Server
===================================
Optional localhost web dashboard for viewing scan results.
Uses Flask for lightweight web serving.

Features:
- REST API for scan results
- Real-time data updates via polling
- Responsive dashboard UI
- Device filtering and search
- Export functionality
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Check for Flask availability
try:
    from flask import Flask, jsonify, render_template_string, request, send_from_directory
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Warning: Flask not installed. Install with: pip install flask", file=sys.stderr)

# Add lib to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# HTML Template for the dashboard
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Linux Recon - Dashboard</title>
    <style>
        :root {
            --bg-primary: #0a0a0a;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #2a2a2a;
            --text-primary: #00ff00;
            --text-secondary: #00cc00;
            --text-muted: #666;
            --accent-network: #00aaff;
            --accent-wifi: #ffaa00;
            --accent-bluetooth: #ff00aa;
            --border-color: #333;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Courier New', Courier, monospace;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 20px;
            border-bottom: 2px solid var(--text-secondary);
            margin-bottom: 20px;
        }
        
        header h1 {
            font-size: 2em;
            text-shadow: 0 0 10px var(--text-primary);
            letter-spacing: 3px;
        }
        
        header .subtitle {
            color: var(--text-muted);
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .stats-bar {
            display: flex;
            justify-content: center;
            gap: 30px;
            padding: 15px;
            background: var(--bg-secondary);
            border-radius: 5px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-label {
            color: var(--text-muted);
            font-size: 0.8em;
            text-transform: uppercase;
        }
        
        .stat.network .stat-value { color: var(--accent-network); }
        .stat.wifi .stat-value { color: var(--accent-wifi); }
        .stat.bluetooth .stat-value { color: var(--accent-bluetooth); }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .controls input, .controls select, .controls button {
            padding: 10px 15px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            font-family: inherit;
            border-radius: 3px;
        }
        
        .controls input:focus, .controls select:focus {
            outline: none;
            border-color: var(--text-primary);
        }
        
        .controls button {
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .controls button:hover {
            background: var(--text-primary);
            color: var(--bg-primary);
        }
        
        .controls input[type="text"] {
            flex: 1;
            min-width: 200px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 15px;
        }
        
        .device-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 5px;
            padding: 15px;
            transition: all 0.2s;
        }
        
        .device-card:hover {
            border-color: var(--text-primary);
            transform: translateY(-2px);
        }
        
        .device-card.network { border-left: 3px solid var(--accent-network); }
        .device-card.wifi { border-left: 3px solid var(--accent-wifi); }
        .device-card.bluetooth { border-left: 3px solid var(--accent-bluetooth); }
        
        .device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .device-name {
            font-weight: bold;
            font-size: 1.1em;
            word-break: break-all;
        }
        
        .device-type {
            font-size: 0.8em;
            padding: 3px 8px;
            border-radius: 3px;
            text-transform: uppercase;
        }
        
        .device-type.network { background: var(--accent-network); color: var(--bg-primary); }
        .device-type.wifi { background: var(--accent-wifi); color: var(--bg-primary); }
        .device-type.bluetooth { background: var(--accent-bluetooth); color: var(--bg-primary); }
        
        .device-details {
            font-size: 0.9em;
            color: var(--text-secondary);
        }
        
        .device-details .row {
            display: flex;
            padding: 3px 0;
        }
        
        .device-details .label {
            color: var(--text-muted);
            width: 80px;
        }
        
        .device-details .value {
            flex: 1;
            word-break: break-all;
        }
        
        .signal-bar {
            display: inline-block;
            height: 10px;
            background: linear-gradient(to right, var(--text-primary) var(--signal), var(--bg-tertiary) var(--signal));
            border-radius: 2px;
            width: 100px;
            margin-left: 5px;
            vertical-align: middle;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: var(--text-muted);
        }
        
        .loading::after {
            content: '';
            animation: dots 1.5s infinite;
        }
        
        @keyframes dots {
            0% { content: ''; }
            25% { content: '.'; }
            50% { content: '..'; }
            75% { content: '...'; }
        }
        
        .empty-state {
            text-align: center;
            padding: 50px;
            color: var(--text-muted);
        }
        
        .empty-state .icon {
            font-size: 3em;
            margin-bottom: 20px;
        }
        
        footer {
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 0.8em;
            margin-top: 30px;
            border-top: 1px solid var(--border-color);
        }
        
        .auto-refresh-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: var(--text-primary);
            border-radius: 50%;
            margin-right: 5px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        @media (max-width: 600px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .stats-bar {
                flex-direction: column;
                gap: 10px;
            }
            
            header h1 {
                font-size: 1.5em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⟨ LINUX RECON ⟩</h1>
            <div class="subtitle">Reconnaissance Radar Dashboard</div>
        </header>
        
        <div class="stats-bar">
            <div class="stat total">
                <div class="stat-value" id="total-count">-</div>
                <div class="stat-label">Total Devices</div>
            </div>
            <div class="stat network">
                <div class="stat-value" id="network-count">-</div>
                <div class="stat-label">Network</div>
            </div>
            <div class="stat wifi">
                <div class="stat-value" id="wifi-count">-</div>
                <div class="stat-label">WiFi</div>
            </div>
            <div class="stat bluetooth">
                <div class="stat-value" id="bluetooth-count">-</div>
                <div class="stat-label">Bluetooth</div>
            </div>
        </div>
        
        <div class="controls">
            <input type="text" id="search" placeholder="Search devices..." oninput="filterDevices()">
            <select id="type-filter" onchange="filterDevices()">
                <option value="all">All Types</option>
                <option value="network">Network</option>
                <option value="wifi">WiFi</option>
                <option value="bluetooth">Bluetooth</option>
            </select>
            <button onclick="refreshData()">↻ Refresh</button>
            <button onclick="exportData()">⬇ Export JSON</button>
        </div>
        
        <div id="device-grid" class="grid">
            <div class="loading">Loading devices</div>
        </div>
        
        <footer>
            <span class="auto-refresh-indicator"></span>
            Auto-refreshing every <span id="refresh-interval">5</span> seconds
            | Last update: <span id="last-update">-</span>
        </footer>
    </div>
    
    <script>
        let allDevices = [];
        const refreshInterval = 5000;
        
        async function fetchDevices() {
            try {
                const response = await fetch('/api/devices');
                const data = await response.json();
                allDevices = data.devices || [];
                updateStats(data);
                renderDevices(allDevices);
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error fetching devices:', error);
            }
        }
        
        function updateStats(data) {
            document.getElementById('total-count').textContent = data.total || 0;
            document.getElementById('network-count').textContent = data.network_count || 0;
            document.getElementById('wifi-count').textContent = data.wifi_count || 0;
            document.getElementById('bluetooth-count').textContent = data.bluetooth_count || 0;
        }
        
        function renderDevices(devices) {
            const grid = document.getElementById('device-grid');
            
            if (devices.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state" style="grid-column: 1 / -1;">
                        <div class="icon">📡</div>
                        <div>No devices found</div>
                        <div style="margin-top: 10px;">Run a scan to discover devices</div>
                    </div>
                `;
                return;
            }
            
            grid.innerHTML = devices.map(device => {
                const type = device.scan_type || 'unknown';
                const name = device.name || device.ssid || device.ip || device.address || 'Unknown';
                const ip = device.ip || '-';
                const mac = device.mac || device.address || device.bssid || '-';
                const signal = device.signal_dbm;
                const signalQuality = device.signal_quality || (signal ? Math.max(0, Math.min(100, (signal + 100) * 2)) : null);
                
                let details = '';
                
                if (type === 'network') {
                    details = `
                        <div class="row"><span class="label">IP:</span><span class="value">${ip}</span></div>
                        <div class="row"><span class="label">MAC:</span><span class="value">${mac}</span></div>
                        ${device.hostname ? `<div class="row"><span class="label">Host:</span><span class="value">${device.hostname}</span></div>` : ''}
                        ${device.latency_ms ? `<div class="row"><span class="label">Latency:</span><span class="value">${device.latency_ms} ms</span></div>` : ''}
                    `;
                } else if (type === 'wifi') {
                    details = `
                        <div class="row"><span class="label">BSSID:</span><span class="value">${mac}</span></div>
                        ${device.channel ? `<div class="row"><span class="label">Channel:</span><span class="value">${device.channel}</span></div>` : ''}
                        ${signalQuality !== null ? `<div class="row"><span class="label">Signal:</span><span class="value">${signal || ''} dBm <span class="signal-bar" style="--signal: ${signalQuality}%"></span></span></div>` : ''}
                        ${device.security ? `<div class="row"><span class="label">Security:</span><span class="value">${device.security} ${device.encryption ? '(' + device.encryption.join(', ') + ')' : ''}</span></div>` : ''}
                    `;
                } else if (type === 'bluetooth') {
                    details = `
                        <div class="row"><span class="label">Address:</span><span class="value">${mac}</span></div>
                        ${device.type ? `<div class="row"><span class="label">Type:</span><span class="value">${device.type}</span></div>` : ''}
                        ${device.device_type ? `<div class="row"><span class="label">Device:</span><span class="value">${device.device_type}</span></div>` : ''}
                        ${device.rssi ? `<div class="row"><span class="label">RSSI:</span><span class="value">${device.rssi} dBm</span></div>` : ''}
                    `;
                }
                
                return `
                    <div class="device-card ${type}">
                        <div class="device-header">
                            <span class="device-name">${escapeHtml(name)}</span>
                            <span class="device-type ${type}">${type}</span>
                        </div>
                        <div class="device-details">
                            ${details}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function filterDevices() {
            const search = document.getElementById('search').value.toLowerCase();
            const typeFilter = document.getElementById('type-filter').value;
            
            const filtered = allDevices.filter(device => {
                const matchesType = typeFilter === 'all' || device.scan_type === typeFilter;
                
                if (!matchesType) return false;
                
                if (!search) return true;
                
                const searchFields = [
                    device.name,
                    device.ssid,
                    device.ip,
                    device.mac,
                    device.address,
                    device.bssid,
                    device.hostname
                ].filter(Boolean).join(' ').toLowerCase();
                
                return searchFields.includes(search);
            });
            
            renderDevices(filtered);
        }
        
        function refreshData() {
            fetchDevices();
        }
        
        async function exportData() {
            try {
                const response = await fetch('/api/export');
                const data = await response.json();
                
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = url;
                a.download = `recon_export_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (error) {
                console.error('Error exporting data:', error);
                alert('Error exporting data');
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Initial load and auto-refresh
        fetchDevices();
        setInterval(fetchDevices, refreshInterval);
        document.getElementById('refresh-interval').textContent = refreshInterval / 1000;
    </script>
</body>
</html>
'''


def create_app(output_dir: str) -> 'Flask':
    """
    Create Flask application.
    
    Args:
        output_dir: Directory containing scan results
    
    Returns:
        Flask application instance
    """
    if not FLASK_AVAILABLE:
        raise ImportError("Flask is required for the web dashboard")
    
    app = Flask(__name__)
    app.config['OUTPUT_DIR'] = output_dir
    
    def load_all_devices() -> List[Dict[str, Any]]:
        """Load all devices from scan results."""
        devices = []
        
        if not os.path.exists(output_dir):
            return devices
        
        for filename in os.listdir(output_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'r') as f:
                    scan = json.load(f)
                
                scan_type = scan.get('scan_type', 'unknown')
                data = scan.get('data', [])
                
                for item in data:
                    device = {
                        'scan_type': scan_type,
                        **item
                    }
                    devices.append(device)
            
            except (json.JSONDecodeError, IOError):
                continue
        
        return devices
    
    @app.route('/')
    def dashboard():
        """Serve the dashboard page."""
        return render_template_string(DASHBOARD_HTML)
    
    @app.route('/api/devices')
    def api_devices():
        """API endpoint to get all devices."""
        devices = load_all_devices()
        
        # Count by type
        network_count = sum(1 for d in devices if d.get('scan_type') == 'network')
        wifi_count = sum(1 for d in devices if d.get('scan_type') == 'wifi')
        bluetooth_count = sum(1 for d in devices if d.get('scan_type') == 'bluetooth')
        
        return jsonify({
            'devices': devices,
            'total': len(devices),
            'network_count': network_count,
            'wifi_count': wifi_count,
            'bluetooth_count': bluetooth_count,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/export')
    def api_export():
        """API endpoint to export all scan data."""
        devices = load_all_devices()
        
        return jsonify({
            'export_timestamp': datetime.now().isoformat(),
            'total_devices': len(devices),
            'devices': devices
        })
    
    @app.route('/api/scan/<scan_type>')
    def api_scan_type(scan_type: str):
        """API endpoint to get devices by scan type."""
        devices = load_all_devices()
        filtered = [d for d in devices if d.get('scan_type') == scan_type]
        
        return jsonify({
            'scan_type': scan_type,
            'devices': filtered,
            'count': len(filtered),
            'timestamp': datetime.now().isoformat()
        })
    
    return app


def run_server(host: str = '127.0.0.1', port: int = 8080, output_dir: str = './output', debug: bool = False):
    """
    Run the web dashboard server.
    
    Args:
        host: Host address to bind to
        port: Port number
        output_dir: Directory containing scan results
        debug: Enable debug mode
    """
    if not FLASK_AVAILABLE:
        print("Error: Flask is not installed.", file=sys.stderr)
        print("Install with: pip install flask", file=sys.stderr)
        sys.exit(1)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    app = create_app(output_dir)
    
    print(f"Starting web dashboard at http://{host}:{port}")
    print(f"Reading scan results from: {output_dir}")
    print("Press Ctrl+C to stop")
    
    app.run(host=host, port=port, debug=debug)


def main():
    """Main entry point for web server."""
    parser = argparse.ArgumentParser(
        description="Web Dashboard - Browser-based scan result viewer"
    )
    parser.add_argument(
        "--host", "-H",
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Port number (default: 8080)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory containing scan results"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    run_server(
        host=args.host,
        port=args.port,
        output_dir=args.output,
        debug=args.debug
    )


if __name__ == "__main__":
    main()
