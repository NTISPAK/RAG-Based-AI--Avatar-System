# NIRA AI Avatar System — Comprehensive Project Document

**Project:** RAG-Based AI Avatar for NIRA (National Database & Registration Authority)  
**Repository:** `NTISPAK/RAG-Based-AI--Avatar-System`  
**Last Updated:** June 2026  
**Status:** Active Development (Production-Ready Backend, Avatar Quality In Progress)

---

## 1. Executive Summary

This project is a **Retrieval-Augmented Generation (RAG)** AI chatbot system that provides a real-time talking avatar interface for NIRA policy queries. Users can interact in **English and Urdu**, receiving spoken responses from a realistic animated avatar. The system combines vector document search, Google's Gemini 2.5 Flash LLM, and real-time neural lip-sync for an immersive user experience.

### Key Capabilities
- **Document Q&A:** Answers questions based on uploaded NIRA policy documents (DOCX)
- **Bilingual Support:** Full English and Urdu conversation with bidirectional translation
- **Real-Time Avatar:** WebRTC-based streaming with ~100ms end-to-end latency
- **Neural Lip-Sync:** Wav2Lip / MuseTalk models for audio-driven face animation
- **Text-to-Speech:** Microsoft Edge TTS (fast, multi-language)

---

## 2. Architecture Overview

The system has three main components:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                │
│                   WebRTC Stream (Video + Audio)                     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LIVETALKING FRONTEND                             │
│              Flask + aiortc (WebRTC) + SocketIO                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐        │
│   │  Wav2Lip     │  │  MuseTalk    │  │  TTS (Edge)      │        │
│   │  lipreal.py  │  │  musereal.py │  │  ttsreal.py      │        │
│   └──────────────┘  └──────────────┘  └──────────────────┘        │
│                         Port: 8010                                   │
└───────────────────────┬─────────────────────────────────────────────┘
                        │ HTTP REST
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RAG BACKEND (FastAPI)                            │
│              Qdrant Vector DB + Google Gemini 2.5 Flash            │
│                                                                      │
│   Ingest Pipeline:  DOCX → Chunks → MiniLM Embeddings → Qdrant     │
│   Query Pipeline:   User Query → Embed → Retrieve → LLM Prompt    │
│                         Port: 8000                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Backend — RAG Chatbot Pipeline

### 3.1 Technology Stack
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | Latest | REST API server |
| LLM | Google Gemini 2.5 Flash | API | Response generation |
| Embeddings | HuggingFace MiniLM (all-MiniLM-L6-v2) | Local | Text embedding (384-dim) |
| Vector DB | Qdrant | 1.x | Semantic document retrieval |
| Translation | Gemini LLM (same key) | API | Urdu ↔ English |
| Document Parsing | python-docx | Local | DOCX file reading |

### 3.2 Data Flow (Query)

1. **User Query** → `/chat` endpoint (`main.py`)
2. **Language Detection** → `translation_service.py` detects if Urdu
3. **Embedding** → MiniLM embeds query into 384-dim vector
4. **Retrieval** → Qdrant similarity search (cosine distance) over `policy_docs` collection
5. **Context Assembly** → Top-K chunks combined into context prompt
6. **LLM Generation** → Gemini 2.5 Flash with system prompt + context + query
7. **Translation** (if needed) → Response translated back to Urdu
8. **Chunking** → Response split into sentences for TTS streaming

### 3.3 Document Ingestion (`ingest.py`)

- **Source:** Two DOCX policy documents (Study Visa, NIRA internal policy)
- **Section-aware chunking:** Documents split by headings (H1, H2) first, then into 512-char overlapping chunks
- **Embedding:** Each chunk → 384-dim vector via HuggingFace MiniLM
- **Storage:** Qdrant `policy_docs` collection, 1536-dim vector space (was previously configured for larger embeddings, currently using 384)

### 3.4 Translation Service (`translation_service.py`)

