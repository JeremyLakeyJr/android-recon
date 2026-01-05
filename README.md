# Linux Recon

<div align="center">

```
╔══════════════════════════════════════════════════════════════╗
║    ██╗     ██╗███╗   ██╗██╗   ██╗██╗  ██╗                    ║
║    ██║     ██║████╗  ██║██║   ██║╚██╗██╔╝                    ║
║    ██║     ██║██╔██╗ ██║██║   ██║ ╚███╔╝                     ║
║    ██║     ██║██║╚██╗██║██║   ██║ ██╔██╗                     ║
║    ███████╗██║██║ ╚████║╚██████╔╝██╔╝ ██╗                    ║
║    ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝                    ║
║                                                              ║
║            ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗      ║
║            ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║      ║
║            ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║      ║
║            ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║      ║
║            ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║      ║
║            ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝      ║
╚══════════════════════════════════════════════════════════════╝
```

**Clean-Room Open-Source Reconnaissance Radar for Linux**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux-green.svg)](https://www.linux.org/)
[![Python](https://img.shields.io/badge/Python-3.7+-yellow.svg)](https://python.org/)

</div>

## Overview

Linux Recon is a clean-room, open-source reconnaissance radar tool designed for all Linux environments. It provides modular network, WiFi, and Bluetooth scanning capabilities with a radar-style terminal UI and optional web dashboard.

### Supported Platforms

- **Debian/Ubuntu** and derivatives
- **Fedora/RHEL/CentOS** and derivatives
- **Arch Linux** and derivatives
- **Android Termux**
- **Other Linux distributions** (with manual dependency installation)

### Key Features

- 🔍 **Modular Scanners**: Network, WiFi, and Bluetooth discovery
- 📊 **JSON Output**: Standardized, machine-readable results
- 🎯 **Radar UI**: Real-time terminal visualization
- 🌐 **Web Dashboard**: Optional localhost browser interface
- 💻 **CLI-First**: Full command-line control
- 📖 **Fully Explainable**: Clean architecture, no proprietary code

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/JeremyLakeyJr/android-recon.git
cd android-recon

# Run the installer
bash install.sh

# Launch Android Recon
./recon.sh
```

### Basic Usage

```bash
# Interactive menu
./recon.sh

# Run specific scans
./recon.sh scan network    # Scan local network
./recon.sh scan wifi       # Scan WiFi networks
./recon.sh scan bt         # Scan Bluetooth devices
./recon.sh scan all        # Run all scanners

# Launch radar UI
./recon.sh radar

# Start web dashboard
./recon.sh web --port 8080
```

## Architecture

### Project Structure

```
android-recon/
├── recon.sh              # Main CLI entry point
├── install.sh            # Auto-installation script
├── requirements.txt      # Python dependencies
├── config/
│   └── default.json      # Default configuration
├── scanners/
│   ├── __init__.py
│   ├── network_scanner.py   # Network host discovery
│   ├── wifi_scanner.py      # WiFi network scanning
│   └── bluetooth_scanner.py # Bluetooth device scanning
├── lib/
│   ├── __init__.py
│   ├── json_utils.py     # JSON output utilities
│   └── exporter.py       # Export functionality
├── ui/
│   ├── __init__.py
│   └── radar_ui.py       # Terminal radar visualization
├── web/
│   ├── __init__.py
│   └── server.py         # Web dashboard server
└── output/               # Scan results directory
```

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         recon.sh                                │
│                    (Main CLI Entry Point)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Scanners    │   │      UI       │   │     Web       │
├───────────────┤   ├───────────────┤   ├───────────────┤
│ • Network     │   │ • Radar UI    │   │ • Dashboard   │
│ • WiFi        │   │   (curses)    │   │   (Flask)     │
│ • Bluetooth   │   │               │   │ • REST API    │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    lib/json_utils   │
                 │  (JSON Utilities)   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   output/*.json     │
                 │  (Scan Results)     │
                 └─────────────────────┘
```

### Data Flow

1. **Input**: User runs a scan command via CLI
2. **Scanning**: Appropriate scanner module executes
3. **Processing**: Results are structured using `ScanResultBuilder`
4. **Output**: JSON files are saved to `output/` directory
5. **Visualization**: UI components read JSON and display results

### JSON Output Format

All scanners produce standardized JSON output:

```json
{
    "scan_type": "network|wifi|bluetooth",
    "timestamp": "2024-01-01T12:00:00.000000",
    "version": "1.0.0",
    "count": 5,
    "data": [
        {
            // Device-specific fields
        }
    ],
    "metadata": {
        // Scanner-specific metadata
    }
}
```

## Scanner Modules

### Network Scanner

Discovers hosts on the local network using:
- Interface enumeration
- ARP table parsing
- Ping sweep
- Optional port scanning

```bash
./recon.sh scan network
./recon.sh scan network --ports  # Enable port scanning
```

**Output Fields:**
- `ip`: IP address
- `mac`: MAC address
- `hostname`: Resolved hostname
- `alive`: Whether host responded
- `latency_ms`: Response time
- `open_ports`: List of open ports (if enabled)

### WiFi Scanner

Discovers nearby wireless networks using:
- `iw` command (primary)
- `iwlist` command (fallback)
- Termux-API (Android fallback)

```bash
./recon.sh scan wifi
```

**Output Fields:**
- `ssid`: Network name
- `bssid`: Access point MAC
- `frequency`: Channel frequency (MHz)
- `channel`: WiFi channel number
- `signal_dbm`: Signal strength
- `signal_quality`: Quality percentage
- `security`: Open/Secured
- `encryption`: WPA, WPA2, WEP, etc.

### Bluetooth Scanner

Discovers Bluetooth devices (Classic and BLE) using:
- `hcitool` (primary)
- Termux-API (Android fallback)

```bash
./recon.sh scan bt
./recon.sh scan bt --duration 20  # Longer scan
./recon.sh scan bt --no-ble       # Classic only
```

**Output Fields:**
- `address`: Device MAC address
- `name`: Device name
- `type`: Classic or BLE
- `device_class`: Bluetooth class code
- `device_type`: Human-readable type
- `rssi`: Signal strength (if available)

## User Interfaces

### Terminal Radar UI

Real-time radar-style visualization in the terminal:

```bash
./recon.sh radar
```

**Features:**
- Animated radar sweep
- Color-coded device types
- Device list with selection
- Detail panel for selected device
- Auto-refresh from scan results

**Controls:**
- `↑/↓`: Navigate device list
- `R`: Refresh data
- `Q`: Quit

### Web Dashboard

Browser-based interface for viewing scan results:

```bash
./recon.sh web                    # Default: localhost:8080
./recon.sh web --port 9000        # Custom port
./recon.sh web --host 0.0.0.0     # Allow external access
```

**Features:**
- Device cards with detailed info
- Type-based filtering
- Search functionality
- Export to JSON
- Auto-refresh

**API Endpoints:**
- `GET /`: Dashboard HTML
- `GET /api/devices`: All devices
- `GET /api/scan/<type>`: Devices by type
- `GET /api/export`: Export all data

## Configuration

Edit `config/default.json` to customize behavior:

```json
{
    "scanners": {
        "network": {
            "timeout": 5,
            "ping_count": 1,
            "port_scan_enabled": false
        },
        "wifi": {
            "scan_interval": 10
        },
        "bluetooth": {
            "scan_duration": 10,
            "scan_le": true
        }
    },
    "radar": {
        "refresh_rate": 1.0
    },
    "web": {
        "port": 8080
    }
}
```

## Requirements

### System Requirements

- **OS**: Linux (Debian/Ubuntu, Fedora, Arch, Termux, etc.)
- **Python**: 3.7+
- **Shell**: Bash

### Dependencies

**System Packages:**
- `python` / `python3`
- `pip`
- `wireless-tools` (iwlist, iwconfig)
- `iw`
- `bluez` (hcitool, hciconfig)

**Python Packages:**
- `flask` (web dashboard)
- `psutil` (system info)
- `netifaces` (network interfaces)

### Platform-Specific Notes

#### Debian/Ubuntu
```bash
sudo apt-get install python3 python3-pip wireless-tools iw bluez nmap
```

#### Fedora/RHEL
```bash
sudo dnf install python3 python3-pip wireless-tools iw bluez nmap
```

#### Arch Linux
```bash
sudo pacman -S python python-pip wireless_tools iw bluez nmap
```

#### Android Termux
For full functionality on Android Termux:
- Install Termux from F-Droid
- Install Termux-API addon
- Grant necessary permissions

```bash
pkg install termux-api python
termux-setup-storage
```

## Permissions

Some features require elevated permissions:

| Feature | Permission Needed |
|---------|------------------|
| Network scan | Usually none |
| WiFi scan | May require root for active scanning |
| Bluetooth scan | Bluetooth access, may require root |
| Port scanning | None |

On rooted devices, use `su` or `tsu`:
```bash
su -c "./recon.sh scan wifi"
```

## Security & Ethics

### Intended Use

This tool is designed for:
- Network administrators auditing their networks
- Security researchers analyzing their own systems
- Educational purposes for learning about network protocols
- Troubleshooting connectivity issues

### Legal Notice

- **Only scan networks and devices you own or have permission to scan**
- Unauthorized network scanning may violate laws in your jurisdiction
- Always obtain proper authorization before conducting security assessments
- The developers are not responsible for misuse of this tool

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

### Development Setup

```bash
git clone https://github.com/JeremyLakeyJr/android-recon.git
cd android-recon
pip install -r requirements.txt
```

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and modular

## Troubleshooting

### Common Issues

**"No wireless interfaces found"**
- Ensure wireless-tools/iw is installed
- On Android, use Termux-API for WiFi scanning
- Some interfaces may need to be brought up: `ip link set wlan0 up`

**"No Bluetooth adapters found"**
- Install bluez package
- Ensure Bluetooth is enabled
- May require root access on some systems

**"Permission denied"**
- Some scans require root access
- On Termux, try using `tsu` package
- Grant necessary Android permissions

**Web dashboard not loading**
- Ensure Flask is installed: `pip install flask`
- Check if port is in use
- Try a different port: `./recon.sh web --port 9000`

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the Linux community
- Inspired by classic network reconnaissance tools
- Uses only open-source, freely available components

---

<div align="center">

**Made with 💚 for the open-source community**

</div>
