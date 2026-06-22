# RAG-Based AI Avatar System — Complete Run Guide

A real-time AI avatar system powered by MuseTalk (diffusion-based lip-sync), Google Gemini RAG, and WebRTC streaming. Supports real-time WebRTC streaming and pre-rendered video generation for low-latency playback.

## Architecture

```
+-------------+     +--------------+     +-------------+     +---------+
|   Browser   |<--->| Avatar Server|---->| RAG Backend |---->| Qdrant  |
| :8010       |     |   :8010      |     |   :8000     |     | :6333   |
+-------------+     +--------------+     +-------------+     +---------+
                             |
                             v
                     +---------------+
                     | Google Gemini |
                     +---------------+
```

- **Avatar Server** (`:8010`) — MuseTalk inference, WebRTC, TTS, serves frontend
- **RAG Backend** (`:8000`) — Document Q&A via Gemini + Qdrant vector search
- **Qdrant** (`:6333`) — Vector database for document embeddings

## Prerequisites

- Python 3.11
- Docker (for Qdrant)
- Google Gemini API key
- FFmpeg installed system-wide
- Model weights in `backend/models/` (see download step below)
- Avatar data in `backend/data/avatars/` (see generation step below)

## 1. Environment Setup

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
cat .env
```

**Required `.env` variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | `AIza...` |
| `QDRANT_URL` | Qdrant endpoint | `http://localhost:6333` |
| `COLLECTION_NAME` | Vector collection name | `policy_docs` |
| `ENABLE_TRANSLATION` | Enable Urdu translation | `true` |
| `DEFAULT_LANGUAGE` | Default chat language | `ur` |
| `SUPPORTED_LANGUAGES` | Comma-separated langs | `en,ur` |

## 2. Install Dependencies

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# Install PyTorch (pick your platform)
# macOS:
pip install torch torchvision torchaudio

# NVIDIA CUDA 12.4:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install all other dependencies
pip install -r requirements.txt
```

## 3. Download AI Models

```bash
# From project root
python scripts/download_models.py
```

This downloads:
- MuseTalk UNet (`musetalkV15/unet.pth` ~3.2 GB)
- SD-VAE (`sd-vae-ft-mse/`)
- Whisper (`whisper/tiny.pt`)
- Face Parsing (`face-parse-bisent/79999_iter.pth`)

If any download fails, run the fix script:

```bash
python scripts/download_models_fix.py
```

## 4. Generate an Avatar

Place a source video in `custom-videos/` (5-30 seconds, face clearly visible, minimal head movement).

```bash
python scripts/generate_avatar.py \
    --video custom-videos/indian-female.mp4 \
    --avatar_id indian_female
```

Output: `backend/data/avatars/<avatar_id>/`
- `full_imgs/` — extracted video frames
- `mask/` — face parsing masks
- `coords.pkl` — face bounding boxes
- `mask_coords.pkl` — mask crop coordinates
- `latents.pt` — VAE-encoded face latents
- `avator_info.json` — metadata

### Optional: Replace Green Screen Background

If your source video has a green screen:

```bash
python scripts/replace_background.py \
    --avatar_id indian_female \
    --background /path/to/office-background.jpg \
    --backup --preview
```

Re-run without `--preview` to apply to all frames.

## 5. Start Qdrant (Vector DB)

### Option A: Docker (recommended)

```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:latest
```

Or use docker-compose:

```bash
docker-compose up -d qdrant
```

### Option B: Docker Compose (Qdrant + RAG Backend)

```bash
docker-compose up -d
```

This starts both Qdrant (`:6333`) and the RAG backend (`:8000`) in containers.

Verify Qdrant is running:

```bash
curl http://localhost:6333/health
```

## 6. Ingest RAG Documents

Place `.docx` files in `backend/rag/documents/`, then:

```bash
cd backend/rag
python ingest.py
```

This chunks the documents, generates embeddings, and stores them in Qdrant under the `policy_docs` collection.

Re-run whenever documents change.

## 7. Start the RAG Backend

### Option A: Native Python (local dev)

```bash
cd backend/rag
python -m uvicorn main:app --reload --port 8000
```

### Option B: Docker (if not using docker-compose)

```bash
docker build -t rag-backend .
docker run -d -p 8000:8000 --env-file .env rag-backend
```

### Option C: Docker Compose (already running)

If you ran `docker-compose up -d` in step 5, the RAG backend is already running on `:8000`.

Verify:

```bash
curl http://localhost:8000/health
```

## 8. Start the Avatar / WebRTC Server

```bash
cd backend
source .venv/bin/activate

