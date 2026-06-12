# Technical & Functional Specification

## Project Overview

A real-time AI avatar system featuring a **single virtual spokesperson** displayed on one screen. The avatar communicates with authorized personnel (CEO, HR, Tech Team, Visa Team, etc.) by identifying the speaker and routing queries to the appropriate department knowledge base. Built on a RAG (Retrieval-Augmented Generation) backend powered by Google Gemini, with documents stored in a Qdrant vector database. Supports both live WebRTC streaming and pre-rendered video generation.

---

## What the Avatar Uses

### Core Engine: MuseTalk

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Architecture** | Latent Diffusion UNet | Generates realistic lip movements from audio |
| **Input** | Mel-spectrogram + VAE latents + audio features | Conditions the diffusion model on speech |
| **Audio Encoder** | OpenAI Whisper (tiny) | Extracts phonetic/audio features from TTS output |
| **VAE** | SD-VAE-ft-mse | Encodes/decodes face image latents |
| **Face Detection** | S3FD (Single Shot Scale-invariant Face Detector) | Locates face bounding boxes in frames |
| **Face Parsing** | BiSeNet (79999_iter.pth) | Segments face regions (jaw, lips, skin) for masking |
| **Blending** | Gaussian blur + alpha compositing | Seamlessly merges generated mouth onto original face |
| **TTS** | Microsoft Edge TTS (via edge-tts library) | Converts text answers to speech |
| **Output** | 720x1280 BGR frames at 25 FPS | Streamed via WebRTC or written to MP4 |

### Avatar Data Pipeline

```
Source Video (5-30s)
    |
    v
+---------------+     +---------------+     +---------------+
| Frame Extract | --> | Face Detect   | --> | Face Parse    |
| (OpenCV)      |     | (S3FD)        |     | (BiSeNet)     |
+---------------+     +---------------+     +---------------+
                                                      |
    +-------------------------------------------------+
    v
+---------------+     +---------------+
| VAE Encode    | --> | Save Latents  |
| (sd-vae-ft)   |     | (latents.pt)  |
+---------------+     +---------------+
```

**Pre-computed per avatar:**
- `full_imgs/` — Extracted frames from source video
- `coords.pkl` — Face bounding boxes per frame
- `mask/` — Face parsing masks per frame
- `mask_coords.pkl` — Mask crop coordinates
- `latents.pt` — VAE-encoded face latents for diffusion input
- `avator_info.json` — Metadata (fps, bbox_shift, etc.)

### Real-Time Inference Loop

```
Audio Chunk (TTS output)
    |
    v
[Whisper] --> Audio Features
    |
    v
[Latent Lookup] --> Pre-encoded VAE latents (avatar-specific)
    |
    v
[UNet Diffusion] --> Predicted latent noise
    |
    v
[VAE Decode] --> Face image with new mouth
    |
    v
[Resize + Blend] --> Mouth region composited onto original frame
    |
    v
[WebRTC Send] --> Streamed to browser
```

### GPU/CPU Offloading

- Diffusion inference (UNet + VAE) runs on GPU (CUDA or MPS)
- Frame blending and compositing runs on CPU (OpenCV)
- Blocking operations offloaded to thread executor to prevent asyncio event loop blocking
- Periodic `gc.collect()` + `torch.cuda.empty_cache()` every 50 batches during prerender

---

## What the Backend Uses

### RAG Backend (`backend/rag/`)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI (uvicorn) | HTTP API server |
| **LLM** | Google Gemini (flash-1.5) | Generates answers from retrieved context |
| **Embeddings** | HuggingFace (sentence-transformers/all-MiniLM-L6-v2) | Converts text to dense vectors |
| **Vector DB** | Qdrant | Stores and searches document embeddings |
| **Document Loader** | python-docx | Reads `.docx` policy documents |
| **Chunking** | LangChain RecursiveCharacterTextSplitter | Splits documents into searchable chunks |
| **Translation** | Custom translation service | Urdu-English bidirectional translation |
| **WebSocket** | FastAPI native | Streams RAG answers in real-time to avatar |

### RAG Query Flow

```
User Question
    |
    v
[Embedding Model] --> Dense Vector
    |
    v
[Qdrant Search] --> Top-K relevant chunks
    |
    v
[Prompt Builder] --> "Context: ... Question: ..."
    |
    v
[Google Gemini] --> Generated Answer
    |
    v
[Sentence Splitter] --> TTS-friendly chunks
    |
    v
[Edge TTS] --> Audio stream to avatar
```

