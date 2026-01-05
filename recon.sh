#!/bin/bash
# ============================================================================
# Linux Recon - Main CLI Entry Point
# ============================================================================
# Clean-room, open-source reconnaissance radar for Linux
# 
# Usage:
#   ./recon.sh [command] [options]
#
# Commands:
#   scan <type>     - Run a scanner (network, wifi, bt, all)
#   radar           - Launch real-time radar terminal UI
#   web             - Start localhost web dashboard
#   export <format> - Export scan results (json, csv)
#   config          - Show/edit configuration
#   help            - Show this help message
# ============================================================================

set -e

# Get script directory (resolve symlinks)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && pwd)"

# Source configuration
CONFIG_FILE="${CONFIG_FILE:-$SCRIPT_DIR/config/default.json}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m'

# Version
VERSION="1.0.0"

# Banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║    ██╗     ██╗███╗   ██╗██╗   ██╗██╗  ██╗                    ║"
    echo "║    ██║     ██║████╗  ██║██║   ██║╚██╗██╔╝                    ║"
    echo "║    ██║     ██║██╔██╗ ██║██║   ██║ ╚███╔╝                     ║"
    echo "║    ██║     ██║██║╚██╗██║██║   ██║ ██╔██╗                     ║"
    echo "║    ███████╗██║██║ ╚████║╚██████╔╝██╔╝ ██╗                    ║"
    echo "║    ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝                    ║"
    echo "║                                                              ║"
    echo "║            ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗      ║"
    echo "║            ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║      ║"
    echo "║            ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║      ║"
    echo "║            ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║      ║"
    echo "║            ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║      ║"
    echo "║            ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝      ║"
    echo "║                                                              ║"
    echo "║              Clean-Room Open-Source Recon Radar              ║"
    echo "║                       Version ${VERSION}                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Help message
show_help() {
    show_banner
    echo -e "${WHITE}USAGE:${NC}"
    echo "  ./recon.sh [command] [options]"
    echo ""
    echo -e "${WHITE}COMMANDS:${NC}"
    echo -e "  ${GREEN}scan${NC} <type>       Run a scanner module"
    echo "                    Types: network, wifi, bt (bluetooth), all"
    echo ""
    echo -e "  ${GREEN}radar${NC}             Launch real-time radar terminal UI"
    echo ""
    echo -e "  ${GREEN}web${NC}               Start localhost web dashboard"
    echo "                    Options: --port <port>, --host <host>"
    echo ""
    echo -e "  ${GREEN}export${NC} <format>   Export latest scan results"
    echo "                    Formats: json, csv"
    echo ""
    echo -e "  ${GREEN}config${NC}            Show current configuration"
    echo "                    Options: --edit (open in editor)"
    echo ""
    echo -e "  ${GREEN}status${NC}            Show system status and capabilities"
    echo ""
    echo -e "  ${GREEN}help${NC}              Show this help message"
    echo ""
    echo -e "${WHITE}EXAMPLES:${NC}"
    echo "  ./recon.sh scan network      # Scan local network"
    echo "  ./recon.sh scan wifi         # Scan WiFi networks"
    echo "  ./recon.sh scan bt           # Scan Bluetooth devices"
    echo "  ./recon.sh scan all          # Run all scanners"
    echo "  ./recon.sh radar             # Launch radar UI"
    echo "  ./recon.sh web --port 9000   # Start web UI on port 9000"
    echo ""
    echo -e "${WHITE}OUTPUT:${NC}"
    echo "  All scan results are saved as JSON in: ${OUTPUT_DIR}/"
    echo ""
    echo -e "${YELLOW}NOTE:${NC} Some features require root access or specific permissions."
    echo ""
}

# Print status messages
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

# Get Python command
get_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        print_error "Python not found. Please run install.sh first."
        exit 1
    fi
}

# Ensure output directory exists
ensure_output_dir() {
    mkdir -p "$OUTPUT_DIR"
}

