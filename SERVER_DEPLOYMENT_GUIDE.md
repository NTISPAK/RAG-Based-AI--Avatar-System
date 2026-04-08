# Server Deployment Guide - AI Avatar System

Complete guide for deploying the AI Avatar System with Urdu translation on a production server.

---

## Table of Contents
1. [Required Files & Assets](#required-files--assets)
2. [Server Requirements](#server-requirements)
3. [Deployment Methods](#deployment-methods)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)

---

## Required Files & Assets

### 1. **Core Application Files**

#### Backend (RAG System)
```
Tester/
├── main.py                          # FastAPI RAG backend
├── translation_service.py           # Urdu translation service
├── ingest.py                        # Document ingestion
├── requirements.txt                 # Python dependencies
├── .env                            # Environment variables (DO NOT commit)
└── .env.example                    # Template for environment variables
```

#### Frontend (LiveTalking)
```
LiveTalking/
├── app.py                          # Main application
├── lipreal.py                      # Wav2Lip inference (optimized)
├── llm.py                          # RAG integration
├── baseasr.py                      # ASR processing
├── webrtc.py                       # WebRTC handling
├── basereal.py                     # Base avatar class
├── requirements.txt                # Python dependencies
├── web/                            # Web interface files
│   ├── webrtcapi.html
│   ├── dashboard.html
│   └── client.js
└── wav2lip/                        # Wav2Lip model code
```

---

### 2. **Large Model Files (Git LFS)**

**CRITICAL: These files are tracked with Git LFS**

#### Models (~205 MB)
```
LiveTalking/models/
└── wav2lip.pth                     # 205 MB - Wav2Lip model weights
```

#### Avatar Assets (~362 MB)
```
LiveTalking/data/avatars/wav2lip256_avatar1/
├── coords.pkl                      # Face coordinates
├── face_imgs/                      # 550 face images
│   ├── 00000000.png
│   ├── 00000001.png
│   └── ... (550 files)
└── full_imgs/                      # 550 full frame images
    ├── 00000000.png
    ├── 00000001.png
    └── ... (550 files)
```

**Total Size:** ~567 MB

---

### 3. **Configuration Files**

```
├── .env                            # API keys and settings (REQUIRED)
├── docker-compose.yml              # Docker orchestration
├── Dockerfile                      # Backend container
├── LiveTalking/Dockerfile.new      # Frontend container
├── .dockerignore                   # Docker build optimization
└── LiveTalking/.dockerignore
```

---

### 4. **Documentation**
```
├── README.md
├── DOCKER_DEPLOYMENT.md
├── URDU_TRANSLATION_README.md
├── URDU_TRANSLATION_IMPLEMENTATION_GUIDE.md
└── SERVER_DEPLOYMENT_GUIDE.md (this file)
```

---

## Server Requirements

### Minimum Requirements
- **OS:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU:** 4 cores
- **RAM:** 8 GB
- **Storage:** 30 GB free space
- **Network:** Public IP with open ports

### Recommended Requirements
- **OS:** Ubuntu 22.04 LTS
- **CPU:** 8 cores (or GPU)
- **RAM:** 16 GB
- **Storage:** 50 GB SSD
- **GPU:** NVIDIA GPU with 6GB+ VRAM (optional but recommended)

### Software Requirements
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **Git:** 2.30+
- **Git LFS:** 3.0+

---

## Deployment Methods

### Method 1: Docker Deployment (Recommended)
✅ Easiest and most reliable  
✅ Includes all dependencies  
✅ Production-ready  

### Method 2: Manual Installation
⚠️ More control but complex  
⚠️ Requires manual dependency management  

### Method 3: Cloud Platform (AWS/GCP/Azure)
✅ Scalable  
✅ Managed infrastructure  
⚠️ Higher cost  

---

## Step-by-Step Deployment

### Method 1: Docker Deployment (Recommended)

#### Step 1: Prepare Your Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git and Git LFS
sudo apt install git git-lfs -y
git lfs install

# Add your user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

#### Step 2: Clone Repository with Large Files

```bash
# Clone the repository
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System

# CRITICAL: Download large files with Git LFS
git lfs pull

# Verify large files are downloaded
ls -lh LiveTalking/models/wav2lip.pth
# Should show ~205 MB, not a few KB

ls -lh LiveTalking/data/avatars/wav2lip256_avatar1/coords.pkl
# Should show actual file size, not a pointer
```

**⚠️ IMPORTANT:** If you see small file sizes (< 1KB), the LFS files are not downloaded. Run `git lfs pull` again.

#### Step 3: Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

**Required Configuration:**
```env
# Google Gemini API Key (REQUIRED)
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Qdrant Configuration
QDRANT_URL=http://qdrant:6333
COLLECTION_NAME=policy_docs

# Translation Settings
ENABLE_TRANSLATION=true
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,ur

# LiveTalking Settings
CHAT_LANGUAGE=en  # Set to 'ur' for Urdu mode
```

**Get Gemini API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and paste into `.env`

#### Step 4: Deploy with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Step 5: Verify Deployment

```bash
# Check if services are running
curl http://localhost:8000/health
curl http://localhost:8010/webrtcapi.html
curl http://localhost:6333/dashboard

# Check translation is enabled
curl http://localhost:8000/languages
```

#### Step 6: Configure Firewall

```bash
# Allow necessary ports
sudo ufw allow 8000/tcp   # RAG Backend
sudo ufw allow 8010/tcp   # LiveTalking
sudo ufw allow 6333/tcp   # Qdrant (optional, for external access)
sudo ufw enable
```

#### Step 7: Access Your Application

```
http://your-server-ip:8010/webrtcapi.html
```

---

### Method 2: Manual Installation (Without Docker)

#### Step 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install system libraries
sudo apt install -y \
    build-essential \
    cmake \
    git \
    git-lfs \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libsndfile1 \
    ffmpeg

# Install Git LFS
git lfs install
```

#### Step 2: Clone Repository

```bash
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System

# Download large files
git lfs pull

# Verify files
ls -lh LiveTalking/models/wav2lip.pth
ls -lh LiveTalking/data/avatars/wav2lip256_avatar1/
```

#### Step 3: Install Qdrant

```bash
# Using Docker for Qdrant (easiest)
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

#### Step 4: Setup Backend

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your GEMINI_API_KEY

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
```

#### Step 5: Setup Frontend

```bash
cd LiveTalking

# Create virtual environment
python3.11 -m venv livetalking_env
source livetalking_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start frontend (English mode)
python app.py --transport webrtc --model wav2lip \
  --avatar_id wav2lip256_avatar1 \
  --REF_FILE en-US-JennyNeural \
  --batch_size 2 &

# Or for Urdu mode
export CHAT_LANGUAGE=ur
python app.py --transport webrtc --model wav2lip \
  --avatar_id wav2lip256_avatar1 \
  --REF_FILE ur-PK-UzmaNeural \
  --batch_size 2 &
```

---

## What You Need from Your Local Machine

### Option A: Using Git (Recommended)

**Nothing extra needed!** Just clone from GitHub:

```bash
# On server
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System
git lfs pull  # Download models and avatars
```

All files including models and avatars are in the GitHub repository via Git LFS.

---

### Option B: Manual File Transfer (If Git LFS Fails)

If Git LFS doesn't work on your server, transfer files manually:

#### Files to Transfer:

**1. Application Code (Small)**
```bash
# On your local machine, create a tarball
tar -czf app-code.tar.gz \
  main.py \
  translation_service.py \
  ingest.py \
  requirements.txt \
  .env.example \
  docker-compose.yml \
  Dockerfile \
  LiveTalking/

# Upload to server
scp app-code.tar.gz user@your-server:/path/to/deploy/
```

**2. Large Model Files (567 MB)**
```bash
# On your local machine
cd LiveTalking

# Create tarball of models
tar -czf models.tar.gz models/

# Create tarball of avatar data
tar -czf avatars.tar.gz data/avatars/

# Upload to server
scp models.tar.gz user@your-server:/path/to/deploy/LiveTalking/
scp avatars.tar.gz user@your-server:/path/to/deploy/LiveTalking/

# On server, extract
cd /path/to/deploy/LiveTalking
tar -xzf models.tar.gz
tar -xzf avatars.tar.gz
```

**3. Environment Configuration**
```bash
# Copy your .env file (with API keys)
scp .env user@your-server:/path/to/deploy/
```

---

## Configuration for Production

### 1. Environment Variables

**Backend (.env):**
```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key

# Database
QDRANT_URL=http://qdrant:6333
COLLECTION_NAME=policy_docs

# Translation
ENABLE_TRANSLATION=true
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,ur

# Production settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 2. Docker Compose for Production

Update `docker-compose.yml`:

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: always
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - ai-avatar-network

  rag-backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: rag-backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - QDRANT_URL=http://qdrant:6333
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - ENABLE_TRANSLATION=true
      - DEFAULT_LANGUAGE=en
      - SUPPORTED_LANGUAGES=en,ur
    depends_on:
      - qdrant
    networks:
      - ai-avatar-network

  livetalking:
    build:
      context: ./LiveTalking
      dockerfile: Dockerfile.new
    container_name: livetalking
    restart: always
    ports:
      - "8010:8010"
    environment:
      - RAG_BACKEND_URL=http://rag-backend:8000
      - CHAT_LANGUAGE=${CHAT_LANGUAGE:-en}
      - REF_FILE=${REF_FILE:-en-US-JennyNeural}
      - BATCH_SIZE=2
    volumes:
      - ./LiveTalking/models:/app/models
      - ./LiveTalking/data:/app/data
    depends_on:
      - rag-backend
    networks:
      - ai-avatar-network

volumes:
  qdrant_storage:

networks:
  ai-avatar-network:
    driver: bridge
```

### 3. Nginx Reverse Proxy (Optional but Recommended)

```bash
# Install Nginx
sudo apt install nginx -y

# Create configuration
sudo nano /etc/nginx/sites-available/ai-avatar
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:8010;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebRTC
    location /webrtc {
        proxy_pass http://localhost:8010/webrtc;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ai-avatar /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## SSL/HTTPS Setup (Recommended for Production)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Monitoring & Maintenance

### Check Service Status

```bash
# Docker services
docker-compose ps
docker-compose logs -f

# System resources
htop
df -h
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Translation status
curl http://localhost:8000/languages

# Qdrant status
curl http://localhost:6333/health
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart rag-backend
docker-compose restart livetalking
```

### Update Application

```bash
# Pull latest changes
git pull origin main
git lfs pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Troubleshooting

### Issue: Models not loading (File size is < 1KB)

**Cause:** Git LFS files not downloaded

**Solution:**
```bash
git lfs pull
ls -lh LiveTalking/models/wav2lip.pth  # Should be ~205 MB
```

### Issue: "GEMINI_API_KEY not found"

**Solution:**
```bash
# Check .env file exists
cat .env | grep GEMINI_API_KEY

# If missing, add it
echo "GEMINI_API_KEY=your_key_here" >> .env
```

### Issue: Port already in use

**Solution:**
```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :8010

# Kill process
sudo kill -9 <PID>
```

### Issue: Out of memory

**Solution:**
```bash
# Reduce batch size in docker-compose.yml
BATCH_SIZE=1

# Or add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Quick Deployment Checklist

- [ ] Server meets minimum requirements
- [ ] Docker and Docker Compose installed
- [ ] Git and Git LFS installed
- [ ] Repository cloned
- [ ] **Git LFS files downloaded** (`git lfs pull`)
- [ ] `.env` file configured with GEMINI_API_KEY
- [ ] Firewall ports opened (8000, 8010)
- [ ] `docker-compose up -d` executed
- [ ] Services verified with health checks
- [ ] Application accessible at `http://server-ip:8010`

---

## Summary: What You Need

### From GitHub (Automated):
✅ All application code  
✅ Models (205 MB) via Git LFS  
✅ Avatar data (362 MB) via Git LFS  
✅ Docker configuration  
✅ Documentation  

### You Must Provide:
🔑 **GEMINI_API_KEY** (from Google AI Studio)  
🖥️ **Server** with Docker installed  
🌐 **Domain name** (optional, for HTTPS)  

### Commands to Deploy:
```bash
# 1. Clone repository
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System

# 2. Download large files
git lfs pull

# 3. Configure
cp .env.example .env
nano .env  # Add GEMINI_API_KEY

# 4. Deploy
docker-compose up -d

# 5. Access
# http://your-server-ip:8010/webrtcapi.html
```

**That's it!** Your AI Avatar System with Urdu translation is deployed! 🎉
