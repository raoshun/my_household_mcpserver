#!/bin/bash
# Stop script for Household Budget MCP Server

set -e

echo "🛑 Stopping Household Budget MCP Server"
echo "=================================================="

# Check if services are running
if docker compose ps --quiet | grep -q .; then
    echo "📦 Stopping running containers..."
    docker compose --profile production down
    echo "✅ All services stopped"
else
    echo "ℹ️  No services are running"
fi

echo ""
echo "📝 To remove all data and volumes, run:"
echo "  docker compose --profile production down -v"
