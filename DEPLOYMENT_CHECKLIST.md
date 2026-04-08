# Server Deployment Checklist

Quick reference for deploying the AI Avatar System on a server.

---

## ✅ Pre-Deployment Checklist

### Server Setup
- [ ] Ubuntu 20.04+ or similar Linux distribution
- [ ] Minimum 8GB RAM, 4 CPU cores
- [ ] 30GB+ free disk space
- [ ] Public IP address or domain name
- [ ] SSH access configured

### Software Installation
- [ ] Docker 20.10+ installed
- [ ] Docker Compose 2.0+ installed
- [ ] Git installed
- [ ] Git LFS installed and initialized (`git lfs install`)

---

## 📦 Required Files & Assets

### What's Already on GitHub
✅ All application code (main.py, translation_service.py, etc.)  
✅ LiveTalking frontend code  
✅ Docker configuration files  
✅ Documentation  
✅ **Models (205 MB)** - via Git LFS  
✅ **Avatar data (362 MB)** - via Git LFS  

### What You Need to Provide
🔑 **GEMINI_API_KEY** - Get from https://makersuite.google.com/app/apikey  
🖥️ **Server** - With Docker installed  
🌐 **Domain** (optional) - For HTTPS/SSL  

---

## 🚀 Deployment Steps

### Step 1: Clone Repository
```bash
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System
```
- [ ] Repository cloned successfully

### Step 2: Download Large Files (CRITICAL)
```bash
git lfs pull
```
- [ ] Git LFS pull completed
- [ ] Verify: `ls -lh LiveTalking/models/wav2lip.pth` shows ~205 MB
- [ ] Verify: `ls -lh LiveTalking/data/avatars/` shows avatar files

**⚠️ WARNING:** If files are < 1KB, Git LFS didn't work. Run `git lfs pull` again.

### Step 3: Configure Environment
```bash
cp .env.example .env
nano .env
```
- [ ] `.env` file created
- [ ] `GEMINI_API_KEY` added
- [ ] Other settings configured (optional)

**Required in .env:**
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### Step 4: Configure Firewall
```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8010/tcp
sudo ufw enable
```
- [ ] Port 8000 opened (Backend)
- [ ] Port 8010 opened (Frontend)

### Step 5: Deploy with Docker
```bash
docker-compose up -d
```
- [ ] All containers started
- [ ] No errors in logs

### Step 6: Verify Deployment
```bash
# Check services
docker-compose ps

# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost:8010/webrtcapi.html
```
- [ ] All services show "Up" status
- [ ] Backend health check returns OK
- [ ] Frontend accessible

### Step 7: Test Application
```
http://your-server-ip:8010/webrtcapi.html
```
- [ ] Web interface loads
- [ ] Can start session
- [ ] Avatar responds to queries
- [ ] Translation works (if enabled)

---

## 🔍 Verification Commands

### Check Service Status
```bash
docker-compose ps
```
Expected: All services "Up" and "healthy"

### Check Logs
```bash
docker-compose logs -f
```
Look for: "Initialization complete!" and no errors

### Test Backend API
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok","translation_enabled":true}`

### Test Translation
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is NIRA?","language":"en"}'
```
Expected: JSON response with answer

### Check Large Files
```bash
ls -lh LiveTalking/models/wav2lip.pth
ls -lh LiveTalking/data/avatars/wav2lip256_avatar1/coords.pkl
```
Expected: Real file sizes (not < 1KB)

---

## 🌐 Access URLs

After deployment, access:

- **Avatar Interface:** `http://your-server-ip:8010/webrtcapi.html`
- **Dashboard:** `http://your-server-ip:8010/dashboard.html`
- **API Docs:** `http://your-server-ip:8000/docs`
- **Qdrant:** `http://your-server-ip:6333/dashboard`

---

## 🔧 Common Issues & Solutions

### Issue: Models not loading
**Symptom:** File size < 1KB  
**Solution:** 
```bash
git lfs pull
```

### Issue: "GEMINI_API_KEY not found"
**Solution:**
```bash
echo "GEMINI_API_KEY=your_key" >> .env
docker-compose restart
```

### Issue: Port already in use
**Solution:**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

### Issue: Container won't start
**Solution:**
```bash
docker-compose logs <service-name>
docker-compose down
docker-compose up -d
```

---

## 🎯 Quick Commands Reference

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart
```

### View Logs
```bash
docker-compose logs -f
docker-compose logs -f rag-backend
docker-compose logs -f livetalking
```

### Update Application
```bash
git pull origin main
git lfs pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📊 Resource Requirements

### Minimum
- CPU: 4 cores
- RAM: 8 GB
- Disk: 30 GB
- Network: 10 Mbps

### Recommended
- CPU: 8 cores (or GPU)
- RAM: 16 GB
- Disk: 50 GB SSD
- Network: 100 Mbps

### With GPU (Optional)
- NVIDIA GPU with 6GB+ VRAM
- CUDA 11.8+
- NVIDIA Docker runtime

---

## 🔐 Security Checklist

- [ ] `.env` file not committed to Git
- [ ] Firewall configured (only necessary ports open)
- [ ] SSL/HTTPS configured (for production)
- [ ] Strong passwords for server access
- [ ] Regular security updates applied
- [ ] API keys rotated periodically

---

## 📝 Environment Variables

### Required
```env
GEMINI_API_KEY=your_key_here
```

### Optional
```env
# Translation
ENABLE_TRANSLATION=true
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,ur
CHAT_LANGUAGE=en

# Database
QDRANT_URL=http://qdrant:6333
COLLECTION_NAME=policy_docs

# Performance
BATCH_SIZE=2
```

---

## 🎬 For Urdu Mode

Set in `.env`:
```env
CHAT_LANGUAGE=ur
```

Update `docker-compose.yml`:
```yaml
livetalking:
  environment:
    - REF_FILE=ur-PK-UzmaNeural  # Urdu female voice
    - CHAT_LANGUAGE=ur
```

Restart:
```bash
docker-compose restart livetalking
```

---

## ✅ Final Checklist

Before going live:

- [ ] All services running and healthy
- [ ] Health checks passing
- [ ] Test queries working
- [ ] Translation tested (if enabled)
- [ ] Firewall configured
- [ ] SSL/HTTPS configured (production)
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Documentation reviewed

---

## 📞 Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Review: `SERVER_DEPLOYMENT_GUIDE.md`
3. Check: `DOCKER_DEPLOYMENT.md`
4. GitHub Issues: https://github.com/NTISPAK/RAG-Based-AI--Avatar-System/issues

---

**Deployment Time:** ~15-30 minutes  
**Difficulty:** Easy (with Docker)  
**Status:** Production Ready ✅
