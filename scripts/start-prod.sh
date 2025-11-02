#!/bin/bash
# Production startup script for Household Budget MCP Server

set -e

echo "🚀 Starting Household Budget MCP Server (Production Mode)"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Error: .env file not found"
    echo "   Copy .env.example to .env and configure production settings"
    exit 1
fi

# Validate required environment variables
: "${BACKEND_PORT:?Error: BACKEND_PORT not set}"
: "${FRONTEND_PORT:?Error: FRONTEND_PORT not set}"

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
    echo "📁 Creating data directory"
    mkdir -p data
fi

# Build images
echo ""
echo "🔨 Building Docker images for production..."
docker compose build --no-cache

# Start all services including nginx
echo ""
echo "🏃 Starting all services (backend, frontend, nginx)..."
docker compose --profile production up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
check_health() {
    local service=$1
    local url=$2
    if curl -f "$url" &> /dev/null; then
        echo "✅ $service is healthy"
        return 0
    else
        echo "❌ $service health check failed"
        return 1
    fi
}

check_health "Backend" "http://localhost:${BACKEND_PORT}/health"
check_health "Frontend" "http://localhost:${FRONTEND_PORT}/health"
check_health "Nginx" "http://localhost:${NGINX_PORT:-80}/health"

echo ""
echo "=================================================="
echo "✨ Production environment is running!"
echo ""
echo "📍 Access points:"
echo "   - Main URL: http://localhost:${NGINX_PORT:-80}"
echo "   - API Docs: http://localhost:${NGINX_PORT:-80}/api/docs"
echo ""
echo "📝 Useful commands:"
echo "   - View logs: docker compose logs -f"
echo "   - Stop services: docker compose --profile production down"
echo "   - Restart: docker compose --profile production restart"
echo ""
echo "🔒 Security reminders:"
echo "   - Change default ports if exposed to public network"
echo "   - Configure firewall rules"
echo "   - Enable HTTPS with SSL certificates"
echo "   - Review and update .env security settings"
