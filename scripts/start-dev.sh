#!/bin/bash
# Development startup script for Household Budget MCP Server

set -e

echo "🚀 Starting Household Budget MCP Server (Development Mode)"
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
    echo "⚠️  Warning: .env file not found, using defaults"
    echo "   Copy .env.example to .env and adjust as needed"
fi

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
    echo "📁 Creating data directory"
    mkdir -p data
fi

# Build and start services
echo ""
echo "🔨 Building Docker images..."
docker compose build

echo ""
echo "🏃 Starting services..."
docker compose up -d backend frontend

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check backend health
if curl -f http://localhost:${BACKEND_PORT:-8000}/health &> /dev/null; then
    echo "✅ Backend is healthy (http://localhost:${BACKEND_PORT:-8000})"
else
    echo "⚠️  Backend health check failed"
fi

# Check frontend health
if curl -f http://localhost:${FRONTEND_PORT:-8080}/health &> /dev/null; then
    echo "✅ Frontend is healthy (http://localhost:${FRONTEND_PORT:-8080})"
else
    echo "⚠️  Frontend health check failed"
fi

echo ""
echo "=================================================="
echo "✨ Development environment is ready!"
echo ""
echo "📍 Access points:"
echo "   - Frontend: http://localhost:${FRONTEND_PORT:-8080}"
echo "   - Backend API: http://localhost:${BACKEND_PORT:-8000}"
echo "   - API Docs: http://localhost:${BACKEND_PORT:-8000}/docs"
echo ""
echo "📝 Useful commands:"
echo "   - View logs: docker compose logs -f"
echo "   - Stop services: docker compose down"
echo "   - Restart: docker compose restart"
echo ""
echo "Press Ctrl+C to stop watching logs, or run:"
echo "  docker compose logs -f"