# Full command with all options explained
python app.py \
    --model musetalk \
    --avatar_id indian_female \
    --batch_size 8 \
    --tts edgetts \
    --REF_FILE ur-PK-UzmaNeural \
    --transport webrtc \
    --listenport 8010
```

### CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `musetalk` | Model type (`musetalk`, `wav2lip`) |
| `--avatar_id` | `avator_1` | Avatar folder in `data/avatars/` |
| `--batch_size` | `16` | Inference batch size (lower = less VRAM) |
| `--tts` | `edgetts` | TTS engine (`edgetts`) |
| `--REF_FILE` | `ur-PK-UzmaNeural` | Edge TTS voice ID |
| `--transport` | `rtcpush` | Transport (`webrtc`, `rtcpush`, `rtmp`) |
| `--listenport` | `8010` | HTTP/WebRTC server port |
| `--max_session` | `1` | Max concurrent WebRTC sessions |
| `--fps` | `50` | Audio FPS (must be 50) |
| `--W` / `--H` | `450` | GUI dimensions |

**VRAM tuning:**
- GTX 1660 (6 GB): `--batch_size 4`
- RTX 3060 (12 GB): `--batch_size 8`
- RTX 4090 (24 GB): `--batch_size 16`

## 9. Open the Frontend

Navigate to:

```
http://localhost:8010/webrtcapi.html
```

Or the dashboard:

```
http://localhost:8010/dashboard.html
```

### UI Toggles

- **Test Mode** — Echoes your input text (default: off)
- **Pre-render Mode** — Generates full MP4 video instead of live WebRTC stream. Queries RAG backend for chat answers before TTS. Use this if real-time inference is too slow.

## Docker Quick Reference

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f rag-backend
docker-compose logs -f qdrant

# Stop everything
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild RAG backend after code changes
docker-compose build rag-backend
docker-compose up -d rag-backend
```

## Complete Startup Sequence

```bash
# Terminal 1: Qdrant
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:latest

# Terminal 2: RAG Backend
cd backend/rag
python -m uvicorn main:app --reload --port 8000

# Terminal 3: Avatar Server
cd backend
python app.py --model musetalk --avatar_id indian_female --batch_size 8 --tts edgetts --REF_FILE ur-PK-UzmaNeural --transport webrtc --listenport 8010

# Browser: http://localhost:8010/webrtcapi.html
```

## Project Structure

```
backend/
  app.py                    # Main avatar/WebRTC server
  llm.py                    # RAG query client
  musereal.py               # MuseTalk real-time inference
  generate_musetalk_avatar.py # Avatar generation core
  musetalk/                 # MuseTalk models & utilities
  data/
    avatars/<id>/           # Avatar frames, latents, masks
  models/                   # Downloaded model weights
  rag/
    main.py                 # FastAPI RAG backend
    ingest.py               # Document ingestion
    translation_service.py  # Urdu translation
    documents/              # Source .docx files
  requirements.txt

frontend/src/
  webrtcapi.html            # Main UI
  dashboard.html            # Alternative dashboard

custom-videos/              # Source videos for avatar generation
scripts/
  generate_avatar.py        # Avatar generation wrapper
  replace_background.py     # Chroma-key background replacement
  download_models.py        # Model downloader
  download_models_fix.py    # Fallback downloader
  docker-start.sh           # Docker startup helper
  start_project.sh          # Native startup helper

docker-compose.yml          # Qdrant + RAG backend
Dockerfile                  # RAG backend image
.env.example                # Environment template
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run from `backend/` or `backend/rag/`, not project root |
| `Could not connect to RAG backend` | Ensure port 8000 server is running |
| Slow on Mac / stuttering WebRTC | Lower `--batch_size 2` or use **Pre-render Mode** |
| Qdrant not found | `docker run -p 6333:6333 qdrant/qdrant` |
| Missing models | Run `python scripts/download_models.py` |
| Windows OOM during prerender | Already fixed: frames stream directly to video writer instead of RAM. Pull latest code. |
| Green screen in avatar | Run `scripts/replace_background.py` with `--preview` first |
