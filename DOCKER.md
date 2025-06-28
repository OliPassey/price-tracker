# Price Tracker - Docker Deployment

This guide covers how to build, deploy, and run the Price Tracker application using Docker.

## Quick Start with Docker

### 1. Build the Image

```bash
# Build with default tag
./build.sh

# Build with specific tag
./build.sh v1.0.0

# Build and tag for your registry
./build.sh latest your-registry.com
```

### 2. Configure Environment Variables (Optional)

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env
```

### 3. Run with Docker Compose (Recommended)

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

### 4. Manual Docker Run

```bash
# Create directories for persistence
mkdir -p data logs

# Run with environment variables
docker run -d \
  --name price-tracker \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.json:/app/config.json:ro \
  -e FLASK_ENV=production \
  -e DATABASE_PATH=/app/data/price_tracker.db \
  -e EMAIL_ENABLED=true \
  -e SMTP_SERVER=smtp.gmail.com \
  -e SENDER_EMAIL=your-email@gmail.com \
  -e SENDER_PASSWORD=your-app-password \
  -e RECIPIENT_EMAIL=alerts@yourdomain.com \
  price-tracker:latest
```

## Environment Variable Configuration

The application supports environment variable overrides for flexible deployment configurations. This allows you to customize settings without modifying the `config.json` file.

### Available Environment Variables

#### Database Configuration
- `DATABASE_PATH` - Path to SQLite database file (default: `/app/data/price_tracker.db`)

#### Scraping Configuration
- `DELAY_BETWEEN_REQUESTS` - Delay between requests in seconds (default: `2`)
- `MAX_CONCURRENT_REQUESTS` - Maximum concurrent requests (default: `1`)
- `REQUEST_TIMEOUT` - Request timeout in seconds (default: `30`)
- `RETRY_ATTEMPTS` - Number of retry attempts (default: `3`)

#### Email Notifications
- `EMAIL_ENABLED` - Enable email notifications (`true`/`false`)
- `SMTP_SERVER` - SMTP server hostname (e.g., `smtp.gmail.com`)
- `SMTP_PORT` - SMTP server port (e.g., `587`)
- `SENDER_EMAIL` - Email address to send from
- `SENDER_PASSWORD` - Email password or app password
- `RECIPIENT_EMAIL` - Email address to send alerts to

#### Webhook Notifications
- `WEBHOOK_ENABLED` - Enable webhook notifications (`true`/`false`)
- `WEBHOOK_URL` - Webhook URL for sending alerts

### Configuration Priority

Environment variables take precedence over `config.json` settings:
1. **Environment Variables** (highest priority)
2. **config.json** file (fallback)

### Using .env Files

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit the `.env` file with your settings:

```env
# Database
DATABASE_PATH=/app/data/price_tracker.db

# Email notifications
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=alerts@mydomain.com
SENDER_PASSWORD=my-app-password
RECIPIENT_EMAIL=me@mydomain.com

# Scraping
DELAY_BETWEEN_REQUESTS=3
MAX_CONCURRENT_REQUESTS=2
```

Docker Compose will automatically load the `.env` file:

```bash
docker-compose up -d
```

## Registry Deployment

### Push to Registry

```bash
# Tag for your registry
docker tag price-tracker:latest your-registry.com/price-tracker:latest

# Push to registry
docker push your-registry.com/price-tracker:latest
```

### Deploy from Registry

```bash
# Deploy using script
./deploy.sh latest your-registry.com

# Or manually
docker pull your-registry.com/price-tracker:latest
docker run -d \
  --name price-tracker \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.json:/app/config.json:ro \
  -e FLASK_ENV=production \
  your-registry.com/price-tracker:latest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_HOST` | `0.0.0.0` | Host to bind the Flask server |
| `FLASK_PORT` | `5000` | Port to bind the Flask server |
| `FLASK_ENV` | `production` | Flask environment (production/development) |
| `PYTHONUNBUFFERED` | `1` | Enable unbuffered Python output |

## Volumes

| Container Path | Description |
|----------------|-------------|
| `/app/data` | Database and persistent data |
| `/app/logs` | Application logs |
| `/app/config.json` | Configuration file (read-only) |

## Health Check

The container includes a health check that verifies the application is responding on port 5000.

```bash
# Check container health
docker ps

# View health check logs
docker inspect price-tracker | grep -A 10 Health
```

## Monitoring

### View Logs

```bash
# Real-time logs
docker logs -f price-tracker

# Last 100 lines
docker logs --tail 100 price-tracker

# With docker-compose
docker-compose logs -f
```

### Container Stats

```bash
# Resource usage
docker stats price-tracker

# Container information
docker inspect price-tracker
```

## Troubleshooting

### Container Won't Start

1. Check logs: `docker logs price-tracker`
2. Verify config file exists and is valid JSON
3. Ensure data and logs directories exist with correct permissions

### Application Not Accessible

1. Verify port mapping: `docker ps`
2. Check firewall settings
3. Verify container is healthy: `docker ps` (should show "healthy")

### Database Issues

1. Check if data directory is properly mounted
2. Verify database file permissions
3. Check logs for database errors

## Production Considerations

### Security

- Run container as non-root user (already configured)
- Use read-only config file mount
- Consider running behind a reverse proxy (nginx, traefik)
- Set up proper firewall rules

### Performance

- Allocate sufficient memory for scraping operations
- Consider scaling with multiple instances behind a load balancer
- Monitor resource usage and adjust limits as needed

### Backup

```bash
# Backup data directory
tar -czf price-tracker-backup-$(date +%Y%m%d).tar.gz data/

# Restore backup
tar -xzf price-tracker-backup-YYYYMMDD.tar.gz
```

## Development

### Local Development with Docker

```bash
# Build development image
docker build -t price-tracker:dev .

# Run with development settings
docker run -it --rm \
  -p 5000:5000 \
  -v $(pwd):/app \
  -e FLASK_ENV=development \
  price-tracker:dev
```

### Debugging

```bash
# Run container with bash shell
docker run -it --rm \
  -v $(pwd):/app \
  price-tracker:latest \
  /bin/bash

# Execute commands in running container
docker exec -it price-tracker /bin/bash
```
