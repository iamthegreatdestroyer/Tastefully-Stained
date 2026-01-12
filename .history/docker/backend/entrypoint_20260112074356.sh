#!/bin/bash
# =============================================================================
# TASTEFULLY STAINED - BACKEND ENTRYPOINT SCRIPT
# =============================================================================
# Production entrypoint with database migration and health checks
#
# Copyright (c) 2025 Tastefully Stained. All Rights Reserved.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          TASTEFULLY STAINED - BACKEND SERVICE                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

# Function to wait for a service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=${4:-30}
    local attempt=1

    echo -e "${YELLOW}⏳ Waiting for $service_name ($host:$port)...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo -e "${GREEN}✓ $service_name is available${NC}"
            return 0
        fi
        echo -e "  Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ Failed to connect to $service_name after $max_attempts attempts${NC}"
    return 1
}

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}📦 Running database migrations...${NC}"
    
    if python -m alembic upgrade head; then
        echo -e "${GREEN}✓ Database migrations completed successfully${NC}"
    else
        echo -e "${RED}✗ Database migration failed${NC}"
        return 1
    fi
}

# Wait for required services based on environment
echo -e "\n${BLUE}🔄 Checking service dependencies...${NC}\n"

# PostgreSQL
if [ -n "$DATABASE_HOST" ]; then
    DB_HOST=${DATABASE_HOST:-postgres}
    DB_PORT=${DATABASE_PORT:-5432}
    wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" 30 || exit 1
fi

# Redis
if [ -n "$REDIS_HOST" ]; then
    REDIS_HOST=${REDIS_HOST:-redis}
    REDIS_PORT=${REDIS_PORT:-6379}
    wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 15 || exit 1
fi

# Run migrations if enabled
if [ "$RUN_MIGRATIONS" = "true" ]; then
    run_migrations || exit 1
fi

# Create required directories
echo -e "\n${BLUE}📁 Ensuring required directories exist...${NC}"
mkdir -p /app/data /app/logs /app/temp /app/uploads /app/exports

# Display configuration (hide sensitive values)
echo -e "\n${BLUE}⚙️  Configuration:${NC}"
echo -e "  APP_ENV: ${APP_ENV:-production}"
echo -e "  DEBUG: ${DEBUG:-false}"
echo -e "  LOG_LEVEL: ${LOG_LEVEL:-info}"
echo -e "  WORKERS: ${WORKERS:-4}"
echo -e "  HOST: 0.0.0.0"
echo -e "  PORT: 8000"

# Health check before starting
echo -e "\n${BLUE}🏥 Performing pre-flight health check...${NC}"
python -c "from src.main import app; print('✓ Application imports successfully')" 2>/dev/null || {
    echo -e "${RED}✗ Failed to import application${NC}"
    exit 1
}
echo -e "${GREEN}✓ Pre-flight checks passed${NC}"

# Start the application
echo -e "\n${GREEN}🚀 Starting Tastefully Stained Backend...${NC}\n"

# Check if we're in development mode
if [ "$APP_ENV" = "development" ] || [ "$DEBUG" = "true" ]; then
    echo -e "${YELLOW}⚠️  Running in DEVELOPMENT mode with hot reload${NC}\n"
    exec uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir /app/src \
        --log-level debug
else
    # Production mode with Gunicorn + Uvicorn workers
    echo -e "${GREEN}🔒 Running in PRODUCTION mode${NC}\n"
    exec gunicorn src.main:app \
        --bind 0.0.0.0:8000 \
        --workers ${WORKERS:-4} \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout ${TIMEOUT:-120} \
        --graceful-timeout ${GRACEFUL_TIMEOUT:-30} \
        --keep-alive ${KEEP_ALIVE:-5} \
        --max-requests ${MAX_REQUESTS:-10000} \
        --max-requests-jitter ${MAX_REQUESTS_JITTER:-1000} \
        --access-logfile - \
        --error-logfile - \
        --capture-output \
        --enable-stdio-inheritance \
        --log-level ${LOG_LEVEL:-info}
fi
