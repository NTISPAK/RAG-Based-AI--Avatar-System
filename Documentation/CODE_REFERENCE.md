# Code Reference Guide - NTIS Policy RAG Chatbot

## Complete Code Breakdown

This document provides line-by-line explanations of all code files.

---

## 1. `main.py` - FastAPI Backend (159 lines)

### Imports (Lines 1-17)
```python
import os                                    # Environment variables
from dotenv import load_dotenv               # Load .env file
from fastapi import FastAPI, Request         # Web framework
from fastapi.staticfiles import StaticFiles  # Serve CSS/JS
from fastapi.templating import Jinja2Templates  # HTML templates
from fastapi.responses import HTMLResponse   # HTML response type
from pydantic import BaseModel               # Request validation
from langchain_huggingface import HuggingFaceEmbeddings  # Text embeddings
from langchain_google_genai import ChatGoogleGenerativeAI  # Gemini LLM
from langchain_qdrant import QdrantVectorStore  # Qdrant integration
from langchain_classic.chains import RetrievalQA  # RAG chain
from langchain_core.prompts import PromptTemplate  # Prompt template
from qdrant_client import QdrantClient       # Qdrant client
```

### Configuration (Lines 19-26)
```python
load_dotenv()  # Load .env file into environment

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Gemini API key
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")  # Qdrant endpoint
COLLECTION_NAME = "policy_docs"  # Vector collection name
```

### System Prompt (Lines 28-65)
```python
SYSTEM_PROMPT = """You are the NTIS Policy Assistant...

STRICT RULES:
1. Use ONLY the retrieved context below to answer questions.
2. NEVER hallucinate or make up information.
3. If the answer is not in the context, respond exactly:
   "I do not have that information in the policy document."
4. Be concise and professional.

POLICY ENFORCEMENT:
- Refund is allowed ONLY if:
  * Service not started after payment
  * Company cancelled service
  * Duplicate payment made
  * Delivered work does not meet agreed scope AND issue cannot be resolved

- Refund is NOT allowed if:
  * Service fully completed and delivered
  * Customer caused delay or late information
  * Customer approved work then changed requirements
  * Service marked non-refundable

- Interpreter Payment: Processed within 21 working days from invoice approval date.

- Approval Hierarchy:
  * Accounts Officer → routine confirmations
  * Accounts Manager → partial refunds/adjustments
  * Senior Management/Director → full refunds or exceptional cases

CONTEXT:
{context}

QUESTION: {question}

ANSWER (based only on context above):"""
```

**Purpose**: 
- Defines LLM behavior
- Enforces strict fact-based responses
- Includes key policy rules for consistency
- Uses placeholders `{context}` and `{question}` for dynamic insertion

### Embeddings Initialization (Lines 72-78)
```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",  # Model ID
    model_kwargs={'device': 'cpu'},  # Use CPU (change to 'cuda' for GPU)
    encode_kwargs={'normalize_embeddings': True}  # L2 normalization
)
```

**Model Details**:
- **Name**: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Speed**: Fast (suitable for CPU)
- **Quality**: Good for general semantic search
- **Normalization**: Enables cosine similarity

### Qdrant Connection (Lines 80-89)
```python
qdrant_client = QdrantClient(url=QDRANT_URL)  # Connect to Qdrant

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,  # "policy_docs"
    embedding=embeddings,  # Embedding function
)
```

**Purpose**:
- Establishes connection to Qdrant vector database
- Creates vector store wrapper for LangChain
- Links embeddings to vector operations

### Retriever Setup (Lines 91-92)
```python
retriever = vector_store.as_retriever(search_kwargs={"k": 4})
```

**Parameters**:
- `k=4`: Retrieve top 4 most similar chunks
- Uses cosine similarity (configured in Qdrant)
- Returns documents sorted by relevance score

### LLM Initialization (Lines 94-100)
```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # Fast, cost-effective model
    temperature=0.5,  # Balanced creativity (0=deterministic, 1=creative)
    google_api_key=GOOGLE_API_KEY,  # API authentication
)
```