- Uses **Gemini 2.5 Flash** with specialized prompts for Urdu translation
- Handles **feminine forms** for avatar persona ("Sara")
- Translation is optional (controlled by `ENABLE_TRANSLATION` env var)
- Can be bypassed by setting `CHAT_LANGUAGE=ur` and sending Urdu directly to Gemini

### 3.5 Key Configuration (`main.py`, `.env`)

```
GOOGLE_API_KEY=<user-provided>
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=policy_docs
ENABLE_TRANSLATION=true
DEFAULT_LANGUAGE=en
CHAT_LANGUAGE=ur
```

### 3.6 Performance Optimizations

- **Retry logic:** 180-second timeout for Gemini API calls (handles rate limiting)
- **Exponential backoff:** Up to 5 retries with jitter
- **Streaming TTS chunks:** LLM response split into sentences to start TTS immediately
- **GPU memory management:** Models loaded once, shared across sessions

---

## 4. Frontend — LiveTalking Avatar System

### 4.1 Technology Stack
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Server | Flask (async) | HTTP + WebRTC signaling |
| WebRTC | aiortc | Real-time audio/video streaming |
| Audio TTS | Microsoft Edge TTS | Text-to-speech |
| Audio ASR | Whisper (tiny) | Audio feature extraction for lip-sync |
| Video | OpenCV | Frame processing and compositing |

### 4.2 Avatar Models

The system supports multiple lip-sync backends. We evaluated several before settling on **MuseTalk**:

#### **Wav2Lip** (Original, Currently Used)
- **Architecture:** CNN encoder-decoder with audio mel-spectrogram conditioning
- **Input:** Face crop (256×256) + audio mel-batch (80×16)
- **Output:** Lip-synced face crop
- **Paste-back:** Hard pixel copy onto original frame using bounding box
- **VRAM:** ~2-3 GB
- **Speed:** 15-25 FPS on RTX 2060 (6GB)
- **Quality Issues:**
  - Only generates mouth region → visible edge seams
  - No head movement or expression control
  - Bounding box wobble causes flickering
  - Face crop too large (44% of frame) → artifacts magnified

#### **MuseTalk V1.5** (In Progress — Target Solution)
- **Architecture:** Diffusion-based UNet with VAE encoder/decoder
- **Input:** Face crop + Whisper audio features (384-dim)
- **Output:** Full face region with natural blending (not just lips)
- **Blending:** Gaussian-feathered mask from face parsing (BiSeNet)
- **VRAM:** ~3-4 GB (fp16)
- **Speed:** 10-20 FPS
- **Advantages over Wav2Lip:**
  - Generates **entire face** (not just mouth) → no edge seams
  - **Built-in face mask blending** → smooth transitions
  - Better lip shape accuracy via diffusion refinement
  - Supports V1.5 enhanced jaw-line blending

#### **Other Models Evaluated**

| Model | Real-time? | VRAM | Why Not Used |
|-------|-----------|------|-------------|
| **SadTalker** | No (1-2 FPS) | 6-8 GB | Offline-only, needs full audio clip first |
| **Hallo2** | No (0.1 FPS) | 8-12 GB | Diffusion-based, 10-30s per clip |
| **LivePortrait** | Borderline | 6-10 GB | Best quality but needs 8GB+ GPU |
| **MuseTalk V1** | Yes | 3-4 GB | Replaced by V1.5 with better jaw blending |

### 4.3 Why We're Switching to MuseTalk

The current Wav2Lip avatar (`wav2lip256_businesswoman`) has three root quality issues:

1. **Face crop too large:** 256×314 pixels (44% of frame) vs. ideal 19%. Wav2Lip outputs 256×256 and gets stretched/distorted.
2. **Bounding box wobble:** Face bbox shifts 44px horizontally and 72px vertically across frames, causing edge flickering.
3. **Hard-cut paste-back:** No feathered edge blending (`combine_frame[y1:y2, x1:x2] = res_frame`).

**MuseTalk fixes all three:**
- Generates the full face region, not just lips
- Uses face parsing masks with Gaussian blur for seamless blending
- Face region is defined by segmentation, not a hard bbox

### 4.4 Avatar Data Structure

