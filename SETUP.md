# Setup Guide

## Project Structure

```
RAG-Based-AI--Avatar-System/
├── backend/                    # All Python backend code
│   ├── requirements.txt       # Backend dependencies
│   ├── app.py                 # Avatar aiohttp server (port 8010)
│   ├── llm.py                 # Calls RAG backend over HTTP
│   ├── musereal.py            # MuseTalk real-time inference
│   ├── ttsreal.py             # TTS streaming
│   ├── models/                # Model weights (.pth, SD-VAE, Whisper)
│   ├── data/avatars/          # Avatar precomputed latents & frames
│   ├── data/videos/           # Rendered MP4 output
│   └── rag/                   # RAG FastAPI backend (port 8000)
│       ├── main.py
│       ├── ingest.py
│       └── translation_service.py
├── frontend/                  # HTML/JS frontend (served by backend)
│   ├── src/                   # HTML pages
│   └── js/                    # JavaScript libraries
├── docs/
│   └── HOW_TO_RUN.md          # Quick run guide
├── scripts/
│   ├── download_models.py     # Download AI model weights
│   ├── download_wav2lip.py  # Download Wav2Lip checkpoint
│   ├── generate_avatar.py     # Generate avatar from video
│   └── restructure.py         # One-time restructure automation
├── custom-videos/             # Committed source videos for avatar generation
├── .env.example               # Environment template
└── README.md
```

## Fresh Machine Setup

### 1. Clone

```bash
git clone https://github.com/NTISPAK/RAG-Based-AI--Avatar-System.git
cd RAG-Based-AI--Avatar-System
```

### 2. Environment

```bash
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY
```

### 3. Virtual Environment & Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install PyTorch first (pick your platform)
# NVIDIA CUDA 12.4:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
# macOS CPU/MPS:
pip install torch torchvision torchaudio
# CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install everything else
pip install -r requirements.txt
```

### 4. Download AI Models

```bash
python scripts/download_models.py
```

**Manual steps still needed:**
- **Wav2Lip checkpoint** — Download with the script:
  ```bash
  python scripts/download_wav2lip.py
  ```
  (If automatic download fails, it prints manual instructions.)
- **Avatar data** — Copy `backend/data/avatars/` from your existing PC, or regenerate:
  ```bash
  python scripts/generate_avatar.py --video custom-videos/indian-female.mp4 --avatar_id indian_female
  ```

### 5. Ingest Documents

```bash
cd rag
python ingest.py
```

### 6. Run (2 Terminals)

**Terminal 1 — RAG Backend:**
```bash
cd backend/rag
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Avatar Server:**
```bash
cd backend
python app.py --model musetalk --avatar_id indian_female --batch_size 8 --tts edgetts --REF_FILE en-IN-NeerjaNeural --transport webrtc
```

Open: http://localhost:8010/webrtcapi.html