**Model Choice**:
- **gemini-2.5-flash**: Fast responses, good quality
- **Alternatives**: gemini-1.5-pro (more powerful but slower)
- **Temperature**: 0.5 balances accuracy and natural language

### Prompt Template (Lines 102-106)
```python
prompt_template = PromptTemplate(
    template=SYSTEM_PROMPT,  # The prompt string defined earlier
    input_variables=["context", "question"]  # Variables to fill
)
```

**Purpose**:
- Wraps system prompt for LangChain
- Defines which variables need to be filled
- `context`: Retrieved chunks from Qdrant
- `question`: User's query

### RetrievalQA Chain (Lines 108-115)
```python
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,  # Gemini LLM
    chain_type="stuff",  # Concatenate all retrieved docs
    retriever=retriever,  # Qdrant retriever
    return_source_documents=True,  # Include source chunks in response
    chain_type_kwargs={"prompt": prompt_template}  # Custom prompt
)
```

**Chain Type "stuff"**:
- Concatenates all retrieved chunks into one prompt
- Simple and effective for small contexts
- Alternative: "map_reduce" for large contexts

### FastAPI App (Lines 119-126)
```python
app = FastAPI(title="NTIS Policy Assistant")  # Create app

app.mount("/static", StaticFiles(directory="static"), name="static")  # CSS/JS
templates = Jinja2Templates(directory="templates")  # HTML templates
```

**Purpose**:
- Creates FastAPI application
- Serves static files (CSS, JS) from `/static`
- Serves HTML templates from `/templates`

### Request Model (Lines 128-130)
```python
class ChatRequest(BaseModel):
    message: str  # User's question
```

**Purpose**:
- Validates incoming POST requests
- Ensures `message` field exists and is a string
- Pydantic automatically validates and provides error messages

### Routes (Lines 132-158)

#### GET / (Lines 135-138)
```python
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})
```

**Purpose**: Serves the chat UI HTML page

#### POST /chat (Lines 140-153)
```python
@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat message and return response."""
    try:
        # Run the QA chain
        result = qa_chain.invoke({"query": request.message})
        
        response = result.get("result", "I do not have that information in the policy document.")
        
        return {"response": response}
    
    except Exception as e:
        print(f"Error: {e}")
        return {"response": f"Error processing request: {str(e)}"}
```

**Flow**:
1. Receive user message
2. Invoke RAG chain with query
3. Extract result from chain output
4. Return JSON response
5. Handle errors gracefully

#### GET /health (Lines 155-158)
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "NTIS Policy Assistant"}
```

**Purpose**: Health check for monitoring/deployment

---

## 2. `ingest.py` - PDF Ingestion Script (91 lines)

### Imports (Lines 1-12)
```python
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader  # PDF parsing
from langchain_text_splitters import RecursiveCharacterTextSplitter  # Chunking
from langchain_huggingface import HuggingFaceEmbeddings  # Embeddings
from langchain_qdrant import QdrantVectorStore  # Qdrant integration
from qdrant_client import QdrantClient  # Direct Qdrant client
from qdrant_client.http.models import Distance, VectorParams  # Collection config
```

### Configuration (Lines 14-19)
```python
load_dotenv()

PDF_PATH = os.path.join(os.path.dirname(__file__), "Accounts, Invoicing & Refund Policy.pdf")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "policy_docs"
```

### Main Function (Lines 21-90)

#### Step 1: Load PDF (Lines 26-33)
```python
loader = PyPDFLoader(PDF_PATH)
documents = loader.load()
print(f"Loaded {len(documents)} pages")
```

**Purpose**:
- Parses PDF file
- Each page becomes a Document object
- Extracts text content and metadata

#### Step 2: Split into Chunks (Lines 35-44)
```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,        # Max characters per chunk
    chunk_overlap=150,     # Overlap between chunks
    length_function=len,   # How to measure length
    separators=["\n\n", "\n", ". ", " ", ""]  # Split priority
)
chunks = text_splitter.split_documents(documents)
```

**Chunking Strategy**:
- **800 chars**: Optimal for semantic coherence
- **150 overlap**: Prevents context loss at boundaries
- **Separators**: Tries to split at paragraph → sentence → word boundaries

**Why Chunking?**
- LLMs have token limits
- Smaller chunks = more precise retrieval
- Overlap ensures context continuity

#### Step 3: Initialize Embeddings (Lines 46-53)
```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)
```

**Same as main.py** - ensures consistency

#### Step 4: Create Qdrant Collection (Lines 55-71)
```python
client = QdrantClient(url=QDRANT_URL)

