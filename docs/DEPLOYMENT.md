# Tastefully Stained - Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

## Quick Start (Docker)

1. Clone the repository:

   ```bash
   git clone https://github.com/iamthegreatdestroyer/Tastefully-Stained.git
   cd Tastefully-Stained
   ```

2. Copy environment file:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Start services:

   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Environment Variables

| Variable                                   | Description                          | Default            |
| ------------------------------------------ | ------------------------------------ | ------------------ |
| `TASTEFULLY_STAINED_ENVIRONMENT`           | Environment (development/production) | development        |
| `TASTEFULLY_STAINED_DEBUG`                 | Enable debug mode                    | true               |
| `TASTEFULLY_STAINED_SECRET_KEY`            | Secret key for signing               | (required)         |
| `TASTEFULLY_STAINED_DATABASE_HOST`         | PostgreSQL host                      | localhost          |
| `TASTEFULLY_STAINED_DATABASE_PORT`         | PostgreSQL port                      | 5432               |
| `TASTEFULLY_STAINED_DATABASE_NAME`         | Database name                        | tastefully_stained |
| `TASTEFULLY_STAINED_DATABASE_USER`         | Database user                        | postgres           |
| `TASTEFULLY_STAINED_DATABASE_PASSWORD`     | Database password                    | (required)         |
| `TASTEFULLY_STAINED_REDIS_HOST`            | Redis host                           | localhost          |
| `TASTEFULLY_STAINED_REDIS_PORT`            | Redis port                           | 6379               |
| `TASTEFULLY_STAINED_ETHEREUM_PROVIDER_URL` | Ethereum RPC URL                     | (optional)         |
| `TASTEFULLY_STAINED_ETHEREUM_PRIVATE_KEY`  | Signing key                          | (optional)         |

## Production Deployment

### Using Docker Compose

```yaml
# docker-compose.prod.yml
version: "3.8"

services:
  backend:
    image: ghcr.io/iamthegreatdestroyer/tastefully-stained-backend:latest
    environment:
      - TASTEFULLY_STAINED_ENVIRONMENT=production
      - TASTEFULLY_STAINED_DEBUG=false
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  frontend:
    image: ghcr.io/iamthegreatdestroyer/tastefully-stained-frontend:latest
    ports:
      - "80:80"

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=tastefully_stained
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Health Checks

Backend health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{ "status": "healthy", "version": "0.1.0", "service": "tastefully-stained" }
```

## Monitoring

### Prometheus Metrics

The backend exposes Prometheus metrics at `/metrics`.

### Logging

Logs are output in JSON format in production for easy parsing:

```json
{ "timestamp": "2024-01-01T00:00:00Z", "level": "INFO", "message": "..." }
```

## Backup & Recovery

### Database Backup

```bash
docker exec postgres pg_dump -U postgres tastefully_stained > backup.sql
```

### Database Restore

```bash
docker exec -i postgres psql -U postgres tastefully_stained < backup.sql
```

## Troubleshooting

### Common Issues

1. **Container won't start**: Check logs with `docker-compose logs`
2. **Database connection failed**: Verify credentials in `.env`
3. **CORS errors**: Update `CORS_ORIGINS` in config
4. **Out of memory**: Increase Docker memory limits