Both Wav2Lip and MuseTalk avatars are pre-processed from source videos:

```
data/avatars/<avatar_id>/
├── full_imgs/        # Original frames (e.g., 576×768)
├── face_imgs/        # Face crops (Wav2Lip only, 256×256)
├── mask/             # Blending masks (MuseTalk only)
├── coords.pkl        # Face bounding boxes per frame
├── mask_coords.pkl   # Mask crop boxes (MuseTalk only)
├── latents.pt        # VAE-encoded face latents (MuseTalk only)
└── avator_info.json  # Metadata
```

### 4.5 Frame Processing Pipeline

**Wav2Lip (`lipreal.py`):**
1. Audio → mel-spectrogram → model input
2. Face tensor (6-channel: RGB+mask, 256×256) → model
3. Model outputs RGB lip-synced face
4. `paste_back_frame()` resizes face and copies to original bbox

**MuseTalk (`musereal.py`):**
1. Audio → Whisper → 384-dim audio features
2. VAE latent (8-channel: masked+ref, 32×32) + audio → UNet diffusion
3. UNet predicts new latent
4. VAE decoder → RGB face image (256×256)
5. `get_image_blending()` uses pre-computed mask to feather face into original frame

### 4.6 Idle Behavior Optimization

We modified `basereal.py` to use a **static idle frame** (`frame_list_cycle[0]`) instead of cycling through all frames when not speaking. This prevents:
- Unnatural head bobbing when the avatar is "listening"
- Green screen artifact cycling
- Frame-to-frame jitter accumulation

### 4.7 Head Movement Analysis

| Avatar | Face Size | X Movement | Y Movement | Status |
|--------|-----------|------------|------------|--------|
| `wav2lip256_avatar1` (Chinese lady) | 109×160 px | 6 px | 4 px | Reference (good) |
| `wav2lip256_businesswoman` | 256×314 px | 44 px | 72 px | **Problematic** |

The businesswoman video source has too much head movement. Our fix plan:
1. Regenerate with **tight face crop** (matching reference proportions)
2. **Lock bounding box** to median position across all frames
3. Add **feathered edge blending** (for Wav2Lip as fallback)
4. Switch to **MuseTalk** for full-face generation

---

## 5. Models Downloaded and Used

### 5.1 Runtime Models

| Model | Size | Location | Purpose |
|-------|------|----------|---------|
| `wav2lip.pth` | 205 MB | `models/wav2lip.pth` | Wav2Lip lip-sync inference |
| `musetalkV15/unet.pth` | 3.2 GB | `models/musetalkV15/` | MuseTalk UNet diffusion |
| `musetalkV15/musetalk.json` | <1 KB | `models/musetalkV15/` | UNet architecture config |
| `sd-vae/` | 319 MB | `models/sd-vae/` | Stable Diffusion VAE encoder/decoder |
| `whisper/` | 144 MB | `models/whisper/` | Whisper tiny audio feature extractor |

### 5.2 Avatar Generation Models

| Model | Size | Location | Purpose |
|-------|------|----------|---------|
| `dw-ll_ucoco_384.pth` | 388 MB | `models/dwpose/` | DWPose body/face landmark detection |
| `resnet18-5c106cde.pth` | 45 MB | `models/face-parse-bisent/` | Face parsing backbone |
| `79999_iter.pth` | 51 MB | `models/face-parse-bisent/` | BiSeNet face segmentation |

**Note:** DWPose and face parsing are only needed for **avatar generation**, not runtime inference.

### 5.3 Model Download Sources

| Model | Source |
|-------|--------|
| MuseTalk V1.5 | `huggingface.co/TMElyralab/MuseTalk` |
| SD-VAE-FT-MSE | `huggingface.co/stabilityai/sd-vae-ft-mse` |
| Whisper Tiny | `huggingface.co/openai/whisper-tiny` |
| DWPose | `huggingface.co/yzd-v/DWPose` |
| Face Parse BiSeNet | GitHub `zllrunning/face-parsing.PyTorch` |

---

## 6. What We Changed and Why

