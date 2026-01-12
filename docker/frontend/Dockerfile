# =============================================================================
# TASTEFULLY STAINED - FRONTEND PRODUCTION DOCKERFILE
# =============================================================================
# Multi-stage build for Next.js/React application
# Port: 17710 (host) -> 3000 (container)
#
# Stage 1: Install dependencies
# Stage 2: Build the application
# Stage 3: Production runtime with nginx
#
# Build: docker build -t tastefully-stained-frontend:latest -f docker/frontend/Dockerfile .
# Run: docker run -p 17710:80 tastefully-stained-frontend:latest
#
# Copyright (c) 2025 Tastefully Stained. All Rights Reserved.
# =============================================================================

# -----------------------------------------------------------------------------
# STAGE 1: Dependencies
# -----------------------------------------------------------------------------
FROM node:20-alpine AS deps

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
COPY frontend/yarn.lock* ./
COPY frontend/pnpm-lock.yaml* ./

# Install dependencies based on lock file
RUN \
    if [ -f yarn.lock ]; then \
    corepack enable && yarn --frozen-lockfile; \
    elif [ -f pnpm-lock.yaml ]; then \
    corepack enable pnpm && pnpm install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then \
    npm ci; \
    else \
    npm install; \
    fi

# -----------------------------------------------------------------------------
# STAGE 2: Builder
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .

# Environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APP_URL
ARG NEXT_PUBLIC_WS_URL

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:17700} \
    NEXT_PUBLIC_APP_URL=${NEXT_PUBLIC_APP_URL:-http://localhost:17710} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL:-ws://localhost:17700}

# Build the application
RUN \
    if [ -f yarn.lock ]; then \
    yarn build; \
    elif [ -f pnpm-lock.yaml ]; then \
    corepack enable pnpm && pnpm build; \
    else \
    npm run build; \
    fi

# -----------------------------------------------------------------------------
# STAGE 3: Production Runtime with Nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine AS runner

LABEL maintainer="Tastefully Stained <admin@tastefullystained.com>" \
    version="0.1.0" \
    description="Tastefully Stained Frontend - Production"

# Install runtime dependencies
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup -g 1001 -S appgroup \
    && adduser -S -u 1001 -G appgroup appuser

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY docker/frontend/nginx.conf /etc/nginx/nginx.conf
COPY docker/frontend/default.conf /etc/nginx/conf.d/default.conf

# Copy static files from builder
COPY --from=builder /app/out /usr/share/nginx/html
# For SSR (if using): COPY --from=builder /app/.next/standalone ./
# For SSR (if using): COPY --from=builder /app/.next/static ./.next/static
# For SSR (if using): COPY --from=builder /app/public ./public

# Create cache directories with correct permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run \
    && chown -R appuser:appgroup /var/cache/nginx \
    && chown -R appuser:appgroup /var/log/nginx \
    && chown -R appuser:appgroup /usr/share/nginx/html \
    && touch /var/run/nginx.pid \
    && chown -R appuser:appgroup /var/run/nginx.pid \
    && chmod -R 755 /var/cache/nginx

# For running nginx as non-root on port 80, we need CAP_NET_BIND_SERVICE
# Alternative: use port 8080 inside container and map to 80/443 outside

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Expose port
EXPOSE 80

# Use non-root user
USER appuser

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