# Run network scanner
scan_network() {
    print_status "Starting network scanner..."
    ensure_output_dir
    PYTHON=$(get_python)
    $PYTHON "$SCRIPT_DIR/scanners/network_scanner.py" --output "$OUTPUT_DIR" "$@"
}

# Run WiFi scanner
scan_wifi() {
    print_status "Starting WiFi scanner..."
    ensure_output_dir
    PYTHON=$(get_python)
    $PYTHON "$SCRIPT_DIR/scanners/wifi_scanner.py" --output "$OUTPUT_DIR" "$@"
}

# Run Bluetooth scanner
scan_bluetooth() {
    print_status "Starting Bluetooth scanner..."
    ensure_output_dir
    PYTHON=$(get_python)
    $PYTHON "$SCRIPT_DIR/scanners/bluetooth_scanner.py" --output "$OUTPUT_DIR" "$@"
}

# Run all scanners
scan_all() {
    print_status "Running all scanners..."
    ensure_output_dir
    
    echo ""
    echo -e "${CYAN}=== Network Scan ===${NC}"
    scan_network "$@" || print_warning "Network scan encountered issues"
    
    echo ""
    echo -e "${CYAN}=== WiFi Scan ===${NC}"
    scan_wifi "$@" || print_warning "WiFi scan encountered issues"
    
    echo ""
    echo -e "${CYAN}=== Bluetooth Scan ===${NC}"
    scan_bluetooth "$@" || print_warning "Bluetooth scan encountered issues"
    
    echo ""
    print_success "All scans complete. Results saved to: $OUTPUT_DIR/"
}

# Launch radar UI
launch_radar() {
    print_status "Launching radar UI..."
    ensure_output_dir
    PYTHON=$(get_python)
    $PYTHON "$SCRIPT_DIR/ui/radar_ui.py" --output "$OUTPUT_DIR" "$@"
}

# Start web dashboard
start_web() {
    print_status "Starting web dashboard..."
    ensure_output_dir
    PYTHON=$(get_python)
    
    # Parse web options
    HOST="127.0.0.1"
    PORT="8080"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --port)
                PORT="$2"
                shift 2
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo -e "${GREEN}Web dashboard starting at: http://${HOST}:${PORT}${NC}"
    $PYTHON "$SCRIPT_DIR/web/server.py" --host "$HOST" --port "$PORT" --output "$OUTPUT_DIR"
}

# Export scan results
export_results() {
    FORMAT="${1:-json}"
    print_status "Exporting results as ${FORMAT}..."
    PYTHON=$(get_python)
    $PYTHON "$SCRIPT_DIR/lib/exporter.py" --format "$FORMAT" --output "$OUTPUT_DIR"
}

# Show configuration
show_config() {
    if [[ "$1" == "--edit" ]]; then
        EDITOR="${EDITOR:-nano}"
        $EDITOR "$CONFIG_FILE"
    else
        echo -e "${WHITE}Current Configuration:${NC}"
        echo "Config file: $CONFIG_FILE"
        echo ""
        if [ -f "$CONFIG_FILE" ]; then
            cat "$CONFIG_FILE"
        else
            print_warning "Config file not found. Using defaults."
        fi
    fi
}

