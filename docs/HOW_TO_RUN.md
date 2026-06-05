# How to Run

Step-by-step guide to start the NTIS AI Avatar system after the restructure.

## Prerequisites

- Python 3.11
- Docker (for Qdrant)
- Google Gemini API key
- Model files already in `backend/models/` and avatars in `backend/data/avatars/`

## 1. Environment Setup

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
```

## 2. Install Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate

# Install PyTorch first (pick your platform)
# macOS:
pip install torch torchvision torchaudio
# NVIDIA CUDA 12.4:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
# CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install everything else
pip install -r requirements.txt
```

## 3. Download AI Models

This downloads the large model weights (MuseTalk, SD-VAE, Whisper, etc.).

```bash
python scripts/download_models.py
```

**What you still need to handle:**
- **Wav2Lip checkpoint** — Run the dedicated script:
  ```bash
  python scripts/download_wav2lip.py
  ```
  If automatic download fails, it will print manual instructions.
- **Avatar data** — Copy your existing `backend/data/avatars/` folder from your current PC, **OR** generate a new avatar from a video:
  ```bash
  python scripts/generate_avatar.py --video custom-videos/indian-female.mp4 --avatar_id indian_female
  ```
  This checks models, extracts frames, detects faces, encodes latents, and saves everything to `backend/data/avatars/indian_female/`.

> **Note:** Model weights and avatar data are excluded from Git because they are very large. Do not commit them.

## 4. Start Qdrant

```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:latest
```

## 5. Ingest Documents (first time or after doc changes)

```bash
cd backend/rag
python ingest.py
```

## 6. Start the RAG Backend

```bash
cd backend/rag
python -m uvicorn main:app --reload --port 8000
```

## 7. Start the Avatar Server

In a **second terminal**:

```bash
cd backend
python app.py --model musetalk --avatar_id indian_female --batch_size 8 --tts edgetts --REF_FILE en-IN-NeerjaNeural --transport webrtc
```

## 8. Open the Frontend

Navigate to: **http://localhost:8010/webrtcapi.html**

## Alternative: Pre-render Mode

If real-time inference is too slow (e.g., on Mac MPS), use the **Pre-render** toggle in the UI. This generates a full MP4 video via the `/render_video` endpoint instead of streaming live.

## Common Issues

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run from `backend/` or `backend/rag/`, not project root |
| `Could not connect to RAG backend` | Ensure port 8000 server is running |
| Slow on Mac | Lower `--batch_size 2` or use pre-render mode |
| Qdrant not found | `docker run -p 6333:6333 qdrant/qdrant` |
| Missing models | Run `python scripts/download_models.py` |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐     ┌─────────┐
│   Browser   │◄───►│ Avatar Server│────►│ RAG Backend│────►│ Qdrant  │
│  :8010      │     │   :8010      │     │   :8000   │     │ :6333   │
└─────────────┘     └──────────────┘     └──────────┘     └─────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Google Gemini│
                    └──────────────┘
```
