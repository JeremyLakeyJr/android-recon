#!/usr/bin/env python3
"""
Linux Recon - Radar Terminal UI
================================
Real-time radar-style terminal interface for displaying scan results.
Uses curses for cross-platform terminal rendering.

Features:
- Animated radar sweep visualization
- Real-time device discovery display
- Color-coded device types
- Signal strength indicators
- Auto-refresh from scan results
"""

import argparse
import curses
import json
import math
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Add lib to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RadarUI:
    """Radar-style terminal user interface."""
    
    # Color pair indices
    COLOR_HEADER = 1
    COLOR_RADAR = 2
    COLOR_DEVICE_NETWORK = 3
    COLOR_DEVICE_WIFI = 4
    COLOR_DEVICE_BLUETOOTH = 5
    COLOR_STATUS = 6
    COLOR_ALERT = 7
    COLOR_DIM = 8
    
    def __init__(self, output_dir: str, refresh_rate: float = 1.0):
        """
        Initialize radar UI.
        
        Args:
            output_dir: Directory containing scan results
            refresh_rate: Screen refresh rate in seconds
        """
        self.output_dir = output_dir
        self.refresh_rate = refresh_rate
        self.stdscr = None
        self.devices: List[Dict[str, Any]] = []
        self.scan_angle = 0
        self.last_scan_time = None
        self.running = True
        
        # UI state
        self.selected_index = 0
        self.scroll_offset = 0
        self.view_mode = 'radar'  # 'radar' or 'list'
    
    def init_colors(self):
        """Initialize color pairs."""
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(self.COLOR_HEADER, curses.COLOR_CYAN, -1)
        curses.init_pair(self.COLOR_RADAR, curses.COLOR_GREEN, -1)
        curses.init_pair(self.COLOR_DEVICE_NETWORK, curses.COLOR_BLUE, -1)
        curses.init_pair(self.COLOR_DEVICE_WIFI, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.COLOR_DEVICE_BLUETOOTH, curses.COLOR_MAGENTA, -1)
        curses.init_pair(self.COLOR_STATUS, curses.COLOR_WHITE, -1)
        curses.init_pair(self.COLOR_ALERT, curses.COLOR_RED, -1)
        curses.init_pair(self.COLOR_DIM, curses.COLOR_WHITE, -1)
    
    def load_scan_results(self) -> List[Dict[str, Any]]:
        """
        Load latest scan results from output directory.
        
        Returns:
            List of discovered devices
        """
        devices = []
        
        if not os.path.exists(self.output_dir):
            return devices
        
        # Load all scan files
        for filename in os.listdir(self.output_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.output_dir, filename)
            
            try:
                with open(filepath, 'r') as f:
                    scan = json.load(f)
                
                scan_type = scan.get('scan_type', 'unknown')
                data = scan.get('data', [])
                timestamp = scan.get('timestamp', '')
                
                for item in data:
                    device = {
                        'scan_type': scan_type,
                        'timestamp': timestamp,
                        **item
                    }
                    devices.append(device)
            
            except (json.JSONDecodeError, IOError):
                continue
        
        # Sort by scan type and then by name/IP
        devices.sort(key=lambda d: (d.get('scan_type', ''), d.get('name', d.get('ip', ''))))
        
        self.last_scan_time = datetime.now()
        return devices
    
    def draw_header(self, height: int, width: int):
        """Draw the header section."""
        title = " LINUX RECON - RADAR "
        
        # Draw top border
        self.stdscr.attron(curses.color_pair(self.COLOR_HEADER))
        self.stdscr.addstr(0, 0, "╔" + "═" * (width - 2) + "╗")
        
        # Draw title
        title_pos = (width - len(title)) // 2
        self.stdscr.addstr(1, 0, "║")
        self.stdscr.addstr(1, title_pos, title, curses.A_BOLD)
        self.stdscr.addstr(1, width - 1, "║")
        
        # Draw separator
        self.stdscr.addstr(2, 0, "╠" + "═" * (width - 2) + "╣")
        self.stdscr.attroff(curses.color_pair(self.COLOR_HEADER))
    
    def draw_radar(self, start_y: int, start_x: int, size: int):
        """
        Draw animated radar sweep visualization.
        
        Args:
            start_y: Starting Y position
            start_x: Starting X position
            size: Radar size (radius)
        """
        center_y = start_y + size // 2
        center_x = start_x + size
        
        self.stdscr.attron(curses.color_pair(self.COLOR_RADAR))
        
        # Draw radar circles
        for r in range(1, size, size // 4 or 1):
            for angle in range(360):
                rad = math.radians(angle)
                y = int(center_y + r * 0.5 * math.sin(rad))
                x = int(center_x + r * math.cos(rad))
                
                if 0 <= y < curses.LINES - 1 and 0 <= x < curses.COLS - 1:
                    try:
                        self.stdscr.addch(y, x, '·')
                    except curses.error:
                        pass
        
        # Draw crosshairs
        for i in range(-size, size + 1):
            y = center_y
            x = center_x + i
            if 0 <= y < curses.LINES - 1 and 0 <= x < curses.COLS - 1:
                try:
                    self.stdscr.addch(y, x, '─')
                except curses.error:
                    pass
        
        for i in range(-size // 2, size // 2 + 1):
            y = center_y + i
            x = center_x
            if 0 <= y < curses.LINES - 1 and 0 <= x < curses.COLS - 1:
                try:
                    self.stdscr.addch(y, x, '│')
                except curses.error:
                    pass
        
        # Draw center
        if 0 <= center_y < curses.LINES - 1 and 0 <= center_x < curses.COLS - 1:
            try:
                self.stdscr.addch(center_y, center_x, '┼')
            except curses.error:
                pass
        
        # Draw sweep line
        sweep_rad = math.radians(self.scan_angle)
        for r in range(1, size):
            y = int(center_y + r * 0.5 * math.sin(sweep_rad))
            x = int(center_x + r * math.cos(sweep_rad))
            
            if 0 <= y < curses.LINES - 1 and 0 <= x < curses.COLS - 1:
                try:
                    self.stdscr.addch(y, x, '█', curses.A_BOLD)
                except curses.error:
                    pass
        
        # Draw devices as blips
        for i, device in enumerate(self.devices[:20]):
            # Calculate position based on device index
            device_angle = (i * 360 / max(len(self.devices), 1)) % 360
            device_rad = math.radians(device_angle)
            
            # Distance based on signal strength if available
            signal = device.get('signal_dbm') or device.get('latency_ms')
            if signal:
                if device.get('signal_dbm'):
                    # WiFi/BT signal: -30 (near) to -90 (far)
                    distance = max(0.2, min(0.9, (abs(signal) - 30) / 60))
                else:
                    # Network latency: 0 (near) to 200ms (far)
                    distance = max(0.2, min(0.9, signal / 200))
            else:
                distance = 0.5 + (i % 5) * 0.1
            
            r = int(size * distance)
            y = int(center_y + r * 0.5 * math.sin(device_rad))
            x = int(center_x + r * math.cos(device_rad))
            
            # Choose color and character based on device type
            scan_type = device.get('scan_type', 'unknown')
            if scan_type == 'network':
                color = self.COLOR_DEVICE_NETWORK
                char = '◆'
            elif scan_type == 'wifi':
                color = self.COLOR_DEVICE_WIFI
                char = '◈'
            elif scan_type == 'bluetooth':
                color = self.COLOR_DEVICE_BLUETOOTH
                char = '●'
            else:
                color = self.COLOR_STATUS
                char = '○'
            
            if 0 <= y < curses.LINES - 1 and 0 <= x < curses.COLS - 1:
                self.stdscr.attron(curses.color_pair(color))
                try:
                    self.stdscr.addch(y, x, char)
                except curses.error:
                    pass
                self.stdscr.attroff(curses.color_pair(color))
        
        self.stdscr.attroff(curses.color_pair(self.COLOR_RADAR))
    
    def draw_device_list(self, start_y: int, start_x: int, height: int, width: int):
        """
        Draw device list panel.
        
        Args:
            start_y: Starting Y position
            start_x: Starting X position
            height: Panel height
            width: Panel width
        """
        # Draw panel border
        self.stdscr.attron(curses.color_pair(self.COLOR_HEADER))
        self.stdscr.addstr(start_y, start_x, "╔" + "═" * (width - 2) + "╗")
        
        title = " DISCOVERED DEVICES "
        title_pos = start_x + (width - len(title)) // 2
        self.stdscr.addstr(start_y, title_pos, title)
        
        for i in range(1, height - 1):
            self.stdscr.addstr(start_y + i, start_x, "║")
            self.stdscr.addstr(start_y + i, start_x + width - 1, "║")
        
        self.stdscr.addstr(start_y + height - 1, start_x, "╚" + "═" * (width - 2) + "╝")
        self.stdscr.attroff(curses.color_pair(self.COLOR_HEADER))
        
        # Draw device entries
        visible_height = height - 2
        visible_devices = self.devices[self.scroll_offset:self.scroll_offset + visible_height]
        
        for i, device in enumerate(visible_devices):
            y = start_y + 1 + i
            
            # Choose color based on device type
            scan_type = device.get('scan_type', 'unknown')
            if scan_type == 'network':
                color = self.COLOR_DEVICE_NETWORK
                icon = '◆'
            elif scan_type == 'wifi':
                color = self.COLOR_DEVICE_WIFI
                icon = '◈'
            elif scan_type == 'bluetooth':
                color = self.COLOR_DEVICE_BLUETOOTH
                icon = '●'
            else:
                color = self.COLOR_STATUS
                icon = '○'
            
            # Get device display name
            name = device.get('name') or device.get('ssid') or device.get('ip') or device.get('address', 'Unknown')
            if len(name) > width - 8:
                name = name[:width - 11] + '...'
            
            # Highlight selected item
            attr = curses.A_REVERSE if i + self.scroll_offset == self.selected_index else 0
            
            self.stdscr.attron(curses.color_pair(color) | attr)
            line = f" {icon} {name}"
            line = line.ljust(width - 2)
            try:
                self.stdscr.addstr(y, start_x + 1, line[:width - 2])
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(color) | attr)
        
        # Draw scroll indicator if needed
        if len(self.devices) > visible_height:
            scroll_pct = self.scroll_offset / max(1, len(self.devices) - visible_height)
            indicator_pos = start_y + 1 + int(scroll_pct * (visible_height - 1))
            self.stdscr.attron(curses.color_pair(self.COLOR_HEADER))
            try:
                self.stdscr.addch(indicator_pos, start_x + width - 1, '█')
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(self.COLOR_HEADER))
    
    def draw_detail_panel(self, start_y: int, start_x: int, height: int, width: int):
        """
        Draw device detail panel.
        
        Args:
            start_y: Starting Y position
            start_x: Starting X position
            height: Panel height
            width: Panel width
        """
        # Draw panel border
        self.stdscr.attron(curses.color_pair(self.COLOR_HEADER))
        self.stdscr.addstr(start_y, start_x, "╔" + "═" * (width - 2) + "╗")
        
        title = " DEVICE DETAILS "
        title_pos = start_x + (width - len(title)) // 2
        self.stdscr.addstr(start_y, title_pos, title)
        
        for i in range(1, height - 1):
            self.stdscr.addstr(start_y + i, start_x, "║")
            self.stdscr.addstr(start_y + i, start_x + width - 1, "║")
        
        self.stdscr.addstr(start_y + height - 1, start_x, "╚" + "═" * (width - 2) + "╝")
        self.stdscr.attroff(curses.color_pair(self.COLOR_HEADER))
        
        # Draw selected device details
        if 0 <= self.selected_index < len(self.devices):
            device = self.devices[self.selected_index]
            
            y = start_y + 1
            
            # Display device properties
            props = [
                ('Type', device.get('scan_type', 'Unknown').title()),
                ('Name', device.get('name') or device.get('ssid') or 'Unknown'),
                ('IP', device.get('ip', '-')),
                ('MAC', device.get('mac') or device.get('address') or device.get('bssid', '-')),
                ('Signal', f"{device.get('signal_dbm', '-')} dBm" if device.get('signal_dbm') else '-'),
                ('Channel', str(device.get('channel', '-'))),
                ('Latency', f"{device.get('latency_ms', '-')} ms" if device.get('latency_ms') else '-'),
                ('Security', device.get('security', '-')),
                ('State', device.get('state', '-')),
            ]
            
            for prop_name, prop_value in props:
                if y >= start_y + height - 1:
                    break
                
                line = f" {prop_name}: {prop_value}"
                if len(line) > width - 2:
                    line = line[:width - 5] + '...'
                
                self.stdscr.attron(curses.color_pair(self.COLOR_STATUS))
                try:
                    self.stdscr.addstr(y, start_x + 1, line[:width - 2])
                except curses.error:
                    pass
                self.stdscr.attroff(curses.color_pair(self.COLOR_STATUS))
                y += 1
    
    def draw_status_bar(self, height: int, width: int):
        """Draw status bar at bottom."""
        y = height - 1
        
        # Build status text
        device_count = len(self.devices)
        network_count = sum(1 for d in self.devices if d.get('scan_type') == 'network')
        wifi_count = sum(1 for d in self.devices if d.get('scan_type') == 'wifi')
        bt_count = sum(1 for d in self.devices if d.get('scan_type') == 'bluetooth')
        
        status = f" Devices: {device_count} | Net: {network_count} | WiFi: {wifi_count} | BT: {bt_count}"
        
        if self.last_scan_time:
            status += f" | Last scan: {self.last_scan_time.strftime('%H:%M:%S')}"
        
        # Draw status bar
        self.stdscr.attron(curses.color_pair(self.COLOR_HEADER) | curses.A_REVERSE)
        try:
            self.stdscr.addstr(y, 0, status.ljust(width - 1)[:width - 1])
        except curses.error:
            pass
        self.stdscr.attroff(curses.color_pair(self.COLOR_HEADER) | curses.A_REVERSE)
        
        # Draw help text
        help_text = " [Q]uit [R]efresh [↑↓]Navigate "
        help_pos = width - len(help_text) - 1
        if help_pos > len(status):
            self.stdscr.attron(curses.color_pair(self.COLOR_DIM) | curses.A_REVERSE)
            try:
                self.stdscr.addstr(y, help_pos, help_text)
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(self.COLOR_DIM) | curses.A_REVERSE)
    
    def draw(self):
        """Draw the entire UI."""
        self.stdscr.clear()
        
        height, width = self.stdscr.getmaxyx()
        
        # Minimum size check
        if height < 15 or width < 60:
            self.stdscr.addstr(0, 0, "Terminal too small. Resize to at least 60x15.")
            self.stdscr.refresh()
            return
        
        # Draw header
        self.draw_header(height, width)
        
        # Calculate panel sizes
        content_start_y = 3
        content_height = height - 4  # Account for header and status bar
        
        # Radar takes left half, device list takes right half
        radar_width = width // 2
        list_width = width - radar_width
        
        # Draw radar
        radar_size = min(radar_width // 2 - 2, content_height - 2)
        if radar_size > 3:
            self.draw_radar(content_start_y + 1, 2, radar_size)
        
        # Draw device list
        list_height = content_height // 2
        self.draw_device_list(
            content_start_y,
            radar_width,
            list_height,
            list_width - 1
        )
        
        # Draw detail panel
        self.draw_detail_panel(
            content_start_y + list_height,
            radar_width,
            content_height - list_height,
            list_width - 1
        )
        
        # Draw status bar
        self.draw_status_bar(height, width)
        
        self.stdscr.refresh()
    
    def handle_input(self):
        """Handle keyboard input."""
        self.stdscr.nodelay(True)
        
        try:
            key = self.stdscr.getch()
        except curses.error:
            return
        
        if key == -1:
            return
        
        if key in (ord('q'), ord('Q')):
            self.running = False
        elif key in (ord('r'), ord('R')):
            self.devices = self.load_scan_results()
        elif key == curses.KEY_UP:
            if self.selected_index > 0:
                self.selected_index -= 1
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset = self.selected_index
        elif key == curses.KEY_DOWN:
            if self.selected_index < len(self.devices) - 1:
                self.selected_index += 1
                height = self.stdscr.getmaxyx()[0]
                visible_height = (height - 4) // 2 - 2
                if self.selected_index >= self.scroll_offset + visible_height:
                    self.scroll_offset = self.selected_index - visible_height + 1
    
    def run(self, stdscr):
        """
        Main UI loop.
        
        Args:
            stdscr: Curses standard screen
        """
        self.stdscr = stdscr
        
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        self.init_colors()
        
        # Initial load
        self.devices = self.load_scan_results()
        
        # Main loop
        last_refresh = 0
        
        while self.running:
            current_time = time.time()
            
            # Auto-refresh scan results
            if current_time - last_refresh > 5:
                self.devices = self.load_scan_results()
                last_refresh = current_time
            
            # Update radar animation
            self.scan_angle = (self.scan_angle + 5) % 360
            
            # Draw and handle input
            self.draw()
            self.handle_input()
            
            # Control refresh rate with minimum threshold to avoid high CPU usage
            sleep_time = max(0.05, self.refresh_rate / 10)
            time.sleep(sleep_time)


def run_radar_ui(output_dir: str, refresh_rate: float = 1.0):
    """
    Launch the radar UI.
    
    Args:
        output_dir: Directory containing scan results
        refresh_rate: Screen refresh rate in seconds
    """
    ui = RadarUI(output_dir, refresh_rate)
    curses.wrapper(ui.run)


def main():
    """Main entry point for radar UI."""
    parser = argparse.ArgumentParser(
        description="Radar UI - Real-time terminal visualization of scan results"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory containing scan results"
    )
    parser.add_argument(
        "--refresh", "-r",
        type=float,
        default=1.0,
        help="Refresh rate in seconds (default: 1.0)"
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output, exist_ok=True)
    
    run_radar_ui(args.output, args.refresh)


if __name__ == "__main__":
    main()