# Show system status
show_status() {
    show_banner
    echo -e "${WHITE}System Status:${NC}"
    echo ""
    
    # Python check
    PYTHON=$(get_python 2>/dev/null) && print_success "Python: $($PYTHON --version)" || print_error "Python: Not found"
    
    # Check for root
    if [ "$EUID" -eq 0 ] || [ "$(id -u)" -eq 0 ]; then
        print_success "Root access: Available"
    else
        print_warning "Root access: Not available (some features limited)"
    fi
    
    # Environment detection
    if [ -d "/data/data/com.termux" ] || [ -n "$TERMUX_VERSION" ]; then
        print_status "Environment: Android Termux"
    elif [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        print_status "Environment: ${NAME:-Linux} ${VERSION_ID:-}"
    else
        print_status "Environment: Linux"
    fi
    
    # Network tools
    command -v ip &> /dev/null && print_success "ip command: Available" || print_warning "ip command: Not found"
    command -v ping &> /dev/null && print_success "ping command: Available" || print_warning "ping command: Not found"
    command -v iwlist &> /dev/null && print_success "iwlist command: Available" || print_warning "iwlist command: Not found"
    command -v iw &> /dev/null && print_success "iw command: Available" || print_warning "iw command: Not found"
    command -v hcitool &> /dev/null && print_success "hcitool command: Available" || print_warning "hcitool command: Not found"
    
    # Python modules
    echo ""
    echo -e "${WHITE}Python Modules:${NC}"
    PYTHON=$(get_python)
    $PYTHON -c "import flask; print('[+] flask: ' + flask.__version__)" 2>/dev/null || print_warning "flask: Not installed"
    $PYTHON -c "import psutil; print('[+] psutil: ' + psutil.version_info.__str__())" 2>/dev/null || print_warning "psutil: Not installed"
    $PYTHON -c "import netifaces; print('[+] netifaces: Available')" 2>/dev/null || print_warning "netifaces: Not installed"
    
    # Output directory
    echo ""
    if [ -d "$OUTPUT_DIR" ]; then
        print_success "Output directory: $OUTPUT_DIR"
        SCAN_COUNT=$(ls -1 "$OUTPUT_DIR"/*.json 2>/dev/null | wc -l)
        echo "  Scan results: $SCAN_COUNT file(s)"
    else
        print_status "Output directory: $OUTPUT_DIR (will be created)"
    fi
}

# Interactive menu
interactive_menu() {
    show_banner
    
    while true; do
        echo ""
        echo -e "${WHITE}Select an option:${NC}"
        echo -e "  ${GREEN}1)${NC} Scan Network"
        echo -e "  ${GREEN}2)${NC} Scan WiFi"
        echo -e "  ${GREEN}3)${NC} Scan Bluetooth"
        echo -e "  ${GREEN}4)${NC} Scan All"
        echo -e "  ${GREEN}5)${NC} Launch Radar UI"
        echo -e "  ${GREEN}6)${NC} Start Web Dashboard"
        echo -e "  ${GREEN}7)${NC} Show Status"
        echo -e "  ${GREEN}8)${NC} Show Config"
        echo -e "  ${GREEN}9)${NC} Help"
        echo -e "  ${GREEN}0)${NC} Exit"
        echo ""
        read -p "Enter choice [0-9]: " choice
        
        case $choice in
            1) scan_network ;;
            2) scan_wifi ;;
            3) scan_bluetooth ;;
            4) scan_all ;;
            5) launch_radar ;;
            6) start_web ;;
            7) show_status ;;
            8) show_config ;;
            9) show_help ;;
            0) 
                print_status "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please enter 0-9."
                ;;
        esac
    done
}

# Main command parser
main() {
    # If no arguments, show interactive menu
    if [ $# -eq 0 ]; then
        interactive_menu
        exit 0
    fi
    
    COMMAND="$1"
    shift
    
    case "$COMMAND" in
        scan)
            SCAN_TYPE="${1:-all}"
            shift 2>/dev/null || true
            case "$SCAN_TYPE" in
                network|net) scan_network "$@" ;;
                wifi|wlan) scan_wifi "$@" ;;
                bt|bluetooth) scan_bluetooth "$@" ;;
                all) scan_all "$@" ;;
                *)
                    print_error "Unknown scan type: $SCAN_TYPE"
                    echo "Valid types: network, wifi, bt, all"
                    exit 1
                    ;;
            esac
            ;;
        radar)
            launch_radar "$@"
            ;;
        web)
            start_web "$@"
            ;;
        export)
            export_results "$@"
            ;;
        config)
            show_config "$@"
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        version|--version|-v)
            echo "Linux Recon v${VERSION}"
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            echo "Run './recon.sh help' for usage information."
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"
