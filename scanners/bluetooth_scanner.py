#!/usr/bin/env python3
"""
Linux Recon - Bluetooth Scanner Module
=======================================
Scans for nearby Bluetooth devices including Classic and Low Energy (BLE).
Outputs results in standardized JSON format.

Features:
- Classic Bluetooth device discovery
- Bluetooth Low Energy (BLE) scanning
- Device name and MAC address collection
- Device class/type identification
- Signal strength (RSSI) measurement
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


# Bluetooth device class codes
BT_DEVICE_CLASSES = {
    # Major device classes
    0x0100: "Computer",
    0x0200: "Phone",
    0x0300: "LAN/Network",
    0x0400: "Audio/Video",
    0x0500: "Peripheral",
    0x0600: "Imaging",
    0x0700: "Wearable",
    0x0800: "Toy",
    0x0900: "Health",
    
    # Minor device classes - Phone
    0x0204: "Cellular",
    0x0208: "Cordless",
    0x020C: "Smartphone",
    0x0210: "Modem/Gateway",
    
    # Minor device classes - Audio/Video
    0x0404: "Headset",
    0x0408: "Hands-free",
    0x0414: "Microphone",
    0x0418: "Loudspeaker",
    0x041C: "Headphones",
    0x0420: "Portable Audio",
    0x0424: "Car Audio",
    0x0428: "Set-top Box",
    0x042C: "HiFi Audio",
    0x0430: "VCR",
    0x0434: "Video Camera",
    0x0438: "Camcorder",
    0x043C: "Video Monitor",
    0x0440: "Video Display and Loudspeaker",
    
    # Minor device classes - Peripheral
    0x0540: "Keyboard",
    0x0580: "Pointing Device",
    0x05C0: "Combo Keyboard/Pointing",
    
    # Minor device classes - Wearable
    0x0704: "Wristwatch",
    0x0708: "Pager",
    0x070C: "Jacket",
    0x0710: "Helmet",
    0x0714: "Glasses",
}


def get_bluetooth_adapters() -> List[Dict[str, Any]]:
    """
    Get list of Bluetooth adapters.
    
    Returns:
        List of adapter information
    """
    adapters = []
    
    # Try hciconfig
    try:
        result = subprocess.run(
            ['hciconfig', '-a'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            current_adapter = None
            
            for line in result.stdout.split('\n'):
                # New adapter
                adapter_match = re.match(r'^(hci\d+):', line)
                if adapter_match:
                    if current_adapter:
                        adapters.append(current_adapter)
                    current_adapter = {
                        'name': adapter_match.group(1),
                        'address': None,
                        'state': 'unknown'
                    }
                    if 'UP RUNNING' in line:
                        current_adapter['state'] = 'UP'
                    elif 'DOWN' in line:
                        current_adapter['state'] = 'DOWN'
                    continue
                
                if current_adapter:
                    # BD Address
                    addr_match = re.search(r'BD Address:\s*([0-9A-Fa-f:]{17})', line)
                    if addr_match:
                        current_adapter['address'] = addr_match.group(1).upper()
            
            if current_adapter:
                adapters.append(current_adapter)
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: check /sys
    if not adapters:
        try:
            bt_path = '/sys/class/bluetooth'
            if os.path.exists(bt_path):
                for adapter in os.listdir(bt_path):
                    adapters.append({
                        'name': adapter,
                        'address': None,
                        'state': 'unknown'
                    })
        except (IOError, OSError):
            pass
    
    return adapters


def bring_adapter_up(adapter: str) -> bool:
    """
    Bring a Bluetooth adapter up.
    
    Args:
        adapter: Adapter name (e.g., 'hci0')
    
    Returns:
        True if successful
    """
    try:
        result = subprocess.run(
            ['hciconfig', adapter, 'up'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def scan_classic_bluetooth(adapter: str = 'hci0', duration: int = 10) -> List[Dict[str, Any]]:
    """
    Scan for classic Bluetooth devices using hcitool.
    
    Args:
        adapter: Bluetooth adapter to use
        duration: Scan duration in seconds
    
    Returns:
        List of discovered devices
    """
    devices = []
    
    try:
        # Run inquiry scan
        result = subprocess.run(
            ['hcitool', '-i', adapter, 'scan', '--length', str(duration)],
            capture_output=True,
            text=True,
            timeout=duration + 10
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                # Parse device entries
                match = re.match(r'\s*([0-9A-Fa-f:]{17})\s+(.*)', line)
                if match:
                    addr = match.group(1).upper()
                    name = match.group(2).strip() or '<unknown>'
                    
                    device = {
                        'address': addr,
                        'name': name,
                        'type': 'Classic',
                        'rssi': None,
                        'device_class': None,
                        'device_type': None
                    }
                    
                    # Try to get device class
                    device_class = get_device_class(adapter, addr)
                    if device_class:
                        device['device_class'] = device_class
                        device['device_type'] = classify_device(device_class)
                    
                    devices.append(device)
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return devices


def scan_ble_devices(adapter: str = 'hci0', duration: int = 10) -> List[Dict[str, Any]]:
    """
    Scan for Bluetooth Low Energy (BLE) devices using hcitool.
    
    Args:
        adapter: Bluetooth adapter to use
        duration: Scan duration in seconds
    
    Returns:
        List of discovered BLE devices
    """
    devices = []
    seen_addresses = set()
    
    try:
        # Start LE scan
        process = subprocess.Popen(
            ['hcitool', '-i', adapter, 'lescan', '--duplicates'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        import time
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Parse BLE device entries
                match = re.match(r'([0-9A-Fa-f:]{17})\s+(.*)', line.strip())
                if match:
                    addr = match.group(1).upper()
                    name = match.group(2).strip()
                    
                    # Skip if we've seen this device
                    if addr in seen_addresses and name in ('(unknown)', ''):
                        continue
                    
                    seen_addresses.add(addr)
                    
                    device = {
                        'address': addr,
                        'name': name if name and name != '(unknown)' else '<unknown>',
                        'type': 'BLE',
                        'rssi': None,
                        'device_class': None,
                        'device_type': 'BLE Device'
                    }
                    
                    # Check if device already in list
                    existing = next((d for d in devices if d['address'] == addr), None)
                    if existing:
                        if device['name'] != '<unknown>' and existing['name'] == '<unknown>':
                            existing['name'] = device['name']
                    else:
                        devices.append(device)
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return devices


def scan_bluetooth_termux() -> List[Dict[str, Any]]:
    """
    Scan for Bluetooth devices using Termux-API.
    
    Returns:
        List of discovered devices
    """
    devices = []
    
    try:
        result = subprocess.run(
            ['termux-bluetooth-scaninfo'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                for dev in data:
                    devices.append({
                        'address': dev.get('address', '').upper(),
                        'name': dev.get('name') or '<unknown>',
                        'type': dev.get('type', 'Unknown'),
                        'rssi': dev.get('rssi'),
                        'device_class': dev.get('class'),
                        'device_type': dev.get('device_type', 'Unknown')
                    })
            except json.JSONDecodeError:
                pass
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return devices


def get_device_class(adapter: str, address: str) -> Optional[int]:
    """
    Get device class for a Bluetooth device.
    
    Args:
        adapter: Bluetooth adapter
        address: Device MAC address
    
    Returns:
        Device class code or None
    """
    try:
        result = subprocess.run(
            ['hcitool', '-i', adapter, 'info', address],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            match = re.search(r'Device Class:\s*0x([0-9a-fA-F]+)', result.stdout)
            if match:
                return int(match.group(1), 16)
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return None


def classify_device(device_class: int) -> str:
    """
    Get human-readable device type from class code.
    
    Args:
        device_class: Bluetooth device class code
    
    Returns:
        Device type description
    """
    if not device_class:
        return "Unknown"
    
    # Check specific minor classes first
    for code, name in BT_DEVICE_CLASSES.items():
        if device_class & 0x0FFC == code:
            return name
    
    # Fall back to major class
    major_class = device_class & 0x1F00
    return BT_DEVICE_CLASSES.get(major_class, "Unknown")


def run_bluetooth_scan(
    output_dir: str,
    duration: int = 10,
    scan_ble: bool = True,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a complete Bluetooth scan.
    
    Args:
        output_dir: Directory to save results
        duration: Scan duration in seconds
        scan_ble: Whether to scan for BLE devices
        verbose: Print verbose output
    
    Returns:
        Scan results dictionary
    """
    builder = ScanResultBuilder("bluetooth")
    
    if verbose:
        print("=" * 60)
        print("Bluetooth Scanner")
        print("=" * 60)
    
    # Get Bluetooth adapters
    if verbose:
        print("\n[*] Detecting Bluetooth adapters...")
    adapters = get_bluetooth_adapters()
    builder.add_metadata("adapters", adapters)
    
    if not adapters:
        msg = "No Bluetooth adapters found"
        if verbose:
            print(f"[!] {msg}")
        builder.add_warning(msg)
        
        # Try Termux API
        if verbose:
            print("[*] Trying Termux-API...")
        devices = scan_bluetooth_termux()
        if devices:
            for dev in devices:
                builder.add_item(dev)
            if verbose:
                print(f"[+] Found {len(devices)} devices via Termux-API")
    else:
        if verbose:
            for adapter in adapters:
                state = adapter.get('state', 'unknown')
                addr = adapter.get('address', 'unknown')
                print(f"    {adapter['name']}: {addr} ({state})")
        
        all_devices = []
        seen_addresses = set()
        
        for adapter in adapters:
            adapter_name = adapter['name']
            
            # Try to bring adapter up if needed
            if adapter.get('state') != 'UP':
                if verbose:
                    print(f"\n[*] Bringing up {adapter_name}...")
                bring_adapter_up(adapter_name)
            
            # Scan for classic Bluetooth devices
            if verbose:
                print(f"\n[*] Scanning for Classic Bluetooth devices on {adapter_name}...")
                print(f"    (This may take up to {duration} seconds)")
            
            classic_devices = scan_classic_bluetooth(adapter_name, duration)
            
            for dev in classic_devices:
                addr = dev.get('address')
                if addr and addr not in seen_addresses:
                    seen_addresses.add(addr)
                    all_devices.append(dev)
            
            if verbose:
                print(f"    Found {len(classic_devices)} classic devices")
            
            # Scan for BLE devices
            if scan_ble:
                if verbose:
                    print(f"\n[*] Scanning for BLE devices on {adapter_name}...")
                
                ble_devices = scan_ble_devices(adapter_name, duration)
                
                for dev in ble_devices:
                    addr = dev.get('address')
                    if addr and addr not in seen_addresses:
                        seen_addresses.add(addr)
                        all_devices.append(dev)
                
                if verbose:
                    print(f"    Found {len(ble_devices)} BLE devices")
        
        # If no devices found with hcitool, try Termux API
        if not all_devices:
            termux_devices = scan_bluetooth_termux()
            for dev in termux_devices:
                addr = dev.get('address')
                if addr and addr not in seen_addresses:
                    seen_addresses.add(addr)
                    all_devices.append(dev)
        
        # Add devices to results
        for dev in all_devices:
            builder.add_item(dev)
        
        if verbose:
            print(f"\n[+] Discovered {len(all_devices)} Bluetooth devices total")
            if all_devices:
                print("\n    Discovered devices:")
                for dev in all_devices:
                    name = dev.get('name', '<unknown>')[:20]
                    addr = dev.get('address', 'unknown')
                    dev_type = dev.get('type', 'Unknown')
                    device_type = dev.get('device_type', '')
                    print(f"      {name:<20} {addr} [{dev_type}] {device_type}")
    
    # Build and save results
    result = builder.build()
    
    if output_dir:
        filepath = builder.save(output_dir)
        if verbose:
            print(f"\n[+] Results saved to: {filepath}")
    
    return result


def main():
    """Main entry point for Bluetooth scanner."""
    parser = argparse.ArgumentParser(
        description="Bluetooth Scanner - Discover nearby Bluetooth devices"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for scan results"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=10,
        help="Scan duration in seconds (default: 10)"
    )
    parser.add_argument(
        "--no-ble",
        action="store_true",
        help="Skip BLE scanning"
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
    
    result = run_bluetooth_scan(
        output_dir=args.output,
        duration=args.duration,
        scan_ble=not args.no_ble,
        verbose=verbose
    )
    
    if args.json:
        print_json(result)


if __name__ == "__main__":
    main()
