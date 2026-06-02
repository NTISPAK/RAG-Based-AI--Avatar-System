# NIRA AI Avatar System — Code Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Directory Structure](#3-directory-structure)
4. [Service Startup & Ports](#4-service-startup--ports)
5. [Backend (RAG + Gemini)](#5-backend-rag--gemini)
6. [LiveTalking (Avatar Engine)](#6-livetalking-avatar-engine)
7. [Data Flow: User Query → Avatar Speech](#7-data-flow-user-query--avatar-speech)
8. [File-by-File Reference](#8-file-by-file-reference)
9. [Configuration & Environment Variables](#9-configuration--environment-variables)
10. [Docker Deployment](#10-docker-deployment)

---

## 1. Project Overview

This project is a **RAG-based AI Avatar Receptionist** for Nauman International Recruitment Agency (NIRA). It combines:

- A **FastAPI backend** that retrieves policy documents from a Qdrant vector database and generates answers using Google Gemini.
- A **LiveTalking frontend** that renders a real-time lip-synced avatar via WebRTC, powered by the Wav2Lip deep learning model.
- **Bilingual support** for English and Urdu (both script and Romanized).

The avatar persona is **Sara**, a friendly female AI receptionist. When a user types or speaks a question, the system retrieves relevant policy context, generates a natural-language answer, converts it to speech via Edge TTS, and renders lip-synced video of the avatar in real time.

---

## 2. Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        User's Browser                              │
│  webrtcapi.html  +  client.js                                      │
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐                    │
│  │ Chat Input  │→ │ /human   │  │ WebRTC A/V │← video + audio     │
│  │ (text/mic)  │  │ (POST)   │  │ streams    │                    │
│  └─────────────┘  └────┬─────┘  └─────▲──────┘                    │
└─────────────────────────┼──────────────┼───────────────────────────┘
                          │              │
              ┌───────────▼──────────────┼───────────────────┐
              │     LiveTalking Server (port 8010)           │
              │                                              │
              │  app.py ──→ llm.py ──→ HTTP POST /chat ──┐  │
              │                                           │  │
              │  ┌──────────┐   ┌──────────┐   ┌───────┐ │  │
              │  │ EdgeTTS  │→  │ LipASR   │→  │Wav2Lip│ │  │
              │  │(ttsreal) │   │(lipasr)  │   │(infer)│ │  │
              │  └────┬─────┘   └────┬─────┘   └───┬───┘ │  │
              │       │              │             │      │  │
              │       └──── audio ───┴── mel ──────┘      │  │
              │                                           │  │
              │  basereal.py: process_frames → WebRTC out │  │
              └───────────────────────────────┬───────────┘  │
                                              │              │
              ┌───────────────────────────────▼──────────┐   │
              │     RAG Backend (port 8000)              │   │
              │                                          │   │
              │  main.py                                 │   │
              │  ┌──────────┐  ┌────────┐  ┌──────────┐ │   │
              │  │ Qdrant   │→ │ Gemini │→ │ Response │─┘   │
              │  │ Retriever│  │ LLM    │  │ (JSON)   │     │
              │  └──────────┘  └────────┘  └──────────┘     │
              └──────────────────────────────────────────────┘
                        │
              ┌─────────▼──────────┐
              │  Qdrant (port 6333)│
              │  Vector Database   │
              │  (Docker container)│
              └────────────────────┘
```

---

## 3. Directory Structure

```
Tester/                              ← Project root
├── main.py                          ← FastAPI backend (RAG + Gemini)
├── ingest.py                        ← Document ingestion script (DOCX → Qdrant)
├── translation_service.py           ← Urdu ↔ English translation via Gemini
├── requirements.txt                 ← Python dependencies for backend
├── .env                             ← Environment variables (API keys, URLs)
├── .env.example                     ← Template for .env
├── Dockerfile                       ← Docker image for backend
├── docker-compose.yml               ← Full stack Docker orchestration
│
├── Updated Study Visa Team Document .docx   ← Source policy document #1
├── NIRA Updated Document .docx              ← Source policy document #2
│
├── LiveTalking/                     ← Avatar engine (lip-sync + WebRTC)
│   ├── app.py                       ← Main server: WebRTC signaling + HTTP endpoints
│   ├── llm.py                       ← Bridge: calls RAG backend /chat API
│   ├── lipreal.py                   ← Wav2Lip model loading, inference, avatar loading
│   ├── basereal.py                  ← Base class: frame processing, audio/video output
│   ├── baseasr.py                   ← Base ASR: audio frame queue management
│   ├── lipasr.py                    ← Lip ASR: mel-spectrogram extraction from audio
│   ├── ttsreal.py                   ← TTS engines (Edge TTS, Fish TTS, Azure, etc.)
│   ├── webrtc.py                    ← WebRTC media track implementation
│   ├── logger.py                    ← Logging configuration
│   │
│   ├── models/
│   │   └── wav2lip.pth              ← Pre-trained Wav2Lip model weights
│   │
│   ├── wav2lip/                     ← Wav2Lip neural network definition
│   │   ├── models/
│   │   │   ├── wav2lip_v2.py        ← Model architecture (encoder-decoder)
│   │   │   └── conv.py              ← Convolution building blocks
│   │   └── audio.py                 ← Mel-spectrogram computation
│   │
│   ├── data/avatars/
│   │   └── wav2lip256_businesswoman/  ← Active avatar data
│   │       ├── full_imgs/           ← 550 full-body frames (576×768 PNG)
│   │       ├── face_imgs/           ← 550 cropped face frames (256×256 PNG)
│   │       └── coords.pkl           ← Bounding box coords for face paste-back
│   │
│   └── web/                         ← Frontend static files
│       ├── webrtcapi.html           ← Main UI page (chat + avatar video)
│       ├── client.js                ← WebRTC negotiation logic
│       └── ...                      ← Other HTML pages
│
└── .venv/                           ← Backend Python virtual environment
```

---

## 4. Service Startup & Ports

| Service        | Port   | How to Start                                                                                                    |
|----------------|--------|-----------------------------------------------------------------------------------------------------------------|
| **Qdrant**     | 6333   | `docker start qdrant`                                                                                           |
| **Backend**    | 8000   | `python -m uvicorn main:app --host 0.0.0.0 --port 8000` (from `Tester/`, using `.venv`)                        |
| **LiveTalking**| 8010   | `python app.py --model wav2lip --avatar_id wav2lip256_businesswoman --batch_size 2 --transport webrtc --listenport 8010 --tts edgetts --REF_FILE "ur-PK-UzmaNeural"` (from `LiveTalking/`, using `livetalking_env`) |

**Startup order:** Qdrant → Backend → LiveTalking

**Access the UI:** `http://localhost:8010/webrtcapi.html`

---

## 5. Backend (RAG + Gemini)

### 5.1 `main.py` — FastAPI Server

This is the core backend. It initializes all components at import time and exposes HTTP endpoints.

**Initialization sequence (lines 78–125):**

1. **Embeddings model** — Loads `sentence-transformers/all-MiniLM-L6-v2` on CPU. Produces 384-dimensional vectors.
2. **Qdrant client** — Connects to Qdrant at `http://localhost:6333`, collection `policy_docs`.
3. **Vector store** — Wraps Qdrant with LangChain's `QdrantVectorStore` for similarity search.
4. **Retriever** — Returns top-4 most relevant document chunks per query (`k=4`).
5. **Gemini LLM** — Initializes `gemini-2.5-flash` with `temperature=0.7`.
6. **Prompt templates** — Two templates: English (`SYSTEM_PROMPT`) and Urdu (`URDU_SYSTEM_PROMPT`). Both instruct Sara to answer in 3-5 spoken sentences using only the provided context.
7. **Translation service** — Optional `TranslationService` using Gemini for Urdu ↔ English.

**Endpoints:**

| Endpoint       | Method | Purpose                                                |
|----------------|--------|--------------------------------------------------------|
| `/chat`        | POST   | Main endpoint. Receives `{message, language}`, runs RAG pipeline, returns `{response, language, processing_time}`. |
| `/health`      | GET    | Health check with translation metrics.                 |
| `/languages`   | GET    | Returns supported languages.                           |
| `/translate`   | POST   | Direct translation endpoint for testing.               |

**`/chat` flow (lines 181–219):**

1. Receives `ChatRequest` with `message` and `language` (default: `en`).
2. If `language == "ur"`: Uses Urdu prompt template (Gemini writes directly in Urdu script). This is a 1-API-call approach to conserve free-tier quota.
3. If `language == "en"`: Uses English prompt template.
4. Calls `run_rag_pipeline()` which:
   - Retrieves top-4 document chunks from Qdrant via similarity search.
   - Formats them into the prompt template with the user's question.
   - Invokes Gemini with retry logic for rate limiting (`_invoke_with_retry`).
5. Returns the generated answer as JSON.

**Rate limit handling (`_invoke_with_retry`, lines 150–163):**
- Catches `RESOURCE_EXHAUSTED`, `429`, `503` errors.
- Parses retry delay from the error message.
- Retries up to 3 times with exponential backoff (capped at 15s).

### 5.2 `ingest.py` — Document Ingestion

Run once to populate Qdrant with policy documents. **Not a server — a one-shot script.**

**Steps (lines 119–184):**

1. **Load DOCX files** — Reads `Updated Study Visa Team Document .docx` and `NIRA Updated Document .docx` using `python-docx`. Splits each file into sections at heading boundaries. Each section becomes a LangChain `Document` with metadata `{source, heading}`.
2. **Chunk documents** — Splits sections into ~800-character chunks with 150-char overlap using a recursive splitter (`_recursive_split`). Tries `\n\n`, then `\n`, then `. `, then space, then hard char split.
3. **Load embeddings** — Same `all-MiniLM-L6-v2` model as the backend.
4. **Flush Qdrant** — Deletes all existing collections and creates a fresh `policy_docs` collection with 384-dim cosine similarity vectors.
5. **Store vectors** — Embeds all chunks and stores them in Qdrant via `QdrantVectorStore.from_documents()`.
6. **Verify** — Prints the total point count.

**Run:** `python ingest.py` (from `Tester/`, using `.venv`)

### 5.3 `translation_service.py` — Urdu ↔ English Translation

Provides the `TranslationService` class used optionally by the backend.

- **`translate_urdu_to_english()`** — Prompts Gemini to translate Urdu text to English.
- **`translate_english_to_urdu()`** — Prompts Gemini to translate English to Urdu with feminine forms (Sara is female).
- **`detect_language()`** — Simple heuristic: counts Unicode characters in the Urdu range (`U+0600`–`U+06FF`). If >30% of alphabetic chars are Urdu, classifies as `ur`.
- **Retry logic** — Same rate-limit handling as the main backend.
- **Metrics** — Tracks translation count and total time.

> **Note:** In the current 1-call approach, translation is NOT used during normal `/chat` flow. Gemini handles Romanized Urdu input directly and outputs Urdu script. This saves API calls on the free tier.

---

## 6. LiveTalking (Avatar Engine)

### 6.1 `app.py` — Main Server & WebRTC Signaling

The entry point for the LiveTalking service. Parses CLI arguments, loads the model and avatar, and starts an aiohttp web server.

**Startup (lines 323–446):**

1. Parses arguments: `--model`, `--avatar_id`, `--batch_size`, `--tts`, `--REF_FILE`, `--transport`, `--listenport`.
2. Loads the Wav2Lip model from `./models/wav2lip.pth` (`load_model`).
3. Loads avatar data: 550 full images, 550 face crops, coordinates, pre-computed face tensors (`load_avatar`).
4. Runs model warmup (single forward pass to allocate GPU memory).
5. Starts aiohttp server on port 8010, serving static files from `web/`.

**HTTP Endpoints:**

| Endpoint          | Purpose                                                         |
|-------------------|-----------------------------------------------------------------|
| `POST /offer`     | WebRTC SDP offer/answer handshake. Creates a new session.       |
| `POST /human`     | Receives user message. `type=chat` triggers RAG pipeline via `llm.py`. `type=echo` directly speaks the text. |
| `POST /humanaudio`| Accepts uploaded audio file and feeds it to the avatar.         |
| `POST /interrupt_talk` | Flushes the TTS queue to stop current speech.             |
| `POST /set_audiotype`  | Switches to custom audio/video playback.                   |
| `POST /record`    | Starts/stops session recording.                                 |
| `POST /is_speaking` | Returns whether the avatar is currently speaking.             |
| `GET /` (static)  | Serves `web/` directory (HTML, JS, CSS).                        |

**Session management:**
- Each WebRTC connection gets a random 6-digit `sessionid`.
- A `LipReal` instance is created per session and stored in `nerfreals[sessionid]`.
- On connection close, the session is cleaned up.

### 6.2 `llm.py` — RAG Backend Bridge

Called by `app.py` when `type == 'chat'`. Runs in a thread pool executor (non-blocking).

**`llm_response(message, nerfreal)` (lines 14–94):**

1. POSTs `{message, language}` to `http://127.0.0.1:8000/chat` (the backend).
2. Language is set via `CHAT_LANGUAGE` env var (default: `en`, set to `ur` for Urdu).
3. Timeout: 180 seconds (Gemini free tier can take 80+ seconds due to rate limiting).
4. On success: splits the answer at sentence boundaries (`.!?۔`), merges short sentences into ~200-char chunks for better TTS prosody.
5. Sends each chunk to `nerfreal.put_msg_txt()` which queues it for TTS.
6. On failure: sends an error message in the appropriate language.

### 6.3 `lipreal.py` — Wav2Lip Model & Avatar

**Top-level functions:**

- **`load_model(path)`** — Loads `wav2lip.pth` checkpoint, strips `module.` prefixes, moves to GPU/CPU.
- **`load_avatar(avatar_id)`** — Loads avatar data from `data/avatars/{avatar_id}/`:
  - `full_imgs/` → 550 full-body PNG frames (576×768) stored as numpy arrays.
  - `face_imgs/` → 550 face-cropped PNG frames (256×256).
  - `coords.pkl` → List of `[y1, y2, x1, x2]` bounding boxes mapping face crops back onto full frames.
  - Pre-computes face tensors: for each face, creates a masked version (bottom half zeroed) concatenated with the original (6 channels), normalized to [0,1], stacked as a GPU tensor.
- **`warm_up(batch_size, model, modelres)`** — Single forward pass with dummy data to pre-allocate GPU memory.
- **`inference()` thread** — The main GPU inference loop:
  1. Pulls mel-spectrogram batches from `audio_feat_queue`.
  2. Pulls corresponding audio frames from `audio_out_queue`.
  3. If all-silence: passes `None` as the result frame (idle).
  4. If speaking: gathers `batch_size` pre-computed face tensors, runs Wav2Lip forward pass, outputs predicted lip-synced face frames.
  5. Pushes `(res_frame, frame_index, audio_frames)` to `res_frame_queue`.

**`LipReal` class (lines 178–256):**

Inherits from `BaseReal`. Per-session avatar instance.

- **`__init__`** — Stores model, avatar data, creates `LipASR` for audio processing, sets up queues.
- **`paste_back_frame(pred_frame, idx)`** — Takes a 256×256 predicted face, resizes it to match the bounding box, and pastes it onto the corresponding full frame.
- **`render(quit_event, ...)`** — Main render loop. Starts 3 threads:
  1. **TTS thread** — Processes text queue → Edge TTS → audio chunks.
  2. **Inference thread** — Mel spectrograms → Wav2Lip → predicted faces.
  3. **Frame processing thread** — Combines results → WebRTC output.
  4. **Main loop** — Calls `asr.run_step()` continuously to feed audio into the pipeline.

### 6.4 `basereal.py` — Base Class for All Avatar Models

**Key responsibilities:**

- **TTS initialization** — Creates the appropriate TTS engine (EdgeTTS, etc.) based on `--tts` flag.
- **`put_msg_txt(msg)`** — Queues text for TTS synthesis.
- **`put_audio_frame(chunk)`** — Feeds raw audio PCM into the ASR pipeline.
- **`mirror_index(size, index)`** — Ping-pong index for natural looping: 0,1,2,...,N-1,N-2,...,1,0,1,...
- **`process_frames()` thread (lines 300–402)** — The video output loop:
  - Pulls `(res_frame, idx, audio_frames)` from `res_frame_queue`.
  - **If silence (idle):** Uses frame 0 (static neutral face looking at camera). No cycling animation.
  - **If speaking:** Calls `paste_back_frame()` to composite the lip-synced face onto the full body frame.
  - Converts the frame to a `VideoFrame` and pushes it onto the WebRTC video track queue.
  - Converts audio frames to `AudioFrame` (16-bit PCM, 16kHz mono) and pushes onto the WebRTC audio track queue.

### 6.5 `baseasr.py` — Audio Frame Queue

**`BaseASR` class:**

- Manages the audio input queue at 16kHz, 20ms chunks (320 samples/chunk).
- **`get_audio_frame()`** — Returns the next audio chunk:
  - If audio is queued: returns real audio with `type=0` (speaking).
  - If queue is empty: returns silence (zeros) with `type=1`.
- **`output_queue`** — Multiprocessing queue that passes audio frames to the inference thread.
- **`feat_queue`** — Multiprocessing queue that passes mel-spectrogram batches to the inference thread.

### 6.6 `lipasr.py` — Mel-Spectrogram Extraction

**`LipASR` class (extends `BaseASR`):**

**`run_step()`** — Called continuously by the main render loop:

1. Pulls `batch_size * 2` audio frames from the queue (each 20ms).
2. Passes each frame through to `output_queue` (for audio playback).
3. Concatenates frames into a continuous audio buffer.
4. Computes mel-spectrogram using `wav2lip.audio.melspectrogram()`.
5. Applies a sliding window to extract 16-frame mel chunks (matching Wav2Lip's expected input).
6. Pushes the mel chunk batch to `feat_queue` for GPU inference.
7. Trims old frames to save memory (keeps only the stride overlap).

### 6.7 `ttsreal.py` — Text-to-Speech

**`BaseTTS` class:**
- Manages a message queue (`msgqueue`).
- Runs a TTS processing thread that pulls messages and calls `txt_to_audio()`.
- Supports `PAUSE` state to interrupt current speech.

**`EdgeTTS` class (lines 94–157):**
- Uses Microsoft Edge TTS (free, no API key needed).
- Voice ID set by `--REF_FILE` (e.g., `ur-PK-UzmaNeural` for Urdu female voice).
- Streams audio chunks from Edge TTS, writes to a BytesIO buffer.
- Reads the buffer as a soundfile, resamples from 24kHz to 16kHz.
- Splits into 20ms chunks and feeds them to `parent.put_audio_frame()`.
- Tags the first chunk with `{status: 'start'}` and the last with `{status: 'end'}`.

### 6.8 `webrtc.py` — WebRTC Media Tracks

**`PlayerStreamTrack` class:**
- Extends `aiortc.MediaStreamTrack`.
- Async queue-based: frames are pushed by the avatar engine, pulled by WebRTC.
- Handles timestamp generation for both audio (16kHz) and video (25fps/40ms per frame).
- Auto-paces video output to maintain consistent frame rate.

**`HumanPlayer` class:**
- Creates one audio and one video `PlayerStreamTrack`.
- Starts a worker thread that calls `nerfreal.render()` — this is what kicks off the entire avatar pipeline.

### 6.9 Frontend: `web/webrtcapi.html` + `web/client.js`

**`client.js`** — WebRTC connection management:
- `start()` — Creates `RTCPeerConnection`, calls `/offer` to exchange SDP, receives audio/video tracks, displays in `<video>` and `<audio>` elements.
- `stop()` — Closes the peer connection.
- Auto-reconnect on connection failure (1.5s delay).
- Sets `jitterBufferTarget = 0` for minimum latency.

**`webrtcapi.html`** — Full chat UI:
- Dark-themed responsive design.
- Text input with send button.
- Microphone button (Web Speech API for speech-to-text, English).
- On submit: POSTs `{text, type:'chat', interrupt:true, sessionid}` to `/human`.
- Shows "Thinking..." while waiting, "Avatar is responding..." when accepted.
- Status indicator (green dot = connected).

---

## 7. Data Flow: User Query → Avatar Speech

```
1. User types "What services do you offer?" in webrtcapi.html
                    │
2. Frontend POSTs to /human {text, type:'chat', sessionid}
                    │
3. app.py calls llm_response() in a thread pool
                    │
4. llm.py POSTs to http://127.0.0.1:8000/chat {message, language:'ur'}
                    │
5. main.py retrieves top-4 document chunks from Qdrant
                    │
6. main.py formats prompt + context, sends to Gemini 2.5 Flash
                    │
7. Gemini returns answer (e.g., 3-5 sentences in Urdu script)
                    │
8. llm.py splits answer into sentence chunks
                    │
9. Each chunk → nerfreal.put_msg_txt(chunk)
                    │
10. BaseTTS.msgqueue receives the text
                    │
11. EdgeTTS converts text → audio stream (24kHz)
                    │
12. Audio resampled to 16kHz, split into 20ms PCM chunks
                    │
13. Chunks fed to BaseASR.queue via put_audio_frame()
                    │
14. LipASR.run_step() extracts mel-spectrograms from audio
                    │
15. Mel batches pushed to feat_queue
                    │
16. inference() thread: Wav2Lip model generates lip-synced face frames
                    │
17. res_frame_queue receives (predicted_face, frame_index, audio)
                    │
18. process_frames() pastes predicted face onto full body frame
                    │
19. VideoFrame + AudioFrame pushed to WebRTC track queues
                    │
20. Browser receives and plays synchronized audio + video
```

---

## 8. File-by-File Reference

### Root Directory (`Tester/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI server. RAG pipeline: Qdrant retrieval → Gemini generation. Endpoints: `/chat`, `/health`, `/languages`, `/translate`. |
| `ingest.py` | One-shot script. Reads DOCX files, chunks them, embeds with MiniLM-L6-v2, stores in Qdrant. Run once to populate the database. |
| `translation_service.py` | `TranslationService` class. Bidirectional Urdu ↔ English translation using Gemini. Includes language detection heuristic. |
| `requirements.txt` | Backend Python dependencies: FastAPI, uvicorn, langchain, qdrant-client, sentence-transformers, python-docx. |
| `.env` | Runtime secrets: `GOOGLE_API_KEY`, `QDRANT_URL`, `COLLECTION_NAME`, translation settings. |
| `.env.example` | Template showing all available environment variables. |
| `Dockerfile` | Docker image for the backend. Python 3.11-slim, installs deps, runs uvicorn. |
| `docker-compose.yml` | Orchestrates Qdrant (6333), backend (8000), LiveTalking (8010) as Docker services. |
| `Updated Study Visa Team Document .docx` | Source policy document about study visas. |
| `NIRA Updated Document .docx` | Source policy document about NIRA services. |

### LiveTalking Directory

| File | Purpose |
|------|---------|
| `app.py` | Main server. CLI argument parsing, model/avatar loading, WebRTC signaling (`/offer`), chat routing (`/human`), aiohttp web server on port 8010. |
| `llm.py` | Bridge to RAG backend. Calls `POST /chat` on port 8000, splits response into TTS-friendly chunks, feeds to avatar via `put_msg_txt()`. |
| `lipreal.py` | Wav2Lip integration. `load_model()`, `load_avatar()`, `warm_up()`, `inference()` thread (GPU), `LipReal` class with `render()` and `paste_back_frame()`. |
| `basereal.py` | Base class for all avatar models. TTS init, audio/video frame processing, WebRTC output loop, recording support, idle frame logic. |
| `baseasr.py` | Audio queue management. 16kHz/20ms chunking, silence generation when idle, multiprocessing queues for mel features and audio output. |
| `lipasr.py` | Mel-spectrogram extraction. Sliding window over audio frames, computes mel via `wav2lip.audio`, pushes batches to inference thread. |
| `ttsreal.py` | TTS engines. `EdgeTTS` (primary): Microsoft Edge TTS, streams audio, resamples 24→16kHz, splits into 20ms chunks. Also supports Fish, XTTS, CosyVoice, Azure, etc. |
| `webrtc.py` | WebRTC tracks. `PlayerStreamTrack` (async queue-based media track), `HumanPlayer` (creates audio+video tracks, starts render thread). |
| `logger.py` | Centralized logging configuration. |
| `web/webrtcapi.html` | Main UI: chat input, mic button (Web Speech API), avatar video display, WebRTC connection management. |
| `web/client.js` | WebRTC negotiation: SDP offer/answer via `/offer`, track handling, auto-reconnect on failure. |
| `models/wav2lip.pth` | Pre-trained Wav2Lip model weights (encoder-decoder for lip sync). |
| `wav2lip/` | Wav2Lip neural network code: model architecture (`wav2lip_v2.py`), convolution blocks (`conv.py`), audio processing (`audio.py`). |
| `data/avatars/wav2lip256_businesswoman/` | Avatar data: 550 full-body frames, 550 face crops (256×256), bounding box coordinates. |

---

## 9. Configuration & Environment Variables

### `.env` (Backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | (required) | Google Gemini API key |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `COLLECTION_NAME` | `policy_docs` | Qdrant collection name |
| `ENABLE_TRANSLATION` | `true` | Enable translation service |
| `DEFAULT_LANGUAGE` | `en` | Default chat language |
| `SUPPORTED_LANGUAGES` | `en,ur` | Comma-separated language codes |

### LiveTalking CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--model` | `musetalk` | Model type: `wav2lip`, `musetalk`, `ultralight` |
| `--avatar_id` | `avator_1` | Avatar folder name in `data/avatars/` |
| `--batch_size` | `16` | Inference batch size. **Use 2 for 6GB GPU.** |
| `--tts` | `edgetts` | TTS engine: `edgetts`, `fishtts`, `azuretts`, etc. |
| `--REF_FILE` | `en-US-JennyNeural` | TTS voice ID. Use `ur-PK-UzmaNeural` for Urdu. |
| `--transport` | `rtcpush` | Transport: `webrtc`, `rtcpush`, `virtualcam` |
| `--listenport` | `8010` | HTTP server port |
| `--fps` | `50` | Audio FPS (must be 50 = 20ms frames) |
| `-l`, `-m`, `-r` | `10, 8, 10` | Sliding window left/middle/right stride |

### LiveTalking Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_BACKEND_URL` | `http://127.0.0.1:8000` | Backend API URL (used by `llm.py`) |
| `CHAT_LANGUAGE` | `en` | Language for RAG queries (`en` or `ur`) |

---

## 10. Docker Deployment

The `docker-compose.yml` defines three services:

1. **qdrant** — `qdrant/qdrant:latest` on ports 6333/6334 with persistent storage volume.
2. **rag-backend** — Built from `./Dockerfile`. Depends on qdrant health check. Port 8000.
3. **livetalking** — Built from `./LiveTalking/Dockerfile.new`. Depends on backend health check. Port 8010. Mounts `models/` and `data/` as volumes.

**Quick start:**
```bash
docker-compose up -d
```

**For GPU support:** Uncomment the `deploy.resources.reservations.devices` section in the `livetalking` service.

---

*Generated for the NIRA AI Avatar System. Last updated: May 2026.*