### Avatar Server (`backend/app.py`)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | aiohttp (async HTTP + WebSocket) | Serves frontend, handles API routes |
| **WebRTC** | aiortc | Peer-to-peer video/audio streaming |
| **Video Codec** | H.264 (via ffmpeg + OpenCV) | Encodes output frames for WebRTC or MP4 |
| **Audio** | pydub + soundfile | Processes TTS audio, resampling, mixing |
| **Session Management** | asyncio + RTCPeerConnection | Manages WebRTC sessions |

---

## All Current Functions

### 1. Real-Time WebRTC Streaming
- User speaks/types question
- RAG backend retrieves answer from policy documents
- Answer chunked into sentences and fed to Edge TTS
- TTS audio drives MuseTalk diffusion inference
- Generated frames streamed live to browser via WebRTC

### 2. Pre-Render Mode
- User submits question via frontend toggle
- Full RAG answer fetched synchronously before any generation
- Complete MP4 video generated server-side with audio muxed via ffmpeg
- Video file served to frontend for playback
- No real-time inference pressure — works on lower-end hardware

### 3. Text-to-Speech (TTS)
- Supports multiple Edge TTS voices (English, Hindi, Urdu, etc.)
- Voice configurable via `--REF_FILE` CLI flag
- Audio cached to prevent redundant generation

### 4. RAG Document Q&A
- Upload `.docx` policy documents to `backend/rag/documents/`
- Run `ingest.py` to chunk, embed, and store in Qdrant
- Avatar automatically queries RAG backend for answers
- Falls back to Gemini general knowledge if no document match

### 5. Language Support
- **English** (default) — Full RAG + TTS support
- **Urdu** — Translation service converts user input/output
- Extensible to other languages via `--REF_FILE` and translation config

### 6. Avatar Management
- Generate new avatar from any video file
- Replace green screen background with static image (chroma key)
- Backup original frames before modification
- Preview mode for background replacement

### 7. WebRTC Session Handling
- Multiple transport modes: `webrtc`, `rtcpush`, `rtmp`
- Automatic ICE candidate handling
- Session timeout and cleanup
- Test Mode (echo) for debugging

### 8. Memory Management (Windows Optimized)
- Frames stream directly to video writer instead of accumulating in RAM
- `MemoryError` catch with fallback to original frame
- Periodic garbage collection and CUDA cache clearing
- Prevents OOM on 6GB VRAM GPUs during long renders

---

## Future Roadmap

### Phase 1: Local LLM (Qwen3 14B)

Replace Google Gemini API dependency with a locally hosted **Qwen3 14B** model:

| Change | Impact |
|--------|--------|
| **No API key required** | Fully offline, zero external dependencies for inference |
| **Lower latency** | No network round-trip to Google servers |
| **Data privacy** | Sensitive policy documents never leave local infrastructure |
| **Hardware requirement** | Requires 24-32 GB VRAM (RTX 4090 / A6000) or CPU offloading |
| **Integration** | vLLM or llama.cpp server exposed on local port; RAG backend switched to local endpoint |

**Architecture change:**
```
Current:  RAG Backend --> Google Gemini API (cloud)
Future:   RAG Backend --> Qwen3 14B (vLLM/llama.cpp) <-- local GPU
```

### Phase 2: HR-Employee Communication Bridge

The avatar will become an **active intermediary** between HR and employees:

| Feature | Description |
|---------|-------------|
| **Unified Interface** | One avatar on one screen serves all employees and external customers. No separate avatars per department. |
| **Employee Direct Chat** | Employees (HR, Tech, Visa, etc.) message the avatar. It identifies their role via facial recognition or login, then queries the correct department RAG corpus and replies instantly. |
| **Customer-to-HR Relay** | External customer queries received via web/email are summarized by the avatar and forwarded to the appropriate department (Visa Team, Tech Support, etc.). |
| **HR-to-Employee Broadcast** | HR or department heads send announcements; the avatar generates personalized video messages for each recipient (e.g., "Hi [Name], your leave request has been approved"). |
| **Ticketing Integration** | Complex issues auto-generate support tickets in HRMS (e.g., BambooHR, Workday) with full conversation context and route to the correct team lead. |

### Phase 3: Receptionist Intelligence

The avatar's **primary role is receptionist** — greeting visitors, answering customer questions, and routing inquiries. Facial recognition and employee features exist purely to help the receptionist serve customers better:

| Feature | Description |
|---------|-------------|
| **Visitor Recognition** | Camera identifies walk-in customers or returning visitors. The avatar greets them by name ("Welcome back, Mr. Khan. Shall I continue your visa application?") and loads their case history. |
| **Employee Escort** | When a staff member (HR, Tech, Visa Team) approaches, the avatar recognizes them, switches to internal mode, and allows them to update policies, check customer queues, or broadcast announcements — all without leaving the reception desk. |
| **Frustration Detection** | Analyzes facial expressions of waiting customers. If someone appears confused or angry, the avatar immediately escalates to a human receptionist or the relevant department head. |
| **Access Control** | Unregistered visitors get a generic welcome and basic FAQ. Registered customers and staff get personalized, context-aware service. |
| **Attendance Logging** | Recognizes staff and logs their presence automatically — one less task for the human receptionist to handle. |

**Technology stack:**
- **Face embedding**: InsightFace or DeepFace (ArcFace model)
- **Database**: SQLite or Qdrant for face vectors
- **Real-time detection**: MediaPipe Face Mesh or RetinaFace
- **Training**: One-shot learning from a single photo

### Phase 4: Smart Reception Hub

The avatar becomes a **smart reception desk** — the first point of contact for everyone entering the office. Internal features support its customer-facing mission:

| Feature | Description |
|---------|-------------|
| **Single Receptionist, Many Hats** | The same virtual receptionist greets customers, helps staff with internal queries, and routes messages — all from one screen at the front desk. |
| **Customer-to-Department Relay** | A customer asks about a technical issue; the avatar summarizes the request and sends a video briefing to the Tech Team lead, then informs the customer that help is on the way. |
| **Staff Announcements** | HR or the CEO can ask the avatar to broadcast a message (e.g., "The visa team is running 10 minutes behind schedule") to waiting customers via the reception screen. |
| **Human Handoff** | When the avatar cannot answer, detects a frustrated customer, or receives a VIP arrival alert, it immediately calls over the human receptionist or the right department head. |
| **Multi-Modal Customer Intake** | Customers can show a photo of a document, speak in Urdu, or type their query — the avatar handles all inputs at the reception desk. |

---

## Hardware Requirements

### Current (Gemini API + MuseTalk)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **GPU** | GTX 1660 (6 GB) | RTX 3060 (12 GB) |
| **RAM** | 16 GB | 32 GB |
| **Storage** | 50 GB (models + avatars) | 100 GB |
| **OS** | Windows 10 / Ubuntu 20.04 / macOS 13 | Windows 11 / Ubuntu 22.04 |

### Future (Qwen3 14B Local)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **GPU** | RTX 3090 (24 GB) | RTX 4090 (24 GB) or A6000 (48 GB) |
| **RAM** | 32 GB | 64 GB |
| **Storage** | 100 GB | 200 GB |
| **CPU** | 8 cores | 16 cores (for concurrent vLLM workers) |

---

## API Endpoints

### Avatar Server (`:8010`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/offer` | POST | WebRTC SDP offer exchange |
| `/human` | POST | Submit text/audio for real-time streaming |
| `/render_video` | POST | Generate pre-rendered MP4 video |
| `/videos/<name>` | GET | Serve generated MP4 files |
| `/webrtcapi.html` | GET | Main frontend |
| `/dashboard.html` | GET | Alternative dashboard |

### RAG Backend (`:8000`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Query RAG with user message, stream answer |
| `/health` | GET | Health check |
| `/ingest` | POST | Trigger document re-ingestion (optional) |

---

## Data Flow Summary

```
Employee/Customer
       |
       v
[Browser] --> WebRTC/HTTP --> [Avatar Server :8010]
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
            [MuseTalk GPU]                  [RAG Backend :8000]
            (Diffusion + VAE)                      |
                    |                          [Qdrant :6333]
                    v                               |
            [WebRTC Stream]                  [Google Gemini]
                    |                        (Future: Qwen3 14B)
                    v
              [Browser Playback]
```

---

## Files and Their Roles

| File | Role |
|------|------|
| `backend/app.py` | Main server — WebRTC, HTTP routing, video rendering |
| `backend/llm.py` | RAG client — calls backend, chunks answers for TTS |
| `backend/musereal.py` | MuseTalk real-time inference loop |
| `backend/generate_musetalk_avatar.py` | Avatar preprocessing (frames, latents, masks) |
| `backend/rag/main.py` | FastAPI RAG server — Qdrant query + Gemini generation |
| `backend/rag/ingest.py` | Document ingestion — chunk, embed, store |
| `backend/rag/translation_service.py` | Urdu-English translation |
| `scripts/generate_avatar.py` | CLI wrapper for avatar generation |
| `scripts/replace_background.py` | Chroma-key background replacement |
| `scripts/download_models.py` | Downloads all model weights |
| `frontend/src/webrtcapi.html` | Main user interface |
| `docker-compose.yml` | Qdrant + RAG backend containers |
| `Dockerfile` | RAG backend container image |
