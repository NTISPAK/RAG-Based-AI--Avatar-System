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

## 2. Start Qdrant

```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:latest
```

## 3. Ingest Documents (first time or after doc changes)

```bash
cd backend/rag
python ingest.py
```

## 4. Start the RAG Backend

```bash
cd backend/rag
python -m uvicorn main:app --reload --port 8000
```

## 5. Start the Avatar Server

In a **second terminal**:

```bash
cd backend
python app.py --model musetalk --avatar_id musetalk_avatar1 --batch_size 8 --tts edgetts --REF_FILE en-IN-NeerjaNeural --transport webrtc
```

## 6. Open the Frontend

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
