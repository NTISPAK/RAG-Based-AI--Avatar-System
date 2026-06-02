# NIRA Digital Avatar — System Requirements & SaaS Guide

---

## 1. What the System Runs

| Service | Stack | Port |
|---------|-------|------|
| RAG Backend | FastAPI + Qdrant + Gemini + HuggingFace Embeddings | 8000 |
| LiveTalking | aiohttp + aiortc + wav2lip (PyTorch) + Edge TTS | 8010 |
| Qdrant | Vector database | 6333 |

Current config: wav2lip model, 450x450 resolution, Edge TTS (en-US-JennyNeural), Gemini 2.5 Flash, WebRTC transport.

---

## 2. Server Requirements

### For Smooth Performance (80–120 FPS)

You need an **NVIDIA GPU with CUDA**. Mac/CPU cannot do real-time lip-sync at acceptable frame rates.

| Component | Minimum (1 session, 80 FPS) | Recommended (3–5 sessions, 120 FPS) |
|-----------|----------------------------|--------------------------------------|
| GPU | RTX 3060 12GB | RTX 4090 24GB or A10G |
| CPU | 8-core (i7-12700) | 16-core (Ryzen 9 7950X) |
| RAM | 32 GB | 64 GB |
| Storage | 256 GB NVMe SSD | 512 GB NVMe SSD |
| Network | 100 Mbps symmetric | 1 Gbps symmetric |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CUDA | 11.8 or 12.x | 11.8 or 12.x |
| Python | 3.10 or 3.11 | 3.10 or 3.11 |

### Best Cloud Options

| Provider | Instance | GPU | Cost |
|----------|----------|-----|------|
| AWS | g5.xlarge | A10G 24GB | ~$1.00/hr |
| GCP | g2-standard-8 | L4 24GB | ~$0.90/hr |
| RunPod | RTX 4090 | 24GB | ~$0.40/hr |

AWS/GCP reserved instances save 40–60% for long-term use.

---

## 3. Selling as a Service

### What You Need to Add

1. **Multi-tenancy** — each client gets their own Qdrant collection, avatar, and system prompt
2. **API key auth** — clients authenticate via API key, backend routes to their data
3. **Embeddable widget** — a `<script>` tag clients paste on their website to show the avatar
4. **Admin dashboard** — clients upload documents, customize the persona, view usage
5. **Billing** — Stripe subscription with usage tracking (queries, talk minutes)
6. **TURN server** — Coturn (~$20/mo VPS) so WebRTC works behind firewalls (without it ~15% of users can't connect)
7. **SSL + domain** — required for WebRTC to work in browsers

### Suggested Pricing

| Tier | Price | What's Included |
|------|-------|-----------------|
| Starter | $49/mo | 1 avatar, 1 knowledge base, 60 min talk-time |
| Business | $199/mo | 3 avatars, 5 knowledge bases, 500 min talk-time |
| Enterprise | Custom | Dedicated GPU, white-label, SLA |

### Monthly Infrastructure Cost

| Scale | Infra Cost | Break-Even |
|-------|-----------|------------|
| 1–10 clients | ~$800/mo | 3–6 clients |
| 10–50 clients | ~$1,800/mo | ~12 clients |
| 50+ clients | ~$4,000/mo | ~20 clients |

---

## 4. Roadmap

**Phase 1 (MVP):** Migrate to GPU server, Dockerize, add SSL, deploy TURN server, basic multi-tenancy, embeddable widget.

**Phase 2 (Product):** Admin dashboard, Stripe billing, document upload pipeline, custom avatars per client.

**Phase 3 (Scale):** Kubernetes with GPU autoscaling, monitoring, load testing, public launch.

---

*NIRA Digital Avatar System — March 2026*
