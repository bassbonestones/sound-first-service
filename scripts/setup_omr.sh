#!/bin/bash
#
# Sound First OMR Setup Script
#
# This script sets up the OMR processing infrastructure:
# 1. Checks/installs Java 17+
# 2. Downloads Audiveris if not present
# 3. Installs Redis (if needed)
# 4. Installs Python dependencies
#
# Usage:
#   ./scripts/setup_omr.sh
#
# After setup, run:
#   ./scripts/start_omr_worker.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$PROJECT_DIR/tools"
AUDIVERIS_DIR="$TOOLS_DIR/audiveris"
AUDIVERIS_VERSION="5.3.1"
AUDIVERIS_JAR="$AUDIVERIS_DIR/Audiveris-$AUDIVERIS_VERSION.jar"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# Check Java
# =============================================================================

check_java() {
    echo_info "Checking Java installation..."
    
    if ! command -v java &> /dev/null; then
        echo_error "Java not found. Please install Java 17+ first."
        echo_info "macOS: brew install openjdk@17"
        echo_info "Ubuntu: sudo apt install openjdk-17-jdk"
        exit 1
    fi
    
    JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1)
    
    if [ "$JAVA_VERSION" -lt 17 ]; then
        echo_error "Java 17+ required (found Java $JAVA_VERSION)"
        exit 1
    fi
    
    echo_success "Java $JAVA_VERSION found"
}

# =============================================================================
# Download Audiveris
# =============================================================================

setup_audiveris() {
    echo_info "Setting up Audiveris..."
    
    mkdir -p "$AUDIVERIS_DIR"
    
    if [ -f "$AUDIVERIS_JAR" ]; then
        echo_success "Audiveris already installed at $AUDIVERIS_JAR"
        return
    fi
    
    echo_info "Downloading Audiveris $AUDIVERIS_VERSION..."
    
    # Download from GitHub releases
    DOWNLOAD_URL="https://github.com/Audiveris/audiveris/releases/download/$AUDIVERIS_VERSION/Audiveris-$AUDIVERIS_VERSION.jar"
    
    if command -v curl &> /dev/null; then
        curl -L -o "$AUDIVERIS_JAR" "$DOWNLOAD_URL"
    elif command -v wget &> /dev/null; then
        wget -O "$AUDIVERIS_JAR" "$DOWNLOAD_URL"
    else
        echo_error "curl or wget required for download"
        exit 1
    fi
    
    if [ -f "$AUDIVERIS_JAR" ]; then
        echo_success "Audiveris downloaded to $AUDIVERIS_JAR"
    else
        echo_error "Failed to download Audiveris"
        exit 1
    fi
    
    # Test Audiveris
    echo_info "Testing Audiveris..."
    if java -jar "$AUDIVERIS_JAR" -help > /dev/null 2>&1; then
        echo_success "Audiveris working correctly"
    else
        echo_warn "Audiveris test failed - may need additional dependencies"
    fi
}

# =============================================================================
# Check/Install Redis
# =============================================================================

check_redis() {
    echo_info "Checking Redis..."
    
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping > /dev/null 2>&1; then
            echo_success "Redis is running"
            return 0
        fi
    fi
    
    echo_warn "Redis not running"
    
    # Check if installed but not running
    if command -v redis-server &> /dev/null; then
        echo_info "Redis is installed but not running"
        echo_info "Start it with: redis-server"
        return 1
    fi
    
    # Offer to install
    echo_info "Redis not installed. Install options:"
    echo_info "  macOS:  brew install redis && brew services start redis"
    echo_info "  Ubuntu: sudo apt install redis-server && sudo systemctl start redis"
    echo_info "  Docker: docker run -d -p 6379:6379 redis"
    return 1
}

# =============================================================================
# Install Python Dependencies
# =============================================================================

install_python_deps() {
    echo_info "Installing Python dependencies..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -f "requirements.txt" ]; then
        echo_error "requirements.txt not found"
        exit 1
    fi
    
    pip install -q celery[redis] redis
    
    echo_success "Python dependencies installed"
}

# =============================================================================
# Create .env file
# =============================================================================

create_env_file() {
    ENV_FILE="$PROJECT_DIR/.env"
    
    if [ -f "$ENV_FILE" ]; then
        echo_info ".env file already exists"
        
        # Check if OMR settings are present
        if ! grep -q "AUDIVERIS_PATH" "$ENV_FILE"; then
            echo_info "Adding OMR settings to .env..."
            cat >> "$ENV_FILE" << EOF

# =============================================================================
# OMR Settings (added by setup_omr.sh)
# =============================================================================
OMR_PROVIDER=audiveris
AUDIVERIS_PATH=$AUDIVERIS_JAR
REDIS_URL=redis://localhost:6379/0
EOF
            echo_success "OMR settings added to .env"
        fi
    else
        echo_info "Creating .env file..."
        cat > "$ENV_FILE" << EOF
# =============================================================================
# Sound First Service Configuration
# =============================================================================

# Database
DATABASE_URL=postgresql://user:password@localhost/soundfirst

# Storage
STORAGE_PROVIDER=local
LOCAL_STORAGE_PATH=./uploads

# OMR Settings
OMR_PROVIDER=audiveris
AUDIVERIS_PATH=$AUDIVERIS_JAR

# Celery / Redis
REDIS_URL=redis://localhost:6379/0
EOF
        echo_success ".env file created"
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "========================================"
    echo "  Sound First OMR Setup"
    echo "========================================"
    echo ""
    
    check_java
    setup_audiveris
    check_redis || true  # Don't fail if Redis isn't running yet
    install_python_deps
    create_env_file
    
    echo ""
    echo "========================================"
    echo "  Setup Complete!"
    echo "========================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Start Redis (if not running):"
    echo "   redis-server"
    echo ""
    echo "2. Start the Celery worker:"
    echo "   ./scripts/start_omr_worker.sh"
    echo ""
    echo "3. Start the API server:"
    echo "   uvicorn app.main:app --reload"
    echo ""
    echo "4. Test OMR processing:"
    echo "   curl -X GET http://localhost:8000/imports/health"
    echo ""
}

main "$@"
