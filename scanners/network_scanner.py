#!/usr/bin/env python3
"""
Linux Recon - Network Scanner Module
=====================================
Scans local network for hosts, open ports, and network information.
Outputs results in standardized JSON format.

Features:
- Local interface detection
- ARP table parsing
- Host discovery via ping sweep
- Basic port scanning (optional)
- Network statistics collection
"""

import argparse
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Add lib to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.json_utils import ScanResultBuilder, print_json


# Common service ports to check
COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]


def get_network_interfaces() -> List[Dict[str, Any]]:
    """
    Get all network interfaces and their IP addresses.
    
    Returns:
        List of interface dictionaries
    """
    interfaces = []
    
    try:
        # Try using 'ip' command (Linux/Termux)
        result = subprocess.run(
            ['ip', '-j', 'addr', 'show'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                for iface in data:
                    iface_info = {
                        'name': iface.get('ifname', 'unknown'),
                        'state': iface.get('operstate', 'unknown'),
                        'mac': None,
                        'ipv4': [],
                        'ipv6': []
                    }
                    
                    # Get MAC address
                    if 'address' in iface:
                        iface_info['mac'] = iface['address']
                    
                    # Get IP addresses
                    for addr_info in iface.get('addr_info', []):
                        if addr_info.get('family') == 'inet':
                            iface_info['ipv4'].append({
                                'address': addr_info.get('local'),
                                'prefix': addr_info.get('prefixlen'),
                                'broadcast': addr_info.get('broadcast')
                            })
                        elif addr_info.get('family') == 'inet6':
                            iface_info['ipv6'].append({
                                'address': addr_info.get('local'),
                                'prefix': addr_info.get('prefixlen')
                            })
                    
                    interfaces.append(iface_info)
                
                return interfaces
            except json.JSONDecodeError:
                pass
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback: Parse 'ip addr' text output
    try:
        result = subprocess.run(
            ['ip', 'addr', 'show'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            current_iface = None
            
            for line in result.stdout.split('\n'):
                # Interface line
                iface_match = re.match(r'^\d+:\s+(\S+):', line)
                if iface_match:
                    if current_iface:
                        interfaces.append(current_iface)
                    current_iface = {
                        'name': iface_match.group(1),
                        'state': 'unknown',
                        'mac': None,
                        'ipv4': [],
                        'ipv6': []
                    }
                    if 'state UP' in line:
                        current_iface['state'] = 'UP'
                    elif 'state DOWN' in line:
                        current_iface['state'] = 'DOWN'
                
                if current_iface:
                    # MAC address
                    mac_match = re.search(r'link/\S+\s+([0-9a-fA-F:]{17})', line)
                    if mac_match:
                        current_iface['mac'] = mac_match.group(1)
                    
                    # IPv4 address
                    ipv4_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', line)
                    if ipv4_match:
                        current_iface['ipv4'].append({
                            'address': ipv4_match.group(1),
                            'prefix': int(ipv4_match.group(2))
                        })
                    
                    # IPv6 address
                    ipv6_match = re.search(r'inet6\s+([0-9a-fA-F:]+)/(\d+)', line)
                    if ipv6_match:
                        current_iface['ipv6'].append({
                            'address': ipv6_match.group(1),
                            'prefix': int(ipv6_match.group(2))
                        })
            
            if current_iface:
                interfaces.append(current_iface)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return interfaces


def get_arp_table() -> List[Dict[str, str]]:
    """
    Get ARP table entries.
    
    Returns:
        List of ARP entries with IP and MAC addresses
    """
    arp_entries = []
    
    # Try 'ip neigh' command
    try:
        result = subprocess.run(
            ['ip', 'neigh', 'show'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 5:
                    ip_addr = parts[0]
                    mac_addr = None
                    state = None
                    
                    for i, part in enumerate(parts):
                        if part == 'lladdr' and i + 1 < len(parts):
                            mac_addr = parts[i + 1]
                        if part in ('REACHABLE', 'STALE', 'DELAY', 'PROBE', 'FAILED', 'PERMANENT'):
                            state = part
                    
                    if mac_addr:
                        arp_entries.append({
                            'ip': ip_addr,
                            'mac': mac_addr,
                            'state': state or 'unknown'
                        })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Fallback to /proc/net/arp
    try:
        with open('/proc/net/arp', 'r') as f:
            lines = f.readlines()[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    ip_addr = parts[0]
                    mac_addr = parts[3]
                    if mac_addr != '00:00:00:00:00:00':
                        arp_entries.append({
                            'ip': ip_addr,
                            'mac': mac_addr,
                            'state': 'ARP'
                        })
    except (IOError, IndexError):
        pass
    
    return arp_entries


def get_default_gateway() -> Optional[Dict[str, str]]:
    """
    Get the default gateway.
    
    Returns:
        Gateway info dictionary or None
    """
    try:
        result = subprocess.run(
            ['ip', 'route', 'show', 'default'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split()
            if len(parts) >= 3 and parts[0] == 'default':
                gateway_ip = parts[2]
                interface = None
                for i, part in enumerate(parts):
                    if part == 'dev' and i + 1 < len(parts):
                        interface = parts[i + 1]
                        break
                
                return {
                    'ip': gateway_ip,
                    'interface': interface
                }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return None


def ping_host(ip: str, timeout: int = 1, count: int = 1) -> Tuple[str, bool, Optional[float]]:
    """
    Ping a single host.
    
    Args:
        ip: IP address to ping
        timeout: Timeout in seconds
        count: Number of ping packets
    
    Returns:
        Tuple of (ip, is_alive, latency_ms)
    """
    try:
        result = subprocess.run(
            ['ping', '-c', str(count), '-W', str(timeout), ip],
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        
        if result.returncode == 0:
            # Extract latency
            latency_match = re.search(r'time=(\d+\.?\d*)\s*ms', result.stdout)
            latency = float(latency_match.group(1)) if latency_match else None
            return (ip, True, latency)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return (ip, False, None)


def scan_port(ip: str, port: int, timeout: float = 1.0) -> Tuple[int, bool]:
    """
    Check if a specific port is open.
    
    Args:
        ip: Target IP address
        port: Port number to check
        timeout: Connection timeout
    
    Returns:
        Tuple of (port, is_open)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return (port, result == 0)
    except (socket.error, OSError):
        return (port, False)


def get_hostname(ip: str) -> Optional[str]:
    """
    Try to resolve hostname from IP address.
    
    Args:
        ip: IP address to resolve
    
    Returns:
        Hostname or None
    """
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except (socket.herror, socket.gaierror):
        return None


def discover_hosts(network: str, timeout: int = 1, max_workers: int = 50) -> List[Dict[str, Any]]:
    """
    Discover live hosts on a network using ping sweep.
    
    Args:
        network: Network in CIDR notation (e.g., '192.168.1.0/24')
        timeout: Ping timeout in seconds
        max_workers: Maximum concurrent ping operations
    
    Returns:
        List of discovered hosts
    """
    hosts = []
    
    try:
        net = ipaddress.ip_network(network, strict=False)
    except ValueError as e:
        print(f"Invalid network: {e}", file=sys.stderr)
        return hosts
    
    # Limit to /24 or smaller to avoid long scans
    if net.num_addresses > 256:
        print(f"Network too large ({net.num_addresses} addresses). Limiting to first 256.", 
              file=sys.stderr)
        net = ipaddress.ip_network(f"{net.network_address}/24", strict=False)
    
    ip_list = [str(ip) for ip in net.hosts()]
    
    print(f"Scanning {len(ip_list)} hosts in {network}...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ip = {executor.submit(ping_host, ip, timeout): ip for ip in ip_list}
        
        for future in as_completed(future_to_ip):
            ip, is_alive, latency = future.result()
            if is_alive:
                hostname = get_hostname(ip)
                hosts.append({
                    'ip': ip,
                    'alive': True,
                    'latency_ms': latency,
                    'hostname': hostname
                })
    
    return sorted(hosts, key=lambda x: ipaddress.ip_address(x['ip']))


def scan_host_ports(ip: str, ports: List[int] = None, timeout: float = 1.0) -> List[Dict[str, Any]]:
    """
    Scan ports on a specific host.
    
    Args:
        ip: Target IP address
        ports: List of ports to scan (default: common ports)
        timeout: Connection timeout
    
    Returns:
        List of open ports
    """
    if ports is None:
        ports = COMMON_PORTS
    
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_port = {executor.submit(scan_port, ip, port, timeout): port for port in ports}
        
        for future in as_completed(future_to_port):
            port, is_open = future.result()
            if is_open:
                service = get_service_name(port)
                open_ports.append({
                    'port': port,
                    'service': service,
                    'protocol': 'tcp'
                })
    
    return sorted(open_ports, key=lambda x: x['port'])


def get_service_name(port: int) -> str:
    """Get common service name for a port."""
    services = {
        21: 'ftp',
        22: 'ssh',
        23: 'telnet',
        25: 'smtp',
        53: 'dns',
        80: 'http',
        110: 'pop3',
        143: 'imap',
        443: 'https',
        445: 'smb',
        993: 'imaps',
        995: 'pop3s',
        3306: 'mysql',
        3389: 'rdp',
        5432: 'postgresql',
        8080: 'http-alt',
        8443: 'https-alt'
    }
    return services.get(port, 'unknown')


def get_network_stats() -> Dict[str, Any]:
    """
    Get network statistics.
    
    Returns:
        Dictionary with network statistics
    """
    stats = {}
    
    # Try to get connection stats
    try:
        result = subprocess.run(
            ['ss', '-s'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            stats['socket_stats'] = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    # Get DNS servers
    try:
        dns_servers = []
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    dns_servers.append(line.split()[1])
        stats['dns_servers'] = dns_servers
    except IOError:
        pass
    
    return stats


def run_network_scan(
    output_dir: str,
    port_scan: bool = False,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run a complete network scan.
    
    Args:
        output_dir: Directory to save results
        port_scan: Whether to scan ports on discovered hosts
        verbose: Print verbose output
    
    Returns:
        Scan results dictionary
    """
    builder = ScanResultBuilder("network")
    
    if verbose:
        print("=" * 60)
        print("Network Scanner")
        print("=" * 60)
    
    # Get network interfaces
    if verbose:
        print("\n[*] Detecting network interfaces...")
    interfaces = get_network_interfaces()
    builder.add_metadata("interfaces", interfaces)
    
    if verbose:
        for iface in interfaces:
            if iface.get('ipv4'):
                print(f"    {iface['name']}: {iface['ipv4'][0]['address']}")
    
    # Get default gateway
    if verbose:
        print("\n[*] Finding default gateway...")
    gateway = get_default_gateway()
    builder.add_metadata("gateway", gateway)
    
    if verbose and gateway:
        print(f"    Gateway: {gateway['ip']} via {gateway.get('interface', 'unknown')}")
    
    # Get ARP table
    if verbose:
        print("\n[*] Reading ARP table...")
    arp_table = get_arp_table()
    builder.add_metadata("arp_table", arp_table)
    
    if verbose:
        print(f"    Found {len(arp_table)} ARP entries")
    
    # Host discovery on each active interface
    discovered_hosts = []
    
    for iface in interfaces:
        if iface['state'] != 'UP':
            continue
        
        for ipv4_info in iface.get('ipv4', []):
            ip_addr = ipv4_info.get('address')
            prefix = ipv4_info.get('prefix', 24)
            
            if not ip_addr or ip_addr.startswith('127.'):
                continue
            
            network = f"{ip_addr}/{prefix}"
            
            if verbose:
                print(f"\n[*] Scanning network: {network}")
            
            hosts = discover_hosts(network)
            
            # Optionally scan ports on discovered hosts
            if port_scan:
                for host in hosts:
                    if verbose:
                        print(f"    Scanning ports on {host['ip']}...")
                    host['open_ports'] = scan_host_ports(host['ip'])
            
            discovered_hosts.extend(hosts)
    
    # Add discovered hosts to results
    for host in discovered_hosts:
        builder.add_item(host)
    
    if verbose:
        print(f"\n[+] Discovered {len(discovered_hosts)} live hosts")
    
    # Build and save results
    result = builder.build()
    
    if output_dir:
        filepath = builder.save(output_dir)
        if verbose:
            print(f"\n[+] Results saved to: {filepath}")
    
    return result


def main():
    """Main entry point for network scanner."""
    parser = argparse.ArgumentParser(
        description="Network Scanner - Discover hosts and services on local network"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for scan results"
    )
    parser.add_argument(
        "--ports", "-p",
        action="store_true",
        help="Enable port scanning on discovered hosts"
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
    
    result = run_network_scan(
        output_dir=args.output,
        port_scan=args.ports,
        verbose=verbose
    )
    
    if args.json:
        print_json(result)


if __name__ == "__main__":
    main()
