#!/bin/bash
#
# Sound First Development Server
#
# Starts all services needed for development:
# - Redis (if Docker available and Redis not running)
# - Celery worker (for OMR processing)
# - FastAPI server (API)
#
# Usage:
#   ./scripts/start_dev.sh
#
# To stop all services:
#   Ctrl+C (services are started in foreground)
#
# For production, use proper process managers (systemd, supervisord, etc.)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Array to track background PIDs
PIDS=()

# Cleanup function
cleanup() {
    echo ""
    echo_info "Shutting down services..."
    
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    
    # Stop Redis container if we started it
    if [ "$STARTED_REDIS_CONTAINER" = true ]; then
        docker stop soundfirst-redis 2>/dev/null || true
    fi
    
    echo_success "All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

STARTED_REDIS_CONTAINER=false

# =============================================================================
# Check/Start Redis
# =============================================================================

start_redis() {
    echo_info "Checking Redis..."
    
    if redis-cli ping &>/dev/null; then
        echo_success "Redis already running"
        return
    fi
    
    # Try Docker
    if command -v docker &>/dev/null; then
        echo_info "Starting Redis via Docker..."
        docker run -d --rm --name soundfirst-redis -p 6379:6379 redis:alpine &>/dev/null
        STARTED_REDIS_CONTAINER=true
        sleep 2
        
        if redis-cli ping &>/dev/null; then
            echo_success "Redis started via Docker"
            return
        fi
    fi
    
    echo_error "Redis not available. Please start Redis manually."
    echo_info "Options:"
    echo_info "  - brew services start redis"
    echo_info "  - docker run -d -p 6379:6379 redis"
    exit 1
}

# =============================================================================
# Start Celery Worker
# =============================================================================

start_celery() {
    echo_info "Starting Celery worker..."
    
    celery -A app.worker worker \
        --loglevel=info \
        --concurrency=2 \
        --queues=omr,default \
        &> logs/celery.log &
    
    PIDS+=($!)
    echo_success "Celery worker started (PID: ${PIDS[-1]})"
}

# =============================================================================
# Start FastAPI Server
# =============================================================================

start_api() {
    echo_info "Starting FastAPI server..."
    echo ""
    echo "========================================"
    echo "  All Services Running"
    echo "========================================"
    echo ""
    echo "API Server:      http://localhost:8000"
    echo "API Docs:        http://localhost:8000/docs"
    echo "Health Check:    http://localhost:8000/imports/health"
    echo ""
    echo "Celery logs:     logs/celery.log"
    echo ""
    echo "Press Ctrl+C to stop all services"
    echo ""
    
    # Run uvicorn in foreground
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "========================================"
    echo "  Sound First Development Server"
    echo "========================================"
    echo ""
    
    # Create logs directory
    mkdir -p logs
    
    start_redis
    sleep 1
    
    start_celery
    sleep 2
    
    # Run API in foreground (blocks until Ctrl+C)
    start_api
}

main "$@"