### 6.1 Filesystem Reorganization

**What:** Moved files into proper directories:
- `docs/` — All markdown documentation
- `documents/` — Source DOCX files
- `scripts/` — Shell scripts (docker-start.sh, start_project.sh)
- `tests/` — Test scripts
- `_archive/` — Unused/legacy files (preserved, not deleted)

**Why:** The project root had 20+ files. This made navigation difficult and risked accidental modification of critical files. Organization follows standard Python project structure.

### 6.2 Ingest Path Fix (`ingest.py`)

**What:** Updated `DOC_PATHS` to point to `documents/` subdirectory.

**Why:** After moving DOCX files to `documents/`, the ingestion script would fail with `FileNotFoundError`, preventing Qdrant collection creation.

### 6.3 Static Idle Frame (`basereal.py`)

**What:** Changed idle frame from `self.frame_list_cycle[idx]` to `self.frame_list_cycle[0]`.

**Why:** Cycling through frames when not speaking caused the avatar to bob its head unnaturally. A static neutral frame (looking at camera) is more natural for a "listening" state.

### 6.4 Batch Size Reduction (`app.py`)

**What:** Forced `batch_size=2` for Wav2Lip warmup and inference.

**Why:** The original `batch_size=8` caused CUDA Out-of-Memory on 6GB GPUs. Batch size 2 is the maximum that fits while maintaining real-time performance.

### 6.5 Timeout Extension (`llm.py`)

**What:** Increased Gemini API timeout from 90s to 180s.

**Why:** Observed 80+ second response times from Gemini during rate limiting. The default 60-90s timeout was causing frequent connection errors.

### 6.6 Unicode Console Fix

**What:** Added `PYTHONIOENCODING="utf-8"` environment variable.

**Why:** Windows console uses `cp1252` encoding. Urdu characters in logs caused `UnicodeEncodeError` and crashed the logger.

---

## 7. How the RAG System Works (Detailed)

### 7.1 Document Ingestion

```python
# ingest.py
DOC_PATHS = [
    "documents/Updated Study Visa Team Document .docx",
    "documents/NIRA Updated Document .docx",
]
```

1. **Read DOCX** using `python-docx` — extracts paragraphs and headings
2. **Section Detection** — splits document by heading levels (H1, H2, H3)
3. **Chunking** — each section split into overlapping 512-character chunks with 64-char overlap
4. **Embedding** — `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")` → 384-dim vectors
5. **Storage** — Qdrant vector database with cosine distance metric
6. **Collection** — `policy_docs` collection (dimension 1536, configured for flexibility)

### 7.2 Query Processing

```python
# main.py /chat endpoint
async def chat(query: ChatRequest):
    # 1. Detect language
    if is_urdu(query.message):
        translated = await translate_urdu_to_english(query.message)
    
    # 2. Embed query
    query_embedding = embedder.embed_query(query.message)
    
    # 3. Retrieve from Qdrant
    results = qdrant.search(
        collection_name="policy_docs",
        query_vector=query_embedding,
        limit=5,
        score_threshold=0.6
    )
    
    # 4. Build prompt
    context = "\n\n".join([r.payload["text"] for r in results])
    prompt = f"""You are NIRA's AI assistant. Answer based ONLY on the context below.
    
Context:
{context}

Question: {query.message}
Answer:"""
    
    # 5. Generate with Gemini
    response = await gemini.generate(prompt, timeout=180)
    
    # 6. Translate back if needed
    if query.language == "ur":
        response = await translate_english_to_urdu(response)
    
    return {"answer": response, "sources": results}
```

### 7.3 System Prompt Design

The Gemini system prompt enforces:
- **Persona:** Professional NIRA representative named "Sara"
- **Constraint:** Answer ONLY from provided document context
- **Tone:** Helpful, concise, policy-accurate
- **Fallback:** "I don't have information about that" if no relevant context

---

## 8. Avatar Video Pipeline (Detailed)

### 8.1 WebRTC Streaming