# Delete existing collection
try:
    client.delete_collection(collection_name=COLLECTION_NAME)
except Exception:
    pass

# Create new collection
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=384,  # Must match embedding dimensions
        distance=Distance.COSINE  # Similarity metric
    )
)
```

**Vector Configuration**:
- **Size**: 384 (matches all-MiniLM-L6-v2)
- **Distance**: COSINE (best for normalized embeddings)
- **Alternatives**: DOT, EUCLIDEAN

#### Step 5: Store Vectors (Lines 73-81)
```python
vector_store = QdrantVectorStore.from_documents(
    documents=chunks,  # Text chunks
    embedding=embeddings,  # Embedding function
    url=QDRANT_URL,
    collection_name=COLLECTION_NAME,
)
```

**Process**:
1. For each chunk:
   - Generate 384-dim embedding
   - Store in Qdrant with metadata
2. Qdrant automatically indexes vectors
3. Ready for similarity search

---

## 3. `templates/index.html` - Chat UI

### Key JavaScript Functions

#### `sendMessage()` (Main chat logic)
```javascript
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message || isProcessing) return;

    isProcessing = true;
    addMessage(message, 'user');  // Display user message
    userInput.value = '';
    sendBtn.disabled = true;
    showTyping();  // Show typing indicator

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        hideTyping();

        if (response.ok && data.response) {
            addMessage(data.response, 'assistant');
        } else {
            addMessage('Sorry, I encountered an error.', 'assistant');
        }
    } catch (error) {
        hideTyping();
        addMessage('Connection error.', 'assistant');
    }

    isProcessing = false;
}
```

#### `addMessage(content, type)` (Display messages)
```javascript
function addMessage(content, type) {
    removeWelcome();  // Remove welcome screen on first message
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    // Create avatar (different for user/assistant)
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.innerHTML = type === 'assistant' ? botSVG : userSVG;
    
    // Create message bubble
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `
        <span class="message-label">${type === 'assistant' ? 'NTIS Assistant' : 'You'}</span>
        <div class="message-text">${content}</div>
    `;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;  // Auto-scroll
}
```

#### `askQuestion(question)` (Quick actions)
```javascript
function askQuestion(question) {
    userInput.value = question;
    userInput.dispatchEvent(new Event('input'));  // Trigger input event
    sendMessage();
    document.querySelector('.sidebar').classList.remove('open');  // Close mobile sidebar
}
```

---

## 4. `static/style.css` - Styling

### CSS Variables (Lines 11-22)
```css
:root {
    --bg-primary: #ffffff;
    --bg-secondary: #f9fafb;
    --text-primary: #111827;
    --text-secondary: #6b7280;
    --accent-color: #2563eb;
    --sidebar-width: 280px;
    --header-height: 64px;
}
```

**Purpose**: Centralized theming for easy customization

### Layout Structure
```css
.app {
    display: flex;           /* Sidebar + Main */
    height: 100vh;
}

.sidebar {
    width: var(--sidebar-width);
    flex-shrink: 0;         /* Don't shrink */
}

