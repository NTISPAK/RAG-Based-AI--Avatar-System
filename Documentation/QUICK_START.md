# NTIS Policy Chatbot - Quick Start Guide

## 🚀 5-Minute Setup

### 1. Prerequisites
```bash
# Install Python 3.11+
python3 --version

# Start Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant
```

### 2. Install
```bash
cd /Users/naumanrashid/Desktop/Tester
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure
Create `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=policy_docs
```

### 4. Ingest Data
```bash
python ingest.py
```

### 5. Run
```bash
uvicorn main:app --reload --port 8080
```

### 6. Open
http://localhost:8080

---

## 📁 File Structure

```
Tester/
├── main.py              # FastAPI app (backend)
├── ingest.py            # PDF ingestion
├── requirements.txt     # Dependencies
├── .env                 # Config (create this)
├── templates/
│   └── index.html       # Chat UI
├── static/
│   └── style.css        # Styles
└── Accounts, Invoicing & Refund Policy.pdf
```

---

## 🔧 Key Commands

### Run Server
```bash
uvicorn main:app --reload --port 8080
```

### Ingest New PDF
```bash
python ingest.py
```

### Check Qdrant
```bash
curl http://localhost:6333/collections/policy_docs
```

---

## 🎯 How It Works

```
User Query → Embeddings → Qdrant Search → LLM → Response
```

1. **User asks question** via chat UI
2. **Convert to vector** using HuggingFace embeddings
3. **Search Qdrant** for similar chunks (top 4)
4. **Send to Gemini** with context
5. **Return answer** to user

---

## ⚙️ Configuration

### Change LLM Temperature
```python
# main.py, line 98
temperature=0.5  # 0=deterministic, 1=creative
```

### Change Retrieval Count
```python
# main.py, line 92
search_kwargs={"k": 4}  # Number of chunks
```

### Change Chunk Size
```python
# ingest.py, line 38
chunk_size=800  # Characters per chunk
```

---

## 🐛 Troubleshooting

### Qdrant not running
```bash
docker ps  # Check if running
docker run -p 6333:6333 qdrant/qdrant
```

### API quota exceeded
- Wait 24 hours for reset
- Or get new API key from https://aistudio.google.com

### Empty responses
```bash
python ingest.py  # Re-ingest PDF
```

### Module errors
```bash
pip install -r requirements.txt --upgrade
```

---

## 📊 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI |
| Vector DB | Qdrant |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) |
| LLM | Google Gemini 2.5 Flash |
| Frontend | HTML/CSS/JS |

---

## 🔐 Environment Variables

| Variable | Example | Required |
|----------|---------|----------|
| `GOOGLE_API_KEY` | `AIzaSy...` | ✅ |
| `QDRANT_URL` | `http://localhost:6333` | ✅ |
| `COLLECTION_NAME` | `policy_docs` | ✅ |

---

## 📝 API Endpoints

### GET /
Returns chat UI

### POST /chat
```json
Request:  {"message": "What is the refund policy?"}
Response: {"response": "A refund is allowed if..."}
```

### GET /health
```json
{"status": "ok", "service": "NTIS Policy Assistant"}
```

---

## 🎨 UI Features

- ✅ Sidebar with quick actions
- ✅ Welcome screen with suggestions
- ✅ Message bubbles (user/assistant)
- ✅ Typing indicator
- ✅ Auto-scroll
- ✅ Mobile responsive
- ✅ Clear chat button

---

## 🚢 Production Deployment

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Build & Run
```bash
docker build -t ntis-chatbot .
docker run -p 8080:8080 --env-file .env ntis-chatbot
```

---

## 📚 Learn More

- Full documentation: `DOCUMENTATION.md`
- LangChain docs: https://python.langchain.com
- Qdrant docs: https://qdrant.tech
- Gemini API: https://ai.google.dev

---

**That's it! You're ready to go! 🎉**