```
Browser ←──WebRTC──→ LiveTalking Flask Server
    │                        │
    │ Video Track            │ Avatar Video (25 FPS)
    │ Audio Track            │ TTS Audio (16kHz)
    │                        │
    │  ←── SDP Offer ──      │
    │  ── SDP Answer ──→    │
```

- **Protocol:** WebRTC (peer-to-peer, low latency)
- **Video:** 25 FPS, BGR format, 576×768 resolution
- **Audio:** 16 kHz, 16-bit PCM, 20ms chunks
- **Transport:** aiortc (Python WebRTC library)

### 8.2 Text-to-Speech Pipeline

1. LLM response received from backend
2. Text split into sentences (better TTS quality than long paragraphs)
3. Each sentence sent to Edge TTS
4. Edge TTS streams MP3 → decoded to PCM
5. Audio resampled to 16 kHz
6. Chunks split into 20ms frames (480 samples at 16kHz)
7. Each chunk tagged with audio type:
   - `type=0`: Real audio data
   - `type=2`: Silence padding

### 8.3 Audio Feature Extraction

**Wav2Lip:**
- Audio chunks → STFT → mel-spectrogram (80 mel bins, 16 time frames)
- Mel batch: `(batch_size, 80, 16)`

**MuseTalk:**
- Audio chunks → Whisper encoder → 384-dim feature vectors
- Whisper features per frame: `(50, 384)` per audio segment

### 8.4 Lip-Sync Inference

**Wav2Lip Inference Loop (`lipreal.py`):**
```python
while running:
    mel_batch = audio_feat_queue.get()  # (2, 80, 16)
    face_batch = face_tensor_stack[indices]  # (2, 6, 256, 256)
    
    with torch.no_grad():
        pred = model(mel_batch, face_batch)  # (2, 3, 256, 256)
    
    # Paste back onto original frame
    combine_frame = frame_list[idx].copy()
    combine_frame[y1:y2, x1:x2] = resized_pred_face
```

**MuseTalk Inference Loop (`musereal.py`):**
```python
while running:
    whisper_features = audio_feat_queue.get()  # (2, 50, 384)
    latent_batch = input_latent_list_cycle[indices]  # (2, 8, 32, 32)
    
    # Positional encoding on audio
    audio_encoded = pe(whisper_features)
    
    # UNet diffusion
    with torch.no_grad():
        pred_latents = unet(latent_batch, timesteps, audio_encoded)
    
    # VAE decode to face image
    pred_face = vae.decode_latents(pred_latents)  # (2, 256, 256, 3)
    
    # Blend with pre-computed mask
    combine_frame = get_image_blending(
        original_frame, pred_face, face_box, mask, crop_box
    )
```

---

## 9. Current Issues and Status

### 9.1 Active Issues

| Issue | Severity | Status | Root Cause |
|-------|----------|--------|------------|
| Uncanny avatar video | High | In Progress | Wav2Lip face crop too large + bbox wobble |
| Edge seam on face | Medium | In Progress | Hard-cut paste-back in Wav2Lip |
| Head movement during speech | Medium | In Progress | Source video has too much movement |
| No head movement (idle) | Low | Fixed | Static frame 0 used for idle state |
| Unicode logging errors | Low | Fixed | Windows console cp1252 vs UTF-8 |
| CUDA OOM during warmup | Low | Fixed | Batch size reduced to 2 |
| Qdrant collection missing | Low | Fixed | Ingest paths updated |
| Disk space full | Medium | Fixed | HF cache cleared (3.7 GB freed) |

### 9.2 In-Progress Work: MuseTalk Migration

**Completed:**
- All MuseTalk models downloaded (unet, VAE, Whisper, DWPose, face parsing)
- `diffusers` and `face_alignment` dependencies installed
- Custom `generate_musetalk_avatar.py` script written (avoids mmpose dependency hell)

**Pending:**
- Fix torch.compile/Triton error on Windows (set `TORCH_DYNAMO_DISABLE=1`)
- Run avatar generation for `musetalk_businesswoman`
- Test MuseTalk inference pipeline
- Update `app.py` to use MuseTalk instead of Wav2Lip
- Verify VRAM usage under 6GB during inference

