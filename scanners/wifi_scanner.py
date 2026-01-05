#!/usr/bin/env python3
"""
Linux Recon - WiFi Scanner Module
==================================
Scans for nearby WiFi networks and collects wireless information.
Outputs results in standardized JSON format.

Features:
- WiFi network discovery
- Signal strength measurement
- Security type detection
- Channel information
- BSSID collection
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# Add lib to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.json_utils import ScanResultBuilder, print_json


def get_wireless_interfaces() -> List[str]:
    """
    Get list of wireless interfaces.
    
    Returns:
        List of wireless interface names
    """
    interfaces = []
    
    # Try iw command
    try:
        result = subprocess.run(
            ['iw', 'dev'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        interfaces.append(parts[1])
            
            if interfaces:
                return interfaces
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: Check /sys/class/net/*/wireless
    try:
        for iface in os.listdir('/sys/class/net'):
            wireless_path = f'/sys/class/net/{iface}/wireless'
            if os.path.exists(wireless_path):
                interfaces.append(iface)
    except (IOError, OSError):
        pass
    
    # Fallback: Look for common wireless interface names
    if not interfaces:
        common_names = ['wlan0', 'wlan1', 'wlp2s0', 'wlp3s0', 'wifi0']
        for name in common_names:
            if os.path.exists(f'/sys/class/net/{name}'):
                interfaces.append(name)
    
    return interfaces


def get_current_connection(interface: str) -> Optional[Dict[str, Any]]:
    """
    Get information about the currently connected WiFi network.
    
    Args:
        interface: Wireless interface name
    
    Returns:
        Dictionary with connection info or None
    """
    connection = {}
    
    # Try iw command
    try:
        result = subprocess.run(
            ['iw', interface, 'link'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and 'Connected to' in result.stdout:
            # Parse BSSID
            bssid_match = re.search(r'Connected to ([0-9a-fA-F:]{17})', result.stdout)
            if bssid_match:
                connection['bssid'] = bssid_match.group(1).upper()
            
            # Parse SSID
            ssid_match = re.search(r'SSID:\s*(.+)', result.stdout)
            if ssid_match:
                connection['ssid'] = ssid_match.group(1).strip()
            
            # Parse frequency
            freq_match = re.search(r'freq:\s*(\d+)', result.stdout)
            if freq_match:
                connection['frequency'] = int(freq_match.group(1))
            
            # Parse signal
            signal_match = re.search(r'signal:\s*(-?\d+)\s*dBm', result.stdout)
            if signal_match:
                connection['signal_dbm'] = int(signal_match.group(1))
            
            return connection if connection else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return None


def scan_wifi_networks_iw(interface: str) -> List[Dict[str, Any]]:
    """
    Scan for WiFi networks using iw command.
    
    Args:
        interface: Wireless interface name
    
    Returns:
        List of discovered networks
    """
    networks = []
    
    try:
        # Trigger a scan
        subprocess.run(
            ['iw', interface, 'scan', 'trigger'],
            capture_output=True,
            timeout=5
        )
        
        # Wait a moment for scan to complete
        time.sleep(2)
        
        # Get scan results
        result = subprocess.run(
            ['iw', interface, 'scan', 'dump'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            # Try without dump
            result = subprocess.run(
                ['iw', interface, 'scan'],
                capture_output=True,
                text=True,
                timeout=30
            )
        
        if result.returncode == 0:
            current_network = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                # New BSS (network)
                bss_match = re.match(r'BSS\s+([0-9a-fA-F:]{17})', line)
                if bss_match:
                    if current_network:
                        networks.append(current_network)
                    current_network = {
                        'bssid': bss_match.group(1).upper(),
                        'ssid': None,
                        'frequency': None,
                        'channel': None,
                        'signal_dbm': None,
                        'signal_quality': None,
                        'security': 'Open',
                        'encryption': []
                    }
                    continue
                
                if current_network is None:
                    continue
                
                # SSID
                ssid_match = re.match(r'SSID:\s*(.*)', line)
                if ssid_match:
                    ssid = ssid_match.group(1).strip()
                    current_network['ssid'] = ssid if ssid else '<hidden>'
                    continue
                
                # Frequency and channel
                freq_match = re.match(r'freq:\s*(\d+)', line)
                if freq_match:
                    freq = int(freq_match.group(1))
                    current_network['frequency'] = freq
                    current_network['channel'] = freq_to_channel(freq)
                    continue
                
                # Signal strength
                signal_match = re.match(r'signal:\s*(-?\d+\.?\d*)\s*dBm', line)
                if signal_match:
                    signal = float(signal_match.group(1))
                    current_network['signal_dbm'] = signal
                    current_network['signal_quality'] = dbm_to_quality(signal)
                    continue
                
                # Security - WPA/WPA2/WPA3
                if 'WPA:' in line or 'RSN:' in line:
                    if 'WPA:' in line and 'WPA' not in current_network['encryption']:
                        current_network['encryption'].append('WPA')
                    if 'RSN:' in line:
                        current_network['encryption'].append('WPA2')
                    current_network['security'] = 'Secured'
                
                # WEP
                if 'Privacy' in line and not current_network['encryption']:
                    current_network['encryption'].append('WEP')
                    current_network['security'] = 'Secured'
            
            # Add last network
            if current_network:
                networks.append(current_network)
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return networks


def scan_wifi_networks_iwlist(interface: str) -> List[Dict[str, Any]]:
    """
    Scan for WiFi networks using iwlist command (fallback).
    
    Args:
        interface: Wireless interface name
    
    Returns:
        List of discovered networks
    """
    networks = []
    
    try:
        result = subprocess.run(
            ['iwlist', interface, 'scan'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            current_network = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                # New cell (network)
                cell_match = re.match(r'Cell\s+\d+\s+-\s+Address:\s*([0-9a-fA-F:]{17})', line)
                if cell_match:
                    if current_network:
                        networks.append(current_network)
                    current_network = {
                        'bssid': cell_match.group(1).upper(),
                        'ssid': None,
                        'frequency': None,
                        'channel': None,
                        'signal_dbm': None,
                        'signal_quality': None,
                        'security': 'Open',
                        'encryption': []
                    }
                    continue
                
                if current_network is None:
                    continue
                
                # ESSID (SSID)
                essid_match = re.match(r'ESSID:"(.*)"', line)
                if essid_match:
                    ssid = essid_match.group(1)
                    current_network['ssid'] = ssid if ssid else '<hidden>'
                    continue
                
                # Channel
                channel_match = re.match(r'Channel:(\d+)', line)
                if channel_match:
                    channel = int(channel_match.group(1))
                    current_network['channel'] = channel
                    current_network['frequency'] = channel_to_freq(channel)
                    continue
                
                # Frequency
                freq_match = re.match(r'Frequency:(\d+\.?\d*)\s*GHz', line)
                if freq_match:
                    freq = int(float(freq_match.group(1)) * 1000)
                    current_network['frequency'] = freq
                    if not current_network['channel']:
                        current_network['channel'] = freq_to_channel(freq)
                    continue
                
                # Signal level
                signal_match = re.search(r'Signal level[=:]?\s*(-?\d+)\s*dBm', line)
                if signal_match:
                    signal = int(signal_match.group(1))
                    current_network['signal_dbm'] = signal
                    current_network['signal_quality'] = dbm_to_quality(signal)
                    continue
                
                # Quality
                quality_match = re.search(r'Quality[=:]?\s*(\d+)/(\d+)', line)
                if quality_match and not current_network['signal_quality']:
                    quality = int(int(quality_match.group(1)) / int(quality_match.group(2)) * 100)
                    current_network['signal_quality'] = quality
                    continue
                
                # Encryption
                enc_match = re.match(r'Encryption key:(on|off)', line)
                if enc_match:
                    if enc_match.group(1) == 'on':
                        current_network['security'] = 'Secured'
                    continue
                
                # IE type
                if 'WPA Version 1' in line:
                    current_network['encryption'].append('WPA')
                elif 'WPA2' in line or 'IEEE 802.11i/WPA2' in line:
                    current_network['encryption'].append('WPA2')
                elif 'WEP' in line:
                    current_network['encryption'].append('WEP')
            
            # Add last network
            if current_network:
                networks.append(current_network)
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return networks


def scan_wifi_networks_termux() -> List[Dict[str, Any]]:
    """
    Scan for WiFi networks using Termux-API (Android specific).
    
    Returns:
        List of discovered networks
    """
    networks = []
    
    try:
        result = subprocess.run(
            ['termux-wifi-scaninfo'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                for net in data:
                    networks.append({
                        'bssid': net.get('bssid', '').upper(),
                        'ssid': net.get('ssid') or '<hidden>',
                        'frequency': net.get('frequency_mhz'),
                        'channel': freq_to_channel(net.get('frequency_mhz', 0)),
                        'signal_dbm': net.get('rssi'),
                        'signal_quality': dbm_to_quality(net.get('rssi', -100)),
                        'security': 'Secured' if net.get('capabilities') else 'Open',
                        'encryption': parse_capabilities(net.get('capabilities', ''))
                    })
            except json.JSONDecodeError:
                pass
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return networks


def freq_to_channel(freq: int) -> Optional[int]:
    """Convert frequency (MHz) to WiFi channel number."""
    if not freq:
        return None
    
    # 2.4 GHz band
    if 2412 <= freq <= 2484:
        if freq == 2484:
            return 14
        return (freq - 2407) // 5
    
    # 5 GHz band
    if 5180 <= freq <= 5825:
        return (freq - 5000) // 5
    
    return None


def channel_to_freq(channel: int) -> Optional[int]:
    """Convert WiFi channel to frequency (MHz)."""
    # 2.4 GHz band
    if 1 <= channel <= 13:
        return 2407 + channel * 5
    if channel == 14:
        return 2484
    
    # 5 GHz band
    if 36 <= channel <= 165:
        return 5000 + channel * 5
    
    return None


def dbm_to_quality(dbm: float) -> int:
    """Convert signal strength in dBm to quality percentage."""
    if not dbm:
        return 0
    
    # Typical range: -30 dBm (excellent) to -90 dBm (poor)
    if dbm >= -30:
        return 100
    if dbm <= -90:
        return 0
    
    # Linear interpolation
    return int(100 - ((-30 - dbm) / 60 * 100))


def parse_capabilities(capabilities: str) -> List[str]:
    """Parse WiFi capabilities string to get encryption types."""
    encryption = []
    
    if not capabilities:
        return encryption
    
    if 'WPA3' in capabilities:
        encryption.append('WPA3')
    if 'WPA2' in capabilities:
        encryption.append('WPA2')
    if 'WPA' in capabilities and 'WPA2' not in capabilities and 'WPA3' not in capabilities:
        encryption.append('WPA')
    if 'WEP' in capabilities:
        encryption.append('WEP')
    
    return encryption


def run_wifi_scan(output_dir: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Run a complete WiFi scan.
    
    Args:
        output_dir: Directory to save results
        verbose: Print verbose output
    
    Returns:
        Scan results dictionary
    """
    builder = ScanResultBuilder("wifi")
    
    if verbose:
        print("=" * 60)
        print("WiFi Scanner")
        print("=" * 60)
    
    # Get wireless interfaces
    if verbose:
        print("\n[*] Detecting wireless interfaces...")
    interfaces = get_wireless_interfaces()
    builder.add_metadata("interfaces", interfaces)
    
    if not interfaces:
        msg = "No wireless interfaces found"
        if verbose:
            print(f"[!] {msg}")
        builder.add_warning(msg)
        
        # Try Termux API as fallback
        if verbose:
            print("[*] Trying Termux-API...")
        networks = scan_wifi_networks_termux()
        if networks:
            for net in networks:
                builder.add_item(net)
            if verbose:
                print(f"[+] Found {len(networks)} networks via Termux-API")
    else:
        if verbose:
            print(f"    Found interfaces: {', '.join(interfaces)}")
        
        all_networks = []
        seen_bssids = set()
        
        for interface in interfaces:
            if verbose:
                print(f"\n[*] Scanning on {interface}...")
            
            # Get current connection
            current = get_current_connection(interface)
            if current:
                builder.add_metadata(f"current_connection_{interface}", current)
                if verbose:
                    print(f"    Currently connected to: {current.get('ssid', 'unknown')}")
            
            # Scan for networks (try iw first, then iwlist)
            networks = scan_wifi_networks_iw(interface)
            
            if not networks:
                networks = scan_wifi_networks_iwlist(interface)
            
            if not networks:
                # Try Termux API
                networks = scan_wifi_networks_termux()
            
            # Add unique networks
            for net in networks:
                bssid = net.get('bssid')
                if bssid and bssid not in seen_bssids:
                    seen_bssids.add(bssid)
                    all_networks.append(net)
        
        # Sort by signal strength
        all_networks.sort(key=lambda x: x.get('signal_dbm') or -100, reverse=True)
        
        for net in all_networks:
            builder.add_item(net)
        
        if verbose:
            print(f"\n[+] Discovered {len(all_networks)} WiFi networks")
            if all_networks:
                print("\n    Top networks by signal strength:")
                for net in all_networks[:5]:
                    ssid = net.get('ssid', '<unknown>')[:20]
                    signal = net.get('signal_dbm', 'N/A')
                    channel = net.get('channel', 'N/A')
                    security = net.get('security', 'Unknown')
                    print(f"      {ssid:<20} Ch:{channel:<3} {signal}dBm {security}")
    
    # Build and save results
    result = builder.build()
    
    if output_dir:
        filepath = builder.save(output_dir)
        if verbose:
            print(f"\n[+] Results saved to: {filepath}")
    
    return result


def main():
    """Main entry point for WiFi scanner."""
    parser = argparse.ArgumentParser(
        description="WiFi Scanner - Discover nearby wireless networks"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for scan results"
    )
    parser.add_argument(
        "--interface", "-i",
        help="Specific wireless interface to use"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Verbose output (default: True)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Quiet mode - suppress verbose output"
    )
    
    args = parser.parse_args()
    
    verbose = args.verbose and not args.quiet
    
    result = run_wifi_scan(
        output_dir=args.output,
        verbose=verbose
    )
    
    if args.json:
        print_json(result)


if __name__ == "__main__":
    main()
