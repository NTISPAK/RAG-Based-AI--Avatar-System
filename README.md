# NTIS Policy RAG with LiveTalking Digital Human

A Retrieval-Augmented Generation (RAG) system integrated with a real-time lip-synced digital human avatar for answering NTIS policy questions.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

- ✅ **Real-time Digital Human** – MuseTalk/Wav2Lip lip-sync animation
- ✅ **WebRTC Video Streaming** – Low-latency video to browser
- ✅ **Semantic RAG** – Qdrant + LangChain for policy document retrieval
- ✅ **Gemini LLM** – Google Gemini 2.5 Flash for answer generation
- ✅ **Anti-hallucination guardrails** – "Not in document" fallback enforced
- ✅ **Urdu Translation** – Full Urdu chat support with Edge-TTS voices
- ✅ **Pre-render Mode** – Generate full MP4 videos offline for slower hardware

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (for Qdrant)
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))
- Model files downloaded (see [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md))

### Run (2 Terminals)

**Terminal 1 – RAG Backend (port 8000):**
```bash
cd backend/rag
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2 – Avatar Server (port 8010):**
```bash
cd backend
python app.py --model musetalk --avatar_id musetalk_avatar1 --batch_size 8 --tts edgetts --REF_FILE en-IN-NeerjaNeural --transport webrtc
```

**Open:** http://localhost:8010/webrtcapi.html

For full details, see [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md).

## 📁 Project Structure

```
RAG-Based-AI--Avatar-System/
├── backend/                   # All Python backend code
│   ├── app.py                 # Avatar aiohttp server (port 8010)
│   ├── llm.py                 # Calls RAG backend over HTTP
│   ├── musereal.py            # MuseTalk real-time inference
│   ├── ttsreal.py             # TTS streaming (edge-tts, Azure, etc.)
│   ├── requirements.txt       # All backend dependencies
│   ├── models/                # Model weights (.pth, SD-VAE, Whisper)
│   ├── data/avatars/          # Avatar precomputed latents & frames
│   ├── data/videos/           # Rendered MP4 output
│   └── rag/                   # RAG FastAPI backend (port 8000)
│       ├── main.py
│       ├── ingest.py
│       └── translation_service.py
├── frontend/                  # HTML/JS frontend
│   ├── src/webrtcapi.html     # Main chat interface
│   ├── src/dashboard.html     # Dashboard
│   └── js/client.js           # WebRTC client
├── docs/                      # Documentation
│   └── HOW_TO_RUN.md          # Step-by-step run guide
├── scripts/
│   └── restructure.py         # One-time restructure script
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **RAG Backend** | FastAPI + LangChain + Qdrant |
| **LLM** | Google Gemini 2.5 Flash |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` |
| **Avatar Engine** | MuseTalk / Wav2Lip / Ultralight |
| **Web Server** | aiohttp (static + WebRTC + API) |
| **TTS** | Edge-TTS / Azure Speech |
| **Video** | WebRTC (aiortc) + OpenCV |
| **Diffusion** | PyTorch + diffusers |

## 📖 How It Works

```
Browser → Avatar Server (8010) → RAG Backend (8000) → Qdrant + Gemini → Response
                                            ↓
                                    TTS + Lip-sync → WebRTC → Browser
```

1. User types a question in the web UI
2. Avatar server proxies it to the RAG backend at `localhost:8000/chat`
3. RAG backend retrieves relevant policy chunks from Qdrant
4. Gemini LLM generates an answer grounded in the retrieved context
5. Answer is streamed back, split into TTS chunks, and lip-synced in real time
6. WebRTC delivers synchronized audio+video to the browser

## 🔧 Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | *(required)* |
| `QDRANT_URL` | Qdrant endpoint | `http://localhost:6333` |
| `COLLECTION_NAME` | Vector collection | `policy_docs` |
| `RAG_BACKEND_URL` | URL the avatar uses to reach RAG | `http://127.0.0.1:8000` |
| `CHAT_LANGUAGE` | Chat language (`en` or `ur`) | `en` |

## 🐳 Docker (RAG Backend Only)

The Docker setup currently covers the RAG backend. The avatar server requires GPU access and large model files that are best run natively.

```bash
# RAG backend only
docker-compose up -d qdrant rag-backend
```

## � Troubleshooting

| Issue | Fix |
|-------|-----|
| Qdrant connection error | `docker run -p 6333:6333 qdrant/qdrant` |
| `Could not connect to RAG backend` | Start the RAG backend on port 8000 first |
| Avatar server import errors | Run from `backend/` directory, not project root |
| Slow inference on Mac | Use `--batch_size 2` or switch to pre-render mode |

## 📚 Documentation

- **[HOW_TO_RUN.md](docs/HOW_TO_RUN.md)** – Full step-by-step setup & run guide
- **[SETUP.md](SETUP.md)** – Production restructure & fresh-machine setup
- **[DOCKER_QUICK_START.md](docs/DOCKER_QUICK_START.md)** – Docker deployment notes
- **[URDU_TRANSLATION_README.md](docs/URDU_TRANSLATION_README.md)** – Urdu chat setup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push and open a Pull Request

## 📝 License

MIT License

---

**Made with ❤️ for NTIS**