### 9.3 VRAM Budget (6 GB GPU)

| Component | VRAM (fp16) |
|-----------|-------------|
| MuseTalk UNet | ~1.6 GB |
| SD-VAE | ~160 MB |
| Whisper Tiny | ~150 MB |
| VAE decode buffer | ~200 MB |
| PyTorch overhead | ~500 MB |
| **Total** | **~2.6 GB** |
| **Headroom** | **~3.4 GB** |

MuseTalk will run comfortably on 6GB with batch_size=2.

---

## 10. Future Roadmap

### 10.1 Short Term (Next 2-4 Weeks)

1. **Complete MuseTalk Integration**
   - Fix avatar generation script (Triton issue)
   - Generate `musetalk_businesswoman` avatar
   - Test real-time inference performance
   - Update frontend to use MuseTalk model

2. **Avatar Quality Improvements**
   - Source a better video: neutral expression, front-facing, minimal movement
   - Test with close-up portrait (head + shoulders only)
   - Adjust `bbox_shift` parameter for optimal face crop

3. **Edge Blending Enhancement**
   - Even with MuseTalk, verify mask feathering quality
   - Tune `upper_boundary_ratio` and Gaussian blur kernel size
   - Test `jaw` vs `neck` vs `raw` parsing modes

### 10.2 Medium Term (1-3 Months)

1. **GPU Upgrade Path**
   - MuseTalk quality ceiling on 6GB is "acceptable"
   - For photorealistic quality, upgrade to 12GB GPU (RTX 3060 12GB / RTX 4070)
   - Then evaluate LivePortrait (state-of-the-art, ~8-10 GB)

2. **Additional Avatars**
   - Generate multiple avatar personas (male, different ethnicities)
   - Avatar selection UI in frontend
   - Per-avatar voice configuration (different Edge TTS voices)

3. **RAG Enhancements**
   - Support PDF and web page ingestion
   - Automatic document update pipeline
   - Better chunking strategy (semantic chunking with sentence transformers)
   - Hybrid search: vector + keyword (BM25)

### 10.3 Long Term (3-6 Months)

1. **Full Multimodal Support**
   - Vision: User uploads images/documents for avatar to discuss
   - Speech-to-text: Allow voice input (not just text)
   - Real-time language switching mid-conversation

2. **Production Deployment**
   - Cloud GPU instance (Vast.ai, RunPod, or AWS g4dn)
   - Docker Compose production setup with HTTPS
   - Load balancing for concurrent users
   - Monitoring and analytics dashboard

3. **Advanced Avatar Features**
   - Emotion-aware responses (sentiment detection → avatar expression)
   - Eye contact tracking (gaze direction adjustment)
   - Gesture generation (hand movements from speech patterns)
   - Background replacement ( greenscreen → virtual office )

---

## 11. Technical Decisions Log

| Decision | Date | Rationale |
|----------|------|-----------|
| FastAPI over Flask for backend | Early 2024 | Async native, automatic OpenAPI docs, better for high concurrency |
| Qdrant over Pinecone/Weaviate | Early 2024 | Open source, self-hosted, no API costs, good Python client |
| MiniLM embeddings | Early 2024 | Fast inference (CPU-friendly), 384-dim is sufficient for policy docs, small model |
| Gemini 2.5 Flash over GPT-4 | Mid 2024 | Better Urdu support, lower cost, faster inference, free tier available |
| Edge TTS over Coqui/Piper | Mid 2024 | No model download, instant startup, natural-sounding, supports Urdu |
| Wav2Lip initially | Mid 2024 | Fastest to set up, lowest VRAM, proven real-time capability |
| MuseTalk migration | June 2026 | Wav2Lip quality ceiling reached; MuseTalk is the best real-time alternative before LivePortrait |
| Windows development environment | Ongoing | User hardware constraint; deployment will be Linux Docker |

---

## 12. File Reference

