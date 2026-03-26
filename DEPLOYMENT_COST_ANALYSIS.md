# Deployment Cost Analysis: RAG & Avatar-Based System

**Subject:** Deployment Cost Analysis — NIRA Digital Avatar System
**Date:** March 2026

---

Hi [Manager's Name],

I have completed a cost analysis for deploying our RAG-powered digital avatar system. The system consists of three services: a **FastAPI RAG backend** (with Qdrant vector database and Google Gemini), a **LiveTalking avatar engine** (wav2lip lip-sync + Edge TTS + WebRTC streaming), and the **Qdrant vector database**. To optimize costs, I've evaluated a hybrid approach using a dedicated server for the backend logic and a GPU cloud instance for real-time avatar inference.

Below is the breakdown based on current market rates as of March 2026.

---

## 1. Core Logic & Database (Hetzner Dedicated Server)

The RAG backend handles document retrieval (Qdrant vector search with HuggingFace embeddings), answer generation (Google Gemini 2.5 Flash), and serves the `/chat` API that LiveTalking calls.

| Spec | Detail |
|------|--------|
| **Model** | Intel Core i7-6700 |
| **RAM** | 64 GB |
| **Storage** | 2 x 512 GB SSD |
| **Cost** | €35.70/month (~$38.50/month) |

**What runs here:**
- FastAPI RAG backend (port 8000)
- Qdrant vector database (port 6333)
- HuggingFace embedding model (sentence-transformers/all-MiniLM-L6-v2)
- Document ingestion pipeline (python-docx based)

64 GB RAM is more than sufficient — Qdrant with our current document set uses under 1 GB, and the embedding model uses ~500 MB. This server can handle hundreds of registered clients' vector collections simultaneously.

---

## 2. AI Inference & Avatar Rendering (VectorLay GPU)

The LiveTalking avatar engine requires a dedicated GPU for real-time wav2lip neural network inference (lip-sync) and WebRTC video streaming. This is the performance bottleneck — without a CUDA GPU, the system cannot achieve smooth frame rates.

| Spec | Detail |
|------|--------|
| **GPU** | NVIDIA RTX 4090 (24 GB VRAM) |
| **Provider** | VectorLay |
| **Hourly Rate** | $0.49/hr |
| **Monthly Cost** | $352.80 (720 hrs/month, 24/7) |
| **Annual Cost** | $4,234 |

**What runs here:**
- LiveTalking avatar engine (port 8010) — wav2lip model, WebRTC signaling, Edge TTS
- Real-time lip-sync inference at 80–120 FPS
- Supports 3–5 concurrent avatar sessions on a single RTX 4090

**Provider comparison (RTX 4090, 24/7):**

| Provider | Hourly Rate | Monthly Cost | vs VectorLay |
|----------|------------|-------------|--------------|
| **VectorLay** | $0.49/hr | **$352.80** | — |
| RunPod | $0.74/hr | $532.80 | +51% |
| Vast.ai | ~$0.55/hr | ~$396.00 | +12% |
| AWS (g5.xlarge, A10G) | $1.21/hr | $871.20 | +147% |
| GCP (g2-standard-8, L4) | $0.90/hr | $648.00 | +84% |

---

## 3. Total Estimated Monthly Cost

| Component | Provider | Monthly Cost (USD) |
|-----------|----------|-------------------|
| Backend + Vector DB + Embeddings | Hetzner | ~$38.50 |
| GPU Inference + Avatar Rendering | VectorLay | $352.80 |
| Google Gemini API (LLM) | Google | ~$5–15 (usage-based) |
| Edge TTS | Microsoft | Free |
| Domain + SSL | Cloudflare | ~$15 |
| **Total** | | **~$411–421/mo** |

**Note:** Google Gemini 2.5 Flash is usage-based (~$0.15 per 1M input tokens). At moderate usage (1,000 queries/day), this costs roughly $5–15/month. Edge TTS is free.

---

## 4. Capacity at This Price Point

| Metric | Capacity |
|--------|----------|
| Registered clients (own documents + collection) | Unlimited |
| Concurrent live avatar sessions | 3–5 simultaneous |
| Expected FPS per session | 80–120 |
| Practical client capacity (avg usage patterns) | 30–50 clients |

Most clients won't use the avatar simultaneously. With typical usage patterns (a few minutes per visitor, spread across business hours), this setup comfortably serves 30–50 registered clients.

---

## 5. Recommendation

I recommend proceeding with **VectorLay** for GPU needs — it offers a **34% saving** over RunPod and is **60% cheaper** than AWS. For the backend, the **Hetzner auction server** provides the RAM and CPU needed to keep vector search latency low and serve the RAG pipeline.

Total deployment cost is approximately **$411/month** for a system that can serve 30–50 clients with their own isolated knowledge bases and a live-talking avatar.

**Next steps:**
1. Provision the Hetzner server and install Qdrant + RAG backend
2. Provision the VectorLay RTX 4090 instance and deploy LiveTalking
3. Set up SSL and domain routing between the two servers
4. Deploy a Coturn TURN server (~$15–20/mo extra if needed for WebRTC NAT traversal)

Please let me know if you'd like to proceed or if you need any further details.

Best regards,
[Your Name]
