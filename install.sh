#!/bin/bash
# ============================================================================
# Linux Recon - Auto-Install Script
# ============================================================================
# This script automatically sets up all dependencies for the Linux Recon
# reconnaissance radar tool on any Linux distribution.
#
# Supported platforms:
#   - Debian/Ubuntu and derivatives
#   - Fedora/RHEL/CentOS and derivatives
#   - Arch Linux and derivatives
#   - Android Termux
#   - Other Linux distributions (manual dependency installation)
#
# Usage: bash install.sh
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              LINUX RECON - Installation Script                ║"
echo "║         Clean-Room Open-Source Reconnaissance Radar           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print status messages
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

# Detect environment (Termux vs standard Linux)
detect_environment() {
    if [ -d "/data/data/com.termux" ] || [ -n "$TERMUX_VERSION" ]; then
        ENVIRONMENT="termux"
        PKG_MANAGER="pkg"
        print_status "Detected Termux environment"
    elif command -v apt-get &> /dev/null; then
        ENVIRONMENT="debian"
        PKG_MANAGER="apt-get"
        print_status "Detected Debian/Ubuntu environment"
    elif command -v dnf &> /dev/null; then
        ENVIRONMENT="fedora"
        PKG_MANAGER="dnf"
        print_status "Detected Fedora/RHEL environment"
    elif command -v yum &> /dev/null; then
        ENVIRONMENT="rhel"
        PKG_MANAGER="yum"
        print_status "Detected RHEL/CentOS environment"
    elif command -v pacman &> /dev/null; then
        ENVIRONMENT="arch"
        PKG_MANAGER="pacman"
        print_status "Detected Arch Linux environment"
    elif command -v zypper &> /dev/null; then
        ENVIRONMENT="suse"
        PKG_MANAGER="zypper"
        print_status "Detected openSUSE environment"
    elif command -v apk &> /dev/null; then
        ENVIRONMENT="alpine"
        PKG_MANAGER="apk"
        print_status "Detected Alpine Linux environment"
    else
        ENVIRONMENT="unknown"
        PKG_MANAGER=""
        print_warning "Unknown environment - manual installation may be required"
    fi
}

# Update package manager
update_packages() {
    print_status "Updating package manager..."
    case $ENVIRONMENT in
        termux)
            pkg update -y
            ;;
        debian)
            sudo apt-get update -y
            ;;
        fedora)
            sudo dnf check-update || true
            ;;
        rhel)
            sudo yum check-update || true
            ;;
        arch)
            sudo pacman -Sy --noconfirm
            ;;
        suse)
            sudo zypper refresh
            ;;
        alpine)
            sudo apk update
            ;;
        *)
            print_warning "Skipping package update for unknown environment"
            ;;
    esac
    print_success "Package manager updated"
}

# Install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    
    case $ENVIRONMENT in
        termux)
            PACKAGES="python python-pip git curl wget termux-api wireless-tools iw root-repo tsu"
            pkg install -y $PACKAGES 2>/dev/null || {
                # Try installing packages one by one if bulk install fails
                for pkg in $PACKAGES; do
                    pkg install -y "$pkg" 2>/dev/null || print_warning "Could not install: $pkg"
                done
            }
            ;;
        debian)
            PACKAGES="python3 python3-pip git curl wget net-tools wireless-tools iw bluetooth bluez nmap"
            sudo apt-get install -y $PACKAGES 2>/dev/null || {
                for pkg in $PACKAGES; do
                    sudo apt-get install -y "$pkg" 2>/dev/null || print_warning "Could not install: $pkg"
                done
            }
            ;;
        fedora)
            PACKAGES="python3 python3-pip git curl wget net-tools wireless-tools iw bluez nmap"
            sudo dnf install -y $PACKAGES 2>/dev/null || print_warning "Some packages could not be installed"
            ;;
        rhel)
            PACKAGES="python3 python3-pip git curl wget net-tools wireless-tools iw bluez nmap"
            sudo yum install -y $PACKAGES 2>/dev/null || print_warning "Some packages could not be installed"
            ;;
        arch)
            PACKAGES="python python-pip git curl wget net-tools wireless_tools iw bluez nmap"
            sudo pacman -S --noconfirm $PACKAGES 2>/dev/null || print_warning "Some packages could not be installed"
            ;;
        suse)
            PACKAGES="python3 python3-pip git curl wget net-tools wireless-tools iw bluez nmap"
            sudo zypper install -y $PACKAGES 2>/dev/null || print_warning "Some packages could not be installed"
            ;;
        alpine)
            PACKAGES="python3 py3-pip git curl wget net-tools wireless-tools iw bluez nmap"
            sudo apk add $PACKAGES 2>/dev/null || print_warning "Some packages could not be installed"
            ;;
        *)
            print_warning "Please manually install: python3, pip, git, wireless-tools, iw, bluetooth tools"
            ;;
    esac
    
    print_success "System dependencies installed"
}