### Backend Files
| File | Purpose | Key Content |
|------|---------|-------------|
| `main.py` | FastAPI entry point | `/chat` endpoint, Qdrant init, Gemini config |
| `ingest.py` | Document ingestion | DOCX → chunks → embeddings → Qdrant |
| `translation_service.py` | Urdu ↔ English | Gemini-based translation with gender-aware prompts |
| `requirements.txt` | Python dependencies | fastapi, uvicorn, langchain, qdrant-client, etc. |
| `.env.example` | Environment template | GOOGLE_API_KEY, QDRANT_URL, etc. |

### Frontend (LiveTalking) Files
| File | Purpose | Key Content |
|------|---------|-------------|
| `LiveTalking/app.py` | Flask server | WebRTC signaling, model/avatar loading, `/offer`, `/human` |
| `LiveTalking/lipreal.py` | Wav2Lip inference | `inference()`, `paste_back_frame()`, face tensor pre-loading |
| `LiveTalking/musereal.py` | MuseTalk inference | `inference()`, `get_image_blending()`, UNet/VAE setup |
| `LiveTalking/basereal.py` | Base avatar class | TTS integration, audio queue, `process_frames()`, idle/speaking states |
| `LiveTalking/llm.py` | Backend bridge | Sends queries to `/chat`, chunks responses for TTS |
| `LiveTalking/ttsreal.py` | Text-to-speech | EdgeTTS streaming, audio resampling, 20ms chunking |
| `LiveTalking/lipasr.py` | Audio features | Mel-spectrogram extraction for Wav2Lip |
| `LiveTalking/museasr.py` | Audio features | Whisper feature extraction for MuseTalk |
| `LiveTalking/webrtc.py` | Media streaming | `PlayerStreamTrack` for WebRTC audio/video tracks |
| `LiveTalking/web/webrtcapi.html` | Frontend UI | WebRTC client, chat interface, avatar video display |
| `LiveTalking/web/client.js` | WebRTC logic | SDP negotiation, connection state, auto-reconnect |
| `LiveTalking/generate_musetalk_avatar.py` | Avatar generator | Simplified MuseTalk avatar generation (no mmpose) |

### Configuration Files
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Qdrant + Backend + LiveTalking services |
| `Dockerfile` | Backend container build |
| `.gitignore` | Excludes models, .env, __pycache__ |

---

## 13. How to Run (Manual Commands)

### Prerequisites
- Python 3.11+
- CUDA 11.8+ capable GPU (6GB+ VRAM)
- Docker Desktop (for Qdrant)

### Step 1: Qdrant Vector DB
```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:latest
```

### Step 2: RAG Backend
```bash
cd c:\Users\ASUS-PC\Downloads\Tester
.\.venv\Scripts\activate
$env:PYTHONIOENCODING="utf-8"
python ingest.py  # Populate Qdrant (run once)
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: LiveTalking Frontend
```bash
cd c:\Users\ASUS-PC\Downloads\Tester\LiveTalking
.\livetalking_env\Scripts\activate
$env:PYTHONIOENCODING="utf-8"
$env:TORCH_DYNAMO_DISABLE = "1"
python app.py
```

### Step 4: Access
- Chatbot API: http://localhost:8000/docs
- Avatar UI: http://localhost:8010/webrtcapi.html

---

## 14. Known Limitations

1. **GPU VRAM:** 6GB limits model choice. LivePortrait and Hallo2 are out of reach.
2. **Windows Development:** Some packages (mmpose, mmcv) don't install cleanly on Windows. Deployment will use Linux Docker.
3. **Single User:** Current WebRTC setup supports one concurrent user per LiveTalking instance.
4. **Avatar Source Quality:** The current businesswoman video is not ideal (too much movement, green screen bleed). A better source video would dramatically improve output.
5. **TTS Latency:** Edge TTS requires internet connection; offline TTS (Piper, Coqui) would be more robust.
6. **Document Format:** Currently only DOCX. PDF and web pages require additional parsers.

---

*Document written by AI coding assistant based on full codebase analysis.*
*For questions or updates, refer to the GitHub repository or ask the assistant.*
