#!/bin/bash
#
# Sound First OMR Worker Start Script
#
# Starts the Celery worker for processing OMR jobs.
#
# Usage:
#   ./scripts/start_omr_worker.sh [--dev]
#
# Options:
#   --dev     Run with auto-reload for development
#   --beat    Include beat scheduler for periodic tasks
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default settings
CONCURRENCY=${CELERY_CONCURRENCY:-2}
LOG_LEVEL=${CELERY_LOG_LEVEL:-info}
QUEUE=${CELERY_QUEUE:-omr,default}

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}[INFO]${NC} Starting Sound First OMR Worker..."
echo -e "${BLUE}[INFO]${NC} Log level: $LOG_LEVEL"
echo -e "${BLUE}[INFO]${NC} Concurrency: $CONCURRENCY"
echo -e "${BLUE}[INFO]${NC} Queues: $QUEUE"

# Parse arguments
DEV_MODE=false
BEAT_MODE=false

for arg in "$@"; do
    case $arg in
        --dev)
            DEV_MODE=true
            ;;
        --beat)
            BEAT_MODE=true
            ;;
    esac
done

# Build celery command
CELERY_CMD="celery -A app.worker worker"
CELERY_CMD="$CELERY_CMD --loglevel=$LOG_LEVEL"
CELERY_CMD="$CELERY_CMD --concurrency=$CONCURRENCY"
CELERY_CMD="$CELERY_CMD --queues=$QUEUE"

if [ "$BEAT_MODE" = true ]; then
    CELERY_CMD="$CELERY_CMD --beat"
fi

if [ "$DEV_MODE" = true ]; then
    echo -e "${GREEN}[DEV]${NC} Running with watchdog auto-reload"
    # Use watchmedo for auto-reload in development
    if command -v watchmedo &> /dev/null; then
        watchmedo auto-restart \
            --directory=./app \
            --pattern="*.py" \
            --recursive \
            -- $CELERY_CMD
    else
        echo -e "${BLUE}[INFO]${NC} watchdog not installed, running without auto-reload"
        echo -e "${BLUE}[INFO]${NC} Install with: pip install watchdog"
        $CELERY_CMD
    fi
else
    $CELERY_CMD
fi
