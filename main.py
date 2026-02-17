"""
NTIS Policy RAG Chatbot - FastAPI Backend
Uses Qdrant for vector storage, HuggingFace embeddings, and Gemini LLM.
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from qdrant_client import QdrantClient

load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "policy_docs"

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are the NTIS Policy Assistant for a translation and interpreting company.

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

# ─────────────────────────────────────────────
# INITIALIZE COMPONENTS
# ─────────────────────────────────────────────
print("Initializing NTIS Policy RAG Chatbot...")

# Initialize embeddings
print("Loading embeddings model...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# Connect to Qdrant
print(f"Connecting to Qdrant at {QDRANT_URL}...")
qdrant_client = QdrantClient(url=QDRANT_URL)

# Create vector store
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)

# Create retriever (k=4 chunks)
retriever = vector_store.as_retriever(search_kwargs={"k": 4})

# Initialize Gemini LLM
print("Initializing Gemini model...")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.5,
    google_api_key=GOOGLE_API_KEY,
)

# Create prompt template
prompt_template = PromptTemplate(
    template=SYSTEM_PROMPT,
    input_variables=["context", "question"]
)

# Create RetrievalQA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"prompt": prompt_template}
)

print("Initialization complete!")

# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────
app = FastAPI(title="NTIS Policy Assistant")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Request model
class ChatRequest(BaseModel):
    message: str

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})

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

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "NTIS Policy Assistant"}
