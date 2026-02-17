# NTIS Policy RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that answers questions about NTIS company policies using semantic search and AI.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Features

- ✅ **Semantic Search** - Vector-based document retrieval using Qdrant
- ✅ **AI-Powered Responses** - Google Gemini LLM for natural language answers
- ✅ **Professional UI** - Modern, responsive chat interface
- ✅ **No Authentication** - Simple, ready-to-use chatbot
- ✅ **Anti-Hallucination** - Strict fact-based responses only
- ✅ **Easy Deployment** - Docker-ready with minimal setup

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker (for Qdrant)
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Tester
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API key:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   QDRANT_URL=http://localhost:6333
   COLLECTION_NAME=policy_docs
   ```

5. **Start Qdrant vector database**
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

6. **Ingest your PDF documents**
   ```bash
   python ingest.py
   ```

7. **Run the application**
   ```bash
   uvicorn main:app --reload --port 8080
   ```

8. **Open in browser**
   ```
   http://localhost:8080
   ```

## 📁 Project Structure

```
Tester/
├── main.py                  # FastAPI backend
├── ingest.py                # PDF ingestion script
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── .gitignore              # Git ignore rules
├── templates/
│   └── index.html          # Chat UI
├── static/
│   └── style.css           # Styles
├── Accounts, Invoicing & Refund Policy.pdf  # Source document
├── DOCUMENTATION.md        # Full documentation
├── QUICK_START.md          # Quick reference
└── CODE_REFERENCE.md       # Code explanations
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI |
| **Vector Database** | Qdrant |
| **Embeddings** | HuggingFace (all-MiniLM-L6-v2) |
| **LLM** | Google Gemini 2.5 Flash |
| **Framework** | LangChain |
| **Frontend** | HTML/CSS/JavaScript |

## 📖 How It Works

```
User Query → Embeddings → Vector Search → LLM → Response
```

1. **User asks a question** via the chat interface
2. **Convert to vector** using HuggingFace embeddings (384 dimensions)
3. **Search Qdrant** for top 4 most similar document chunks
4. **Send to Gemini** with retrieved context
5. **Return answer** to user with strict fact-checking

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

- **Full Documentation**: See [DOCUMENTATION.md](DOCUMENTATION.md)
- **Quick Reference**: See [QUICK_START.md](QUICK_START.md)
- **Code Reference**: See [CODE_REFERENCE.md](CODE_REFERENCE.md)

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