# Install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    # Create requirements if not exists
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
    
    if [ -f "$REQUIREMENTS_FILE" ]; then
        pip install -r "$REQUIREMENTS_FILE" --quiet || {
            print_warning "Some Python packages may not have installed correctly"
        }
    else
        # Install individual packages
        pip install flask --quiet 2>/dev/null || print_warning "flask not installed"
        pip install psutil --quiet 2>/dev/null || print_warning "psutil not installed"
        pip install netifaces --quiet 2>/dev/null || print_warning "netifaces not installed"
    fi
    
    print_success "Python dependencies installed"
}

# Setup permissions (Termux specific)
setup_permissions() {
    if [ "$ENVIRONMENT" = "termux" ]; then
        print_status "Setting up Termux permissions..."
        
        # Request storage permission
        termux-setup-storage 2>/dev/null || print_warning "Could not setup storage"
        
        print_success "Permissions configured"
    fi
}

# Make scripts executable
setup_scripts() {
    print_status "Setting up executable permissions..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Make main scripts executable
    chmod +x "$SCRIPT_DIR/recon.sh" 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/scanners/"*.sh 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/scanners/"*.py 2>/dev/null || true
    
    print_success "Scripts configured"
}

# Create symlink for easy access
create_symlink() {
    print_status "Creating command symlink..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [ "$ENVIRONMENT" = "termux" ]; then
        LINK_PATH="$HOME/../usr/bin/recon"
    else
        LINK_PATH="$HOME/.local/bin/recon"
        mkdir -p "$HOME/.local/bin"
    fi
    
    # Remove existing symlink
    rm -f "$LINK_PATH" 2>/dev/null || true
    
    # Create new symlink
    ln -s "$SCRIPT_DIR/recon.sh" "$LINK_PATH" 2>/dev/null || {
        print_warning "Could not create symlink - use ./recon.sh directly"
        return
    }
    
    print_success "Symlink created: $LINK_PATH"
}

# Verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    ERRORS=0
    
    # Check Python
    if command -v python3 &> /dev/null || command -v python &> /dev/null; then
        print_success "Python found"
    else
        print_error "Python not found"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
        print_success "pip found"
    else
        print_error "pip not found"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Check Flask
    python3 -c "import flask" 2>/dev/null || python -c "import flask" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Flask module found"
    else
        print_warning "Flask module not found - web dashboard may not work"
    fi
    
    # Check psutil
    python3 -c "import psutil" 2>/dev/null || python -c "import psutil" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "psutil module found"
    else
        print_warning "psutil module not found - some features may not work"
    fi
    
    if [ $ERRORS -eq 0 ]; then
        print_success "Installation verified successfully!"
    else
        print_warning "Installation completed with $ERRORS warning(s)"
    fi
}

# Print usage instructions
print_usage() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    Installation Complete!                     ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./recon.sh              - Launch interactive CLI"
    echo "  ./recon.sh --help       - Show all available commands"
    echo "  ./recon.sh scan network - Run network scanner"
    echo "  ./recon.sh scan wifi    - Run WiFi scanner"
    echo "  ./recon.sh scan bt      - Run Bluetooth scanner"
    echo "  ./recon.sh radar        - Launch radar UI"
    echo "  ./recon.sh web          - Start web dashboard"
    echo ""
    echo -e "${YELLOW}Note:${NC} Some features require root access or specific permissions."
    echo ""
}

# Main installation flow
main() {
    detect_environment
    update_packages
    install_system_deps
    install_python_deps
    setup_permissions
    setup_scripts
    create_symlink
    verify_installation
    print_usage
}

# Run main function
main
