# Docker Deployment Guide

Complete containerized deployment guide for the AI Avatar System with RAG Backend.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [GPU Support](#gpu-support)
- [Deployment Options](#deployment-options)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (included with Docker Desktop)
- Git with Git LFS installed
- 8GB+ RAM recommended
- 20GB+ free disk space

### For GPU Support (Optional but Recommended)
- NVIDIA GPU with CUDA support
- NVIDIA Docker runtime ([Install Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html))

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System
```

### 2. Download Large Files (Git LFS)

```bash
git lfs pull
```

This will download:
- `LiveTalking/models/wav2lip.pth` (205 MB)
- `LiveTalking/data/avatars/` (362 MB)

### 3. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Google Gemini API Key (Required)
GEMINI_API_KEY=your_gemini_api_key_here

# Qdrant Configuration
QDRANT_URL=http://qdrant:6333

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Get Gemini API Key:** https://makersuite.google.com/app/apikey

### 4. Start All Services

```bash
docker-compose up -d
```

This will start:
- **Qdrant** (Vector Database) on port 6333
- **RAG Backend** (FastAPI) on port 8000
- **LiveTalking** (Avatar Frontend) on port 8010

### 5. Verify Deployment

Check service health:

```bash
docker-compose ps
```

All services should show "healthy" status.

### 6. Access the Application

- **Avatar Interface**: http://localhost:8010/webrtcapi.html
- **RAG Backend API**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## Configuration

### Environment Variables

#### RAG Backend
- `GEMINI_API_KEY`: Google Gemini API key (required)
- `QDRANT_URL`: Qdrant connection URL (default: http://qdrant:6333)
- `EMBEDDING_MODEL`: HuggingFace embedding model (default: sentence-transformers/all-MiniLM-L6-v2)

#### LiveTalking Frontend
- `RAG_BACKEND_URL`: RAG backend URL (default: http://rag-backend:8000)
- `BATCH_SIZE`: Inference batch size (default: 2, optimized for Mac M2/CPU)
- `AVATAR_ID`: Avatar to use (default: wav2lip256_avatar1)
- `REF_FILE`: TTS voice (default: en-US-JennyNeural)

### Performance Tuning

#### For CPU-Only Systems (Mac M2, Intel)
Keep default settings:
```yaml
BATCH_SIZE=2
```

#### For GPU Systems (NVIDIA)
Increase batch size for better performance:
```yaml
BATCH_SIZE=4
```

And uncomment GPU support in `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## GPU Support

### Enable NVIDIA GPU Support

1. **Install NVIDIA Container Toolkit**:

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

2. **Verify GPU Access**:

```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

3. **Update docker-compose.yml**:

Uncomment the GPU section in the `livetalking` service:

```yaml
livetalking:
  # ... other config ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

4. **Restart Services**:

```bash
docker-compose down
docker-compose up -d
```

## Deployment Options

### Option 1: Development (Current Setup)
All services on one machine with Docker Compose.

### Option 2: Production with Separate Servers

#### Server 1: RAG Backend + Qdrant
```bash
docker-compose up -d qdrant rag-backend
```

#### Server 2: LiveTalking Frontend
Update `RAG_BACKEND_URL` to point to Server 1:
```yaml
environment:
  - RAG_BACKEND_URL=http://<server1-ip>:8000
```

```bash
docker-compose up -d livetalking
```

### Option 3: Cloud Deployment

#### Deploy to AWS/GCP/Azure

1. **Build and push images to registry**:

```bash
# Tag images
docker tag rag-based-ai--avatar-system-rag-backend:latest your-registry/rag-backend:latest
docker tag rag-based-ai--avatar-system-livetalking:latest your-registry/livetalking:latest

# Push to registry
docker push your-registry/rag-backend:latest
docker push your-registry/livetalking:latest
```

2. **Deploy using cloud-specific tools**:
   - AWS: ECS/EKS
   - GCP: Cloud Run/GKE
   - Azure: Container Instances/AKS

## Managing the System

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f livetalking
docker-compose logs -f rag-backend
docker-compose logs -f qdrant
```

### Stop Services

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

### Update and Rebuild

```bash
git pull
git lfs pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Clean Up

```bash
# Stop and remove containers, networks
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Data Persistence

### Volumes

The following data is persisted in Docker volumes:

- **qdrant_storage**: Vector database data
- **LiveTalking/models**: Wav2Lip models (mounted from host)
- **LiveTalking/data**: Avatar data (mounted from host)

### Backup Qdrant Data

```bash
docker run --rm -v rag-based-ai--avatar-system_qdrant_storage:/data -v $(pwd):/backup ubuntu tar czf /backup/qdrant-backup.tar.gz /data
```

### Restore Qdrant Data

```bash
docker run --rm -v rag-based-ai--avatar-system_qdrant_storage:/data -v $(pwd):/backup ubuntu tar xzf /backup/qdrant-backup.tar.gz -C /
```

## Troubleshooting

### Issue: Services won't start

**Solution**: Check logs and ensure ports are not in use:

```bash
docker-compose logs
sudo lsof -i :6333  # Qdrant
sudo lsof -i :8000  # RAG Backend
sudo lsof -i :8010  # LiveTalking
```

### Issue: Out of memory

**Solution**: Increase Docker memory limit:
- Docker Desktop: Settings → Resources → Memory (set to 8GB+)

### Issue: Models not found

**Solution**: Ensure Git LFS files are downloaded:

```bash
git lfs pull
ls -lh LiveTalking/models/wav2lip.pth
ls -lh LiveTalking/data/avatars/wav2lip256_avatar1/
```

### Issue: Slow performance on CPU

**Solution**: 
1. Reduce batch size in docker-compose.yml:
   ```yaml
   BATCH_SIZE=1
   ```
2. Use GPU if available (see GPU Support section)

### Issue: Qdrant connection failed

**Solution**: Wait for Qdrant to be healthy:

```bash
docker-compose logs qdrant
curl http://localhost:6333/health
```

### Issue: Permission denied errors

**Solution**: Fix file permissions:

```bash
sudo chown -R $USER:$USER .
chmod -R 755 LiveTalking/
```

## Performance Benchmarks

### CPU (Mac M2)
- Inference FPS: 10-15
- Response Time: 2-3 seconds
- Batch Size: 2

### GPU (NVIDIA GTX 1660)
- Inference FPS: 40-60
- Response Time: 1-2 seconds
- Batch Size: 4

### GPU (NVIDIA RTX 4090)
- Inference FPS: 100+
- Response Time: <1 second
- Batch Size: 8

## Security Considerations

1. **API Keys**: Never commit `.env` file to Git
2. **Network**: Use firewall rules to restrict access
3. **HTTPS**: Use reverse proxy (nginx/traefik) for production
4. **Updates**: Regularly update base images and dependencies

## Support

For issues and questions:
- GitHub Issues: https://github.com/NTISPAK/RAG-Based-AI--Avatar-System/issues
- Documentation: See README.md

## License

See LICENSE file in the repository.
