# NTIS Policy RAG with LiveTalking Digital Human

A Retrieval-Augmented Generation (RAG) system integrated with LiveTalking digital human frontend for answering NTIS policy questions with real-time lip-synced video responses.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

- ✅ **Real-time Digital Human** – LiveTalking with Wav2lip model for realistic lip-sync animation
- ✅ **WebRTC Video Streaming** – Low-latency video delivery to browser
- ✅ **Semantic RAG** – Qdrant + LangChain for policy document retrieval
- ✅ **Gemini LLM** – Google Gemini 2.5 Flash for answer generation
- ✅ **Anti-hallucination guardrails** – System prompt enforces "not in document" fallback

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker (for Qdrant)
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))
- LiveTalking models downloaded (wav2lip.pth, avatar files)

### Quick Start

See **[QUICKSTART.md](QUICKSTART.md)** for detailed setup instructions.

**Automated Start:**
```bash
./start_project.sh
```

**Manual Start:**

1. **Start Qdrant**
   ```bash
   docker run -p 6333:6333 qdrant/qdrant:latest
   ```

2. **Start RAG Backend** (Terminal 1)
   ```bash
   cd /Users/naumanrashid/Desktop/Tester
   source .venv/bin/activate
   python -m uvicorn main:app --reload
   ```

3. **Start LiveTalking Frontend** (Terminal 2)
   ```bash
   cd /Users/naumanrashid/Desktop/Tester/LiveTalking
   source livetalking_env/bin/activate
   python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
   ```

4. **Access the Application**
   - Simple UI: http://localhost:8010/webrtcapi.html
   - Dashboard: http://localhost:8010/dashboard.html

## 📁 Project Structure

```
Tester/
├── main.py                    # RAG Backend (FastAPI)
├── ingest.py                  # PDF ingestion script
├── requirements.txt           # Backend dependencies
├── .env                       # Environment variables
├── start_project.sh           # Automated startup script
├── LiveTalking/              # Frontend (Digital Human)
│   ├── app.py                # LiveTalking server
│   ├── llm.py                # Modified to call RAG backend
│   ├── web/                  # Frontend HTML files
│   ├── models/               # AI models (wav2lip.pth)
│   └── data/avatars/         # Avatar files
├── static/                    # Static files
├── templates/                 # HTML templates
├── data/                      # Policy documents
├── QUICKSTART.md             # Quick start guide
├── README_LIVETALKING.md     # LiveTalking integration docs
└── frontend_backup_*/        # Old frontend (backed up)
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI |
| **Vector Database** | Qdrant |
| **Embeddings** | HuggingFace (all-MiniLM-L6-v2) |
| **LLM** | Google Gemini 2.5 Flash |
| **Framework** | LangChain |
| **Frontend** | LiveTalking (WebRTC + Wav2lip) |
| **Digital Human** | Wav2lip lip-sync model |
| **Video Streaming** | WebRTC (aiortc) |

## 📖 How It Works

```
User Browser → LiveTalking (WebRTC) → RAG Backend → Qdrant + Gemini → Response → TTS + Lip-sync → Video Stream
```

1. **User types question** in LiveTalking web interface
2. **LiveTalking sends** question to RAG backend via HTTP
3. **RAG backend** converts query to vector embeddings
4. **Qdrant search** retrieves top 4 most similar document chunks
5. **Gemini LLM** generates answer from retrieved context
6. **LiveTalking** converts answer to speech and generates lip-sync video
7. **WebRTC streams** synchronized video to user's browser

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_API_KEY` | Gemini API key | - | ✅ Yes |
| `QDRANT_URL` | Qdrant endpoint | `http://localhost:6333` | ✅ Yes |
| `COLLECTION_NAME` | Vector collection name | `policy_docs` | ✅ Yes |

### Customization

**Change LLM model:**
```python
# In main.py, line 96
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",  # More powerful
    temperature=0.3,          # More deterministic
)
```

**Adjust retrieval count:**
```python
# In main.py, line 92
retriever = vector_store.as_retriever(
    search_kwargs={"k": 6}  # Retrieve 6 chunks instead of 4
)
```

**Modify chunking strategy:**
```python
# In ingest.py, line 37
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Larger chunks
    chunk_overlap=200,    # More overlap
)
```

## 📡 API Endpoints

### GET /
Returns the chat interface (HTML)

### POST /chat
Process user message and return AI response

**Request:**
```json
{
  "message": "What is the refund policy?"
}
```

**Response:**
```json
{
  "response": "A refund is allowed if..."
}
```

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "ok",
  "service": "NTIS Policy Assistant"
}
```

## 🐳 Docker Deployment

### Build Docker image
```bash
docker build -t ntis-chatbot .
```

### Run container
```bash
docker run -p 8080:8080 --env-file .env ntis-chatbot
```

### Docker Compose (with Qdrant)
```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
  
  chatbot:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    depends_on:
      - qdrant
```

## 🔒 Security Notes

- ✅ `.env` file is gitignored (never commit API keys)
- ✅ Use environment variables for all secrets
- ✅ API keys should be rotated regularly
- ✅ In production, use secrets manager (AWS Secrets, Azure Key Vault)

## 🐛 Troubleshooting

### Qdrant connection error
```bash
# Check if Qdrant is running
docker ps

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant
```

### API quota exceeded
- Wait for quota reset (daily limit)
- Get a new API key from [Google AI Studio](https://aistudio.google.com)

### Empty responses
```bash
# Re-ingest the PDF
python ingest.py
```

### Module import errors
```bash
# Upgrade dependencies
pip install -r requirements.txt --upgrade
```

## 📚 Documentation

- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
- **LiveTalking Integration**: See [README_LIVETALKING.md](README_LIVETALKING.md)
- **LiveTalking Setup**: See [LiveTalking/LIVETALKING_SETUP.md](LiveTalking/LIVETALKING_SETUP.md)
- **Mac M2 Notes**: See [LiveTalking/MAC_M2_SETUP.md](LiveTalking/MAC_M2_SETUP.md)
- **Model Downloads**: See [LiveTalking/DOWNLOAD_MODELS.md](LiveTalking/DOWNLOAD_MODELS.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [LangChain](https://python.langchain.com) - RAG framework
- [Qdrant](https://qdrant.tech) - Vector database
- [Google Gemini](https://ai.google.dev) - LLM API
- [FastAPI](https://fastapi.tiangolo.com) - Web framework
- [HuggingFace](https://huggingface.co) - Embeddings

## 📧 Support

For issues or questions:
1. Check the [documentation](DOCUMENTATION.md)
2. Review [troubleshooting guide](#-troubleshooting)
3. Open an issue on GitHub

---

**Made with ❤️ for NTIS**