.main {
    flex: 1;                /* Take remaining space */
    display: flex;
    flex-direction: column;
}
```

### Responsive Design (Lines 450+)
```css
@media (max-width: 768px) {
    .sidebar {
        position: fixed;
        transform: translateX(-100%);  /* Hidden by default */
    }
    
    .sidebar.open {
        transform: translateX(0);      /* Slide in */
    }
    
    .menu-btn {
        display: flex;                 /* Show hamburger menu */
    }
}
```

---

## 5. `.env` - Environment Configuration

```env
GOOGLE_API_KEY=AIzaSyBVipvYccz9t4Y33H8VPvHF1r2Dlx0Wziw
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=policy_docs
```

**Security Notes**:
- Never commit to Git (add to `.gitignore`)
- Use secrets manager in production
- Rotate API keys regularly

---

## 6. `requirements.txt` - Dependencies

```txt
fastapi==0.115.0              # Web framework
uvicorn==0.30.0               # ASGI server
python-dotenv==1.0.0          # Environment variables
langchain>=0.3.7              # RAG framework
langchain-google-genai>=2.0.4 # Gemini integration
langchain-community>=0.3.5    # Community integrations
langchain-qdrant>=0.2.0       # Qdrant integration
langchain-huggingface>=1.0.0  # HuggingFace embeddings
langchain-text-splitters>=1.0.0  # Text chunking
langchain-classic>=0.1.0      # Classic chains
qdrant-client>=1.12.0         # Qdrant client
sentence-transformers>=3.3.0  # Embedding models
pypdf>=5.1.0                  # PDF parsing
jinja2>=3.1.4                 # HTML templates
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     INGESTION PHASE                         │
│  (Run once: python ingest.py)                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
    ┌───────────────────────────────────────┐
    │  1. Load PDF                          │
    │     PyPDFLoader                       │
    │     → 6 pages                         │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  2. Split Text                        │
    │     RecursiveCharacterTextSplitter    │
    │     → 9 chunks (800 chars each)       │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  3. Generate Embeddings               │
    │     all-MiniLM-L6-v2                  │
    │     → 9 vectors (384-dim each)        │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  4. Store in Qdrant                   │
    │     Collection: policy_docs           │
    │     → 9 vectors indexed               │
    └───────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      QUERY PHASE                            │
│  (Runtime: User asks question)                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
    ┌───────────────────────────────────────┐
    │  1. User Query                        │
    │     "What is the refund policy?"      │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  2. Generate Query Embedding          │
    │     all-MiniLM-L6-v2                  │
    │     → 384-dim vector                  │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  3. Vector Search (Qdrant)            │
    │     Cosine similarity                 │
    │     → Top 4 chunks                    │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  4. Build Prompt                      │
    │     System Prompt + Context + Query   │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  5. LLM Generation                    │
    │     Gemini 2.5 Flash                  │
    │     → Natural language answer         │
    └───────────────┬───────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────────────┐
    │  6. Return to User                    │
    │     JSON: {"response": "..."}         │
    └───────────────────────────────────────┘
```

---

## Key Concepts Explained

### 1. RAG (Retrieval-Augmented Generation)
- **Problem**: LLMs don't know your specific data
- **Solution**: Retrieve relevant context, then generate answer
- **Benefit**: Accurate, fact-based responses

### 2. Vector Embeddings
- **Purpose**: Convert text to numbers for similarity search
- **How**: Neural network encodes semantic meaning
- **Example**: "refund policy" and "return money" have similar vectors

### 3. Cosine Similarity
```
similarity = (A · B) / (||A|| × ||B||)
```
- Measures angle between vectors
- Range: -1 to 1 (1 = identical)
- Works well with normalized embeddings

### 4. Chunking Strategy
- **Too small**: Loses context
- **Too large**: Dilutes relevance
- **Sweet spot**: 500-1000 characters
- **Overlap**: Prevents information loss

---

## Performance Optimization Tips

### 1. Speed Up Embeddings
```python
# Use GPU
model_kwargs={'device': 'cuda'}

# Or use smaller model
model_name="sentence-transformers/all-MiniLM-L12-v2"
```

### 2. Reduce Latency
```python
# Decrease retrieval count
search_kwargs={"k": 2}

# Use faster LLM
model="gemini-1.5-flash-8b"
```

### 3. Cache Results
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_embedding(text):
    return embeddings.embed_query(text)
```

---

## Security Best Practices

### 1. API Key Protection
```python
# ✅ Good
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ❌ Bad
GOOGLE_API_KEY = "AIzaSy..."  # Never hardcode
```

### 2. Input Validation
```python
class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000)  # Limit length
```

### 3. Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: ChatRequest):
    ...
```

---

**End of Code Reference**
