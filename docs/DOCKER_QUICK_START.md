# Docker Quick Start Guide

Deploy the complete AI Avatar System in 5 minutes!

## Prerequisites

- Docker & Docker Compose installed
- Git with Git LFS
- 8GB+ RAM
- 20GB+ disk space

## Quick Deploy

### 1. Clone & Setup

```bash
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System
git lfs pull
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Get API key: https://makersuite.google.com/app/apikey

### 3. Start Everything

```bash
./docker-start.sh
```

Or manually:

```bash
docker-compose up -d
```

### 4. Access Services

- **Avatar**: http://localhost:8010/webrtcapi.html
- **API Docs**: http://localhost:8000/docs
- **Qdrant**: http://localhost:6333/dashboard

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart
docker-compose restart

# Rebuild
docker-compose up -d --build
```

## Troubleshooting

### Services won't start
```bash
docker-compose logs
```

### Models not found
```bash
git lfs pull
```

### Port already in use
```bash
# Stop conflicting services
sudo lsof -i :8000
sudo lsof -i :8010
```

## Performance

- **CPU (Mac M2)**: 10-15 FPS, batch_size=2
- **GPU (GTX 1660)**: 40-60 FPS, batch_size=4
- **GPU (RTX 4090)**: 100+ FPS, batch_size=8

For GPU support, see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md#gpu-support)

## Architecture

```
┌─────────────────────────────────────────────┐
│           Docker Compose Network            │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Qdrant  │  │   RAG    │  │LiveTalk  │ │
│  │  :6333   │◄─┤ Backend  │◄─┤  :8010   │ │
│  │          │  │  :8000   │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

## What's Included

✅ Complete RAG backend with Gemini  
✅ LiveTalking avatar with Wav2Lip  
✅ Qdrant vector database  
✅ All models and avatar data  
✅ Optimized performance settings  
✅ Health checks and auto-restart  

## Next Steps

- Read [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for detailed configuration
- Check [README.md](README.md) for system overview
- See [PERFORMANCE_FIX_REPORT.md](PERFORMANCE_FIX_REPORT.md) for optimization details

## Support

Issues: https://github.com/NTISPAK/RAG-Based-AI--Avatar-System/issues
