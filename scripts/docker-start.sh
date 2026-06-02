#!/bin/bash

# Docker Deployment Startup Script for AI Avatar System
# This script helps you deploy the complete system with Docker

set -e

echo "=========================================="
echo "AI Avatar System - Docker Deployment"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file and add your GEMINI_API_KEY"
    echo "   Get your API key from: https://makersuite.google.com/app/apikey"
    echo ""
    read -p "Press Enter after you've added your API key to .env..."
fi

# Check if Git LFS files are downloaded
if [ ! -f "LiveTalking/models/wav2lip.pth" ]; then
    echo "⚠️  Model files not found. Downloading with Git LFS..."
    git lfs pull
    echo "✅ Model files downloaded"
else
    echo "✅ Model files found"
fi

echo ""
echo "Starting services..."
echo ""

# Build and start services
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Access your services:"
echo "  🎭 Avatar Interface:  http://localhost:8010/webrtcapi.html"
echo "  📚 RAG Backend API:   http://localhost:8000/docs"
echo "  🔍 Qdrant Dashboard:  http://localhost:6333/dashboard"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
