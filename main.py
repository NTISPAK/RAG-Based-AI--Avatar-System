"""
NTIS Policy RAG Chatbot - FastAPI Backend
==========================================
Uses Qdrant for vector storage, HuggingFace embeddings, and Gemini LLM.
Integrates Firebase Firestore in STRICTLY READ-ONLY mode for user data.

SECURITY: Firebase integration is READ-ONLY.
- No write/update/delete operations allowed
- All write attempts are blocked and raise PermissionError
- User data isolation is enforced
"""
import os
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import PromptTemplate
from qdrant_client import QdrantClient

# Firebase integration modules (READ-ONLY)
from firebase_schema_explorer import (
    get_schema_explorer,
    discover_firestore_schema,
    get_firestore_schema
)
from firebase_read_service import (
    get_read_service,
    read_user_data,
    format_firebase_data_for_llm,
    FirebaseReadResult
)
from query_intent_classifier import (
    get_classifier,
    classify_query,
    should_query_firebase,
    IntentClassification,
    QueryIntent
)
# AI-based intent classifier (with rule-based fallback)
from ai_intent_classifier import (
    get_ai_classifier,
    should_query_firebase_ai
)
from firebase_auth import (
    verify_firebase_token,
    require_auth,
    optional_auth,
    AuthenticatedUser
)

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "policy_docs"

# ─────────────────────────────────────────────
# SYSTEM PROMPT (Enhanced with Firebase data support)
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are the NTIS Policy Assistant, a helpful AI for a translation and interpreting company.

Your role is to answer questions using ONLY the information provided below. Be conversational, friendly, and professional.

DATA SOURCES:
1. POLICY DOCUMENTS - Company policies (refunds, payments, invoicing)
2. USER DATA - Personal bookings, profile, orders (if user is logged in)

CRITICAL RULES:
1. Answer ONLY using the context and user data provided below
2. NEVER make up or assume information not in the context
3. If the EXACT answer isn't in the context, look for RELATED information that helps answer the question
4. If truly no relevant information exists, say: "I don't have specific information about that in my current data."
5. Be concise but complete - give all relevant details from the context
6. Use natural language - synthesize information, don't just copy-paste
7. For user data, present it clearly and only show what's relevant to the question
8. If the question is phrased differently but relates to policy content, find and use that content

FORMATTING GUIDELINES:
- When showing user's bookings/data, use clean bullet points or numbered lists
- Format dates clearly (e.g., "January 15, 2024" not raw timestamps)
- For status fields, use plain language (e.g., "Completed" not "isCompleted: true")
- Group related information together
- Use line breaks to separate different items
- Make it easy to scan and read

CONTEXT FROM POLICY DOCUMENTS:
{context}

USER'S PERSONAL DATA:
{user_data}

USER QUESTION: {question}

