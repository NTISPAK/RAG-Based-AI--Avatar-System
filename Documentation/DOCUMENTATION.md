# NTIS Policy RAG Chatbot - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Setup Instructions](#setup-instructions)
6. [Component Details](#component-details)
7. [API Documentation](#api-documentation)
8. [Configuration](#configuration)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

**NTIS Policy RAG Chatbot** is a Retrieval-Augmented Generation (RAG) system that answers questions about NTIS company policies using:
- **Vector Database**: Qdrant for semantic search
- **Embeddings**: HuggingFace sentence-transformers
- **LLM**: Google Gemini 2.5 Flash
- **Backend**: FastAPI
- **Frontend**: Modern HTML/CSS/JavaScript

### Key Features
- ✅ Semantic search over policy documents
- ✅ Context-aware responses using RAG
- ✅ Professional chat interface
- ✅ No authentication required (simple version)
- ✅ Real-time streaming responses
- ✅ Mobile responsive design

---

## Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│       FastAPI Backend               │
│  ┌──────────────────────────────┐   │
│  │  1. Receive Query            │   │
│  └──────────┬───────────────────┘   │
│             │                       │
│             ▼                       │
│  ┌──────────────────────────────┐   │
│  │  2. Generate Embeddings      │   │
│  │     (HuggingFace)            │   │
│  └──────────┬───────────────────┘   │
│             │                       │
│             ▼                       │
│  ┌──────────────────────────────┐   │
│  │  3. Vector Search (Qdrant)   │   │
│  │     Retrieve top-k chunks    │   │
│  └──────────┬───────────────────┘   │
│             │                       │
│             ▼                       │
│  ┌──────────────────────────────┐   │
│  │  4. Build Prompt with        │   │
│  │     Retrieved Context        │   │
│  └──────────┬───────────────────┘   │
│             │                       │
│             ▼                       │
│  ┌──────────────────────────────┐   │
│  │  5. LLM Generation           │   │
│  │     (Gemini 2.5 Flash)       │   │
│  └──────────┬───────────────────┘   │
│             │                       │
└─────────────┼───────────────────────┘
              │
              ▼
     ┌────────────────┐
     │   Response     │
     └────────────────┘
```

---

## Technology Stack

### Backend
- **FastAPI** (0.115.0) - Web framework
- **Uvicorn** (0.30.0) - ASGI server
- **LangChain** (0.3.7+) - RAG orchestration
- **Qdrant Client** (1.12.0+) - Vector database
- **Google Gemini** - LLM API

### Embeddings & NLP
- **sentence-transformers** (3.3.0+) - Text embeddings
- **HuggingFace** - Model hosting
- **Model**: `all-MiniLM-L6-v2` (384 dimensions)

### Frontend
- **HTML5** - Structure
- **CSS3** - Styling with CSS variables
- **Vanilla JavaScript** - Interactivity
- **Inter Font** - Typography

### Data Processing
- **PyPDF** (5.1.0+) - PDF parsing
- **RecursiveCharacterTextSplitter** - Text chunking

---

## Project Structure

```
/Users/naumanrashid/Desktop/Tester/
│
├── main.py                          # FastAPI application
├── ingest.py                        # PDF ingestion script
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables
│
├── templates/
│   └── index.html                   # Chat UI
│
├── static/
│   └── style.css                    # Styles
│
├── Accounts, Invoicing & Refund Policy.pdf  # Source document
│
└── DOCUMENTATION.md                 # This file
```

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Qdrant running locally or remotely
- Google Gemini API key

### Step 1: Clone/Download Project
```bash
cd /Users/naumanrashid/Desktop/Tester
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create `.env` file:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=policy_docs
```

### Step 5: Start Qdrant
**Option A: Docker**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

**Option B: Local Installation**
Follow [Qdrant docs](https://qdrant.tech/documentation/quick-start/)

### Step 6: Ingest PDF Documents
```bash
python ingest.py
```

**Expected Output:**
```
==================================================
NTIS Policy Document Ingestion
==================================================

[1/5] Loading PDF: /path/to/pdf
      Loaded 6 pages

[2/5] Splitting into chunks...
      Created 9 chunks

[3/5] Loading embeddings model...
      Model loaded: all-MiniLM-L6-v2

[4/5] Connecting to Qdrant...
      Created collection: policy_docs

[5/5] Storing vectors in Qdrant...
      Stored 9 vectors

SUCCESS! Document ingestion complete.
```

### Step 7: Run the Application
```bash
uvicorn main:app --reload --port 8080
```

### Step 8: Access the UI
Open browser: `http://localhost:8080`

---

## Component Details

### 1. `main.py` - FastAPI Backend

#### Initialization Flow
```python
1. Load environment variables (.env)
2. Initialize HuggingFace embeddings model
3. Connect to Qdrant vector database
4. Create vector store with embeddings
5. Initialize Gemini LLM
6. Build RetrievalQA chain
7. Start FastAPI server
```

#### Key Components

**Embeddings Model**
```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)
```
- **Model**: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Device**: CPU (change to 'cuda' for GPU)
- **Normalization**: Enabled for cosine similarity

**Vector Store**
```python
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)
```

**Retriever**
```python
retriever = vector_store.as_retriever(search_kwargs={"k": 4})
```
- Retrieves top 4 most relevant chunks

**LLM Configuration**
```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.5,
    google_api_key=GOOGLE_API_KEY,
)
```
- **Model**: gemini-2.5-flash
- **Temperature**: 0.5 (balanced creativity/accuracy)
- **API**: Google AI Studio

**System Prompt**
```python
SYSTEM_PROMPT = """You are the NTIS Policy Assistant...

STRICT RULES:
1. Use ONLY the retrieved context
2. NEVER hallucinate
3. If no answer, say "I do not have that information"
4. Be concise and professional

CONTEXT: {context}
QUESTION: {question}
"""
```

#### API Endpoints

**GET /**
- Returns chat UI (index.html)

**POST /chat**
- Input: `{"message": "user question"}`
- Output: `{"response": "assistant answer"}`
- Process:
  1. Receive user message
  2. Invoke QA chain
  3. Return LLM response

**GET /health**
- Returns: `{"status": "ok", "service": "NTIS Policy Assistant"}`

---

### 2. `ingest.py` - Document Ingestion

#### Process Flow
```
1. Load PDF → 2. Split Text → 3. Generate Embeddings → 4. Store in Qdrant
```

#### Configuration
```python
PDF_PATH = "Accounts, Invoicing & Refund Policy.pdf"
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "policy_docs"
```

#### Text Splitting Strategy
```python
RecursiveCharacterTextSplitter(
    chunk_size=800,        # Characters per chunk
    chunk_overlap=150,     # Overlap for context continuity
    separators=["\n\n", "\n", ". ", " ", ""]
)
```

**Why these settings?**
- **800 chars**: Balances context vs. precision
- **150 overlap**: Prevents losing context at boundaries
- **Separators**: Splits at natural boundaries (paragraphs, sentences)

#### Qdrant Collection Setup
```python
VectorParams(
    size=384,              # Match embedding dimensions
    distance=Distance.COSINE  # Similarity metric
)
```

---

### 3. Frontend (`templates/index.html` + `static/style.css`)

#### UI Components

**Sidebar**
- Logo and branding
- Quick action buttons
- Status indicator
- Collapsible on mobile

**Chat Area**
- Welcome screen with suggestion chips
- Message bubbles (user/assistant)
- Typing indicator
- Auto-scroll

**Input Area**
- Auto-resizing textarea
- Send button (disabled when empty)
- Keyboard shortcuts (Enter to send)

#### JavaScript Functions

**`sendMessage()`**
```javascript
async function sendMessage() {
    // 1. Get user input
    // 2. Display user message
    // 3. Show typing indicator
    // 4. POST to /chat endpoint
    // 5. Display assistant response
    // 6. Hide typing indicator
}
```

**`askQuestion(question)`**
- Pre-fills input with suggested question
- Automatically sends message

**`clearChat()`**
- Resets chat to welcome screen

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_API_KEY` | Gemini API key | - | ✅ Yes |
| `QDRANT_URL` | Qdrant endpoint | `http://localhost:6333` | ✅ Yes |
| `COLLECTION_NAME` | Vector collection | `policy_docs` | ✅ Yes |

### Customization Options

#### Change LLM Model
```python
# In main.py
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",  # More powerful
    temperature=0.3,          # More deterministic
)
```

#### Adjust Retrieval Count
```python
# In main.py
retriever = vector_store.as_retriever(
    search_kwargs={"k": 6}  # Retrieve 6 chunks instead of 4
)
```

#### Change Embedding Model
```python
# In main.py and ingest.py
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",  # Better quality
    # Note: Update vector size in Qdrant to 768
)
```

#### Modify Chunking Strategy
```python
# In ingest.py
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Larger chunks
    chunk_overlap=200,    # More overlap
)
```

---

## Deployment

### Production Checklist

1. **Environment Variables**
   - Use secrets manager (AWS Secrets, Azure Key Vault)
   - Never commit `.env` to Git

2. **Qdrant**
   - Use managed Qdrant Cloud
   - Or self-host with persistent storage

3. **FastAPI**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
   ```

4. **Reverse Proxy**
   - Use Nginx or Caddy
   - Enable HTTPS with Let's Encrypt

5. **Docker Deployment**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
   ```

6. **Monitoring**
   - Add logging (Python `logging` module)
   - Track API usage and costs
   - Monitor Qdrant performance

---

## Troubleshooting

### Common Issues

#### 1. Qdrant Connection Error
```
Error: Could not connect to Qdrant at http://localhost:6333
```
**Solution:**
- Ensure Qdrant is running: `docker ps` or check service
- Verify `QDRANT_URL` in `.env`

#### 2. Gemini API Quota Exceeded
```
Error: 429 RESOURCE_EXHAUSTED
```
**Solution:**
- Wait for quota reset (daily limit)
- Upgrade to paid tier
- Use different API key

#### 3. Empty Responses
```
Response: "I do not have that information in the policy document."
```
**Solution:**
- Check if PDF was ingested: `python ingest.py`
- Verify Qdrant has vectors
- Increase retrieval count (`k`)

#### 4. Slow Response Times
**Solution:**
- Use GPU for embeddings: `model_kwargs={'device': 'cuda'}`
- Reduce chunk count in retrieval
- Cache embeddings
- Use faster LLM model

#### 5. Module Import Errors
```
ModuleNotFoundError: No module named 'langchain'
```
**Solution:**
```bash
pip install -r requirements.txt --upgrade
```

---

## Recreating from Scratch

### Minimal Steps

1. **Create Project Directory**
   ```bash
   mkdir ntis-chatbot && cd ntis-chatbot
   ```

2. **Create `requirements.txt`**
   ```
   fastapi==0.115.0
   uvicorn==0.30.0
   python-dotenv==1.0.0
   langchain>=0.3.7
   langchain-google-genai>=2.0.4
   langchain-community>=0.3.5
   langchain-qdrant>=0.2.0
   langchain-huggingface>=1.0.0
   langchain-text-splitters>=1.0.0
   langchain-classic>=0.1.0
   qdrant-client>=1.12.0
   sentence-transformers>=3.3.0
   pypdf>=5.1.0
   jinja2>=3.1.4
   ```

3. **Create `.env`**
   ```env
   GOOGLE_API_KEY=your_key
   QDRANT_URL=http://localhost:6333
   COLLECTION_NAME=policy_docs
   ```

4. **Create `main.py`** (copy from this project)

5. **Create `ingest.py`** (copy from this project)

6. **Create `templates/index.html`** (copy from this project)

7. **Create `static/style.css`** (copy from this project)

8. **Add PDF Document**
   - Place policy PDF in root directory

9. **Install & Run**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python ingest.py
   uvicorn main:app --reload --port 8080
   ```

---

## Advanced Features (Future Enhancements)

### 1. Add User Authentication
- Firebase Auth
- JWT tokens
- User-specific chat history

### 2. Multi-Document Support
- Ingest multiple PDFs
- Document metadata filtering
- Source attribution in responses

### 3. Conversation Memory
- Store chat history in database
- Context-aware follow-up questions
- Session management

### 4. Analytics Dashboard
- Query analytics
- User engagement metrics
- Popular questions

### 5. Advanced RAG Techniques
- Hybrid search (vector + keyword)
- Re-ranking retrieved chunks
- Query expansion
- Multi-query retrieval

---

## License & Credits

**Project**: NTIS Policy RAG Chatbot  
**Version**: 1.0.0  
**Created**: 2026  
**Technologies**: LangChain, Qdrant, FastAPI, Google Gemini

---

## Support

For issues or questions:
1. Check this documentation
2. Review error logs
3. Verify configuration
4. Test with simple queries first

**End of Documentation**