YOUR ANSWER (natural, well-formatted, conversational, based only on the information above):"""

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

# Create retriever (k=5 chunks for better coverage)
retriever = vector_store.as_retriever(search_kwargs={"k": 5})

# Initialize Gemini LLM
print("Initializing Gemini model...")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.5,
    google_api_key=GOOGLE_API_KEY,
)

# Create prompt template (with user_data for Firebase integration)
prompt_template = PromptTemplate(
    template=SYSTEM_PROMPT,
    input_variables=["context", "user_data", "question"]
)

print("Initialization complete!")

# ─────────────────────────────────────────────
# FIREBASE INITIALIZATION (READ-ONLY)
# ─────────────────────────────────────────────
firebase_schema = None
firebase_enabled = False

print("\nInitializing Firebase integration (READ-ONLY)...")
try:
    # Discover schema at startup (runs once, then cached)
    firebase_schema = discover_firestore_schema()
    
    # Initialize AI-based classifier with schema (includes rule-based fallback)
    ai_classifier = get_ai_classifier(firebase_schema)
    
    # Also keep rule-based classifier as backup
    classifier = get_classifier(firebase_schema)
    
    # Initialize read service
    read_service = get_read_service()
    
    firebase_enabled = True
    collection_count = len(firebase_schema.get("collections", {}))
    print(f"✓ Firebase schema discovered: {collection_count} collections")
    print(f"✓ Schema cached to: firebase_schema.json")
    print("✓ AI Intent Classifier initialized (with rule-based fallback)")
    print("✓ Firebase READ-ONLY mode active")
    
except FileNotFoundError as e:
    print(f"⚠ Firebase credentials not found: {e}")
    print("  Set FIREBASE_CREDENTIALS_PATH in .env")
    print("  Continuing without Firebase integration...")
except Exception as e:
    print(f"⚠ Firebase initialization failed: {e}")
    print("  Continuing without Firebase integration...")

# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────
app = FastAPI(title="NTIS Policy Assistant")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Request/Response models
class ChatRequest(BaseModel):
    """Chat request with optional user ID for Firebase queries."""
    message: str
    user_id: Optional[str] = Field(None, description="User ID for personal data queries")


class ChatResponse(BaseModel):
    """Structured response with Firebase metadata."""
    used_firebase: bool = Field(False, description="Whether Firebase was queried")
    firebase_read_paths: Dict[str, Any] = Field(default_factory=dict, description="Paths read from Firebase")
    rag_answer: str = Field(..., description="The natural language answer")
    intent: str = Field("unknown", description="Detected query intent")
    confidence: float = Field(0.0, description="Intent classification confidence")

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: Optional[AuthenticatedUser] = Depends(optional_auth)
):
    """
    Process chat message with RAG + Firebase integration.
    
    AUTHENTICATION:
    - Optional for policy-only questions
    - REQUIRED for personal data queries
    - Only returns data for the authenticated user
    
    Pipeline:
    1. Classify query intent
    2. If personal data needed → Verify authentication → Query Firebase (READ-ONLY)
    3. Retrieve context from Qdrant
    4. Combine contexts and generate response
    5. Return structured JSON with metadata
    """
    try:
        # Initialize response variables
        user_data_context = "No user data requested or available."
        firebase_read_paths: Dict[str, Any] = {}
        used_firebase = False
        intent_type = "unknown"
        confidence = 0.0
        
        # Log authentication status
        if current_user:
            logger.info(f"[Auth] Authenticated user: {current_user.uid} ({current_user.email})")
        else:
            logger.info("[Auth] Unauthenticated request")
        
        # ─────────────────────────────────────────
        # STEP 1: Classify query intent using AI (with fallback)
        # ─────────────────────────────────────────
        if firebase_enabled and firebase_schema:
            # Use AI-based classifier (automatically falls back to rule-based if needed)
            should_query, classification = should_query_firebase_ai(
                request.message,
                confidence_threshold=0.4,
                schema=firebase_schema
            )
            
            intent_type = classification.intent.value
            confidence = classification.confidence
            
            logger.info(f"[AI Intent] {intent_type} (confidence: {confidence:.2f})")
            logger.info(f"[AI Intent] Requires Firebase: {classification.requires_firebase}")
            
            # ─────────────────────────────────────────
            # STEP 2: Query Firebase if needed (READ-ONLY)
            # ─────────────────────────────────────────
            if should_query and classification.requires_firebase:
                logger.info(f"[Firebase] Personal data query detected")
                logger.info(f"[Firebase] Suggested collections: {classification.suggested_collections}")
                
                # SECURITY: Require authentication for personal data
                if not current_user:
                    logger.warning("[Firebase] Personal data requested but user not authenticated")
                    user_data_context = (
                        "⚠️ Authentication Required\n\n"
                        "You asked for personal data, but you're not logged in. "
                        "Please log in to access your bookings, profile, and other personal information."
                    )
                else:
                    # SECURITY: Use authenticated user's UID only
                    user_id = current_user.uid
                    logger.info(f"[Firebase] Querying data for authenticated user: {user_id}")
                    
                    # Query Firebase (READ-ONLY operations only)
                    try:
                        # Query user-specific data ONLY
                        firebase_result = read_user_data(
                            user_id=user_id,
                            collections=classification.suggested_collections
                        )
                        
                        if firebase_result.success and firebase_result.data:
                            used_firebase = True
                            user_data_context = format_firebase_data_for_llm(firebase_result)
                            
                            # Track read paths for response
                            firebase_read_paths = read_service.get_read_paths()
                            
                            logger.info(f"[Firebase] Retrieved {firebase_result.document_count} documents")
                        else:
                            user_data_context = "No matching data found in database for your account."
                            logger.info("[Firebase] No data found for user")
                            
                    except PermissionError as e:
                        # SECURITY: Write operation was attempted and blocked
                        logger.error(f"[SECURITY] Blocked operation: {e}")
                        user_data_context = "Security: Read-only access enforced."
                    except Exception as e:
                        logger.error(f"[Firebase] Error: {e}")
                        user_data_context = f"Database query error: {str(e)}"
        
        # ─────────────────────────────────────────
        # STEP 3: Retrieve context from Qdrant with similarity scores
        # ─────────────────────────────────────────
        # Use similarity_search_with_score to get relevance scores
        docs_with_scores = vector_store.similarity_search_with_score(request.message, k=5)
        
        logger.info(f"[Qdrant] Retrieved {len(docs_with_scores)} policy chunks")
        
        # ─────────────────────────────────────────
        # STEP 3.5: Smart relevance checking to save LLM costs
        # ─────────────────────────────────────────
        RELEVANCE_THRESHOLD = 0.2  # Minimum similarity score (0-1) - very permissive to avoid false negatives
        
        if docs_with_scores:
            # Extract scores (higher score = more similar)
            max_score = max(score for _, score in docs_with_scores)
            avg_score = sum(score for _, score in docs_with_scores) / len(docs_with_scores)
            
            logger.info(f"[Relevance] Max: {max_score:.3f}, Avg: {avg_score:.3f} (threshold: {RELEVANCE_THRESHOLD})")
            
            # Conservative filtering: Only skip LLM for clearly irrelevant queries
            # Skip only if ALL these conditions are met:
            # 1. Max score is VERY low (< 0.2)
            # 2. Average score is also low (< 0.15)
            # 3. No Firebase data was retrieved
            # 4. Intent is unknown or clearly off-topic
            should_skip = (
                max_score < RELEVANCE_THRESHOLD and 
                avg_score < 0.15 and
                not used_firebase and 
                intent_type not in ["general_info", "policy_question", "personal_data", "payment_info", "booking_info"]
            )
            
            if should_skip:
                logger.info("[Cost Optimization] Very low relevance - skipping LLM call")
                return ChatResponse(
                    used_firebase=False,
                    firebase_read_paths={},
                    rag_answer="I don't have that information in my current data. Could you rephrase your question or ask about NTIS policies, refunds, payments, or invoicing?",
                    intent=intent_type,
                    confidence=confidence
                )
            
            # Log if we're in borderline territory
            if max_score < 0.35:
                logger.warning(f"[Relevance] Borderline relevance detected (score: {max_score:.3f}) - proceeding with LLM call to avoid false negative")
        
        # Extract just the documents for context
        docs = [doc for doc, score in docs_with_scores]
        policy_context = "\n\n".join([doc.page_content for doc in docs])
        
        # ─────────────────────────────────────────
        # STEP 4: Generate response with LLM
        # ─────────────────────────────────────────
        full_prompt = prompt_template.format(
            context=policy_context,
            user_data=user_data_context,
            question=request.message
        )
        
        llm_response = llm.invoke(full_prompt)
        
        # Extract text from response
        if hasattr(llm_response, 'content'):
            answer = llm_response.content
        else:
            answer = str(llm_response)
        
        # ─────────────────────────────────────────
        # STEP 5: Return structured response
        # ─────────────────────────────────────────
        return ChatResponse(
            used_firebase=used_firebase,
            firebase_read_paths=firebase_read_paths,
            rag_answer=answer,
            intent=intent_type,
            confidence=confidence
        )
    
    except Exception as e:
        logger.error(f"[Error] {e}")
        import traceback
        traceback.print_exc()
        
        return ChatResponse(
            used_firebase=False,
            firebase_read_paths={},
            rag_answer=f"Error processing request: {str(e)}",
            intent="error",
            confidence=0.0
        )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "NTIS Policy Assistant",
        "firebase_enabled": firebase_enabled,
        "firebase_collections": len(firebase_schema.get("collections", {})) if firebase_schema else 0
    }


@app.get("/schema")
async def get_schema():
    """
    Get the discovered Firebase schema.
    
    READ-ONLY: This endpoint only returns cached schema information.
    """
    if not firebase_enabled or not firebase_schema:
        return {
            "enabled": False,
            "message": "Firebase integration not enabled"
        }
    
    return {
        "enabled": True,
        "discovered_at": firebase_schema.get("discovered_at"),
        "total_collections": firebase_schema.get("total_collections", 0),
        "total_documents_sampled": firebase_schema.get("total_documents_sampled", 0),
        "total_fields_discovered": firebase_schema.get("total_fields_discovered", 0),
        "collections": list(firebase_schema.get("collections", {}).keys())
    }


@app.post("/classify")
async def classify_intent(request: ChatRequest):
    """
    Classify a query's intent without executing it.
    
    Useful for debugging and understanding how queries are classified.
    """
    if not firebase_enabled:
        return {
            "firebase_enabled": False,
            "message": "Firebase integration not enabled"
        }
    
    classification = classify_query(request.message, firebase_schema)
    
    return {
        "query": request.message,
        "intent": classification.intent.value,
        "confidence": classification.confidence,
        "requires_firebase": classification.requires_firebase,
        "user_id_required": classification.user_id_required,
        "suggested_collections": classification.suggested_collections,
        "suggested_fields": classification.suggested_fields,
        "matched_patterns": classification.matched_patterns,
        "explanation": classification.explanation
    }


# Legacy endpoint for backward compatibility
@app.post("/chat/simple")
async def chat_simple(request: ChatRequest):
    """
    Simple chat endpoint without Firebase integration.
    
    Returns only the RAG answer without structured metadata.
    """
    try:
        # Retrieve context from Qdrant only
        docs = retriever.invoke(request.message)
        policy_context = "\n\n".join([doc.page_content for doc in docs])
        
        # Generate response
        full_prompt = prompt_template.format(
            context=policy_context,
            user_data="No user data requested.",
            question=request.message
        )
        
        llm_response = llm.invoke(full_prompt)
        
        if hasattr(llm_response, 'content'):
            answer = llm_response.content
        else:
            answer = str(llm_response)
        
        return {"response": answer}
    
    except Exception as e:
        logger.error(f"[Error] {e}")
        return {"response": f"Error: {str(e)}"}
