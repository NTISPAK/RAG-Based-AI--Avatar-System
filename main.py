"""NIRA Policy RAG Backend.

FastAPI server that provides the /chat endpoint for the LiveTalking avatar.
Uses Qdrant for vector retrieval and Google Gemini for generation."""

import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, validator
from qdrant_client import QdrantClient
from translation_service import TranslationService


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "policy_docs")
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "en,ur").split(",")


SYSTEM_PROMPT = """You are the friendly AI receptionist for Nauman International Recruitment Agency (NIRA). You assist visitors with questions about study visas, work permits, and agency services.

RESPONSE GUIDELINES:
- Answer ONLY what was asked. Do NOT dump all available information.
- Keep responses to 3-5 sentences. Be concise but warm and conversational.
- Use natural spoken English — this will be read aloud by a digital avatar.
- No markdown, no bullet points, no asterisks, no special formatting.
- If the question is broad like "what services do you offer", give a brief overview, not an exhaustive list.
- End with a short offer to help further.

STRICT RULES:
1. Use ONLY the context below. Never invent information.
2. Stay precise to the question. Do not volunteer unrelated information from the context.
3. If the answer is not in the context, say: "I'm sorry, I don't have that specific information right now, but I can connect you with one of our consultants who can help."

CONTEXT:
{context}

QUESTION: {question}

ANSWER (precise to the question, 3-5 sentences, warm and spoken tone):"""


print("Initializing NTIS Policy RAG Chatbot...")

print("Loading embeddings model (English)...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

print(f"Connecting to Qdrant at {QDRANT_URL}...")
qdrant_client = QdrantClient(url=QDRANT_URL)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)

retriever = vector_store.as_retriever(search_kwargs={"k": 4})

print("Initializing Gemini model...")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY,
)

prompt_template = PromptTemplate(
    template=SYSTEM_PROMPT,
    input_variables=["context", "question"]
)

# Initialize translation service
if ENABLE_TRANSLATION:
    print("Initializing translation service...")
    translator = TranslationService(api_key=GOOGLE_API_KEY)
    print(f"Translation enabled. Supported languages: {SUPPORTED_LANGUAGES}")
else:
    translator = None
    print("Translation disabled.")

print("Initialization complete!")


app = FastAPI(title="NTIS Policy Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    language: str = DEFAULT_LANGUAGE
    
    @validator('language')
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}. Supported: {SUPPORTED_LANGUAGES}")
        return v


def run_rag_pipeline(message: str) -> str:
    docs = retriever.invoke(message)
    print(f"[RAG] Retrieved {len(docs)} docs for query: {message!r}")
    for i, doc in enumerate(docs):
        print(f"  [Doc {i}] {doc.page_content[:120]!r}")
    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = prompt_template.format(context=context, question=message)
    print(f"[RAG] Prompt length: {len(prompt)} chars")
    response = llm.invoke(prompt)
    answer = response.content if hasattr(response, "content") else str(response)
    print(f"[RAG] Answer: {answer[:200]!r}")
    return answer


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        start_time = time.time()
        original_message = request.message
        original_language = request.language
        
        print(f"[Chat] Received message in {original_language}: {original_message[:100]}...")
        
        # If input is Urdu and translation is enabled, translate to English first
        if original_language == "ur" and translator:
            print(f"[Chat] Translating Urdu input to English...")
            english_message = translator.translate_urdu_to_english(original_message)
            print(f"[Chat] Translated to English: {english_message[:100]}...")
        else:
            english_message = original_message
        
        # Run RAG pipeline in English
        print(f"[Chat] Running RAG pipeline...")
        english_answer = run_rag_pipeline(english_message)
        
        # If output should be Urdu and translation is enabled, translate response
        if original_language == "ur" and translator:
            print(f"[Chat] Translating English response to Urdu...")
            urdu_answer = translator.translate_english_to_urdu(english_answer)
            print(f"[Chat] Translated to Urdu: {urdu_answer[:100]}...")
            final_answer = urdu_answer
        else:
            final_answer = english_answer
        
        total_time = time.time() - start_time
        print(f"[Chat] Total processing time: {total_time:.2f}s")
        
        return {
            "response": final_answer,
            "language": original_language,
            "processing_time": round(total_time, 2)
        }
        
    except Exception as exc:
        print(f"[Chat Error] {exc}")
        error_message = "I'm sorry, I encountered an error processing your request."
        if request.language == "ur" and translator:
            error_message = translator.translate_english_to_urdu(error_message)
        return {
            "response": error_message,
            "language": request.language,
            "error": str(exc)
        }


@app.get("/health")
async def health():
    health_data = {
        "status": "ok",
        "service": "NIRA Policy Assistant",
        "translation_enabled": ENABLE_TRANSLATION,
        "supported_languages": SUPPORTED_LANGUAGES
    }
    
    if translator:
        health_data["translation_metrics"] = translator.get_metrics()
    
    return health_data


@app.get("/languages")
async def get_languages():
    """Get supported languages."""
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "default_language": DEFAULT_LANGUAGE,
        "translation_enabled": ENABLE_TRANSLATION
    }


@app.post("/translate")
async def translate_text(text: str, source_lang: str, target_lang: str):
    """Direct translation endpoint for testing."""
    if not translator:
        return {"error": "Translation is disabled"}
    
    if source_lang not in SUPPORTED_LANGUAGES or target_lang not in SUPPORTED_LANGUAGES:
        return {"error": f"Unsupported language. Supported: {SUPPORTED_LANGUAGES}"}
    
    try:
        if source_lang == "ur" and target_lang == "en":
            translation = translator.translate_urdu_to_english(text)
        elif source_lang == "en" and target_lang == "ur":
            translation = translator.translate_english_to_urdu(text)
        else:
            return {"error": "Translation between these languages not supported"}
        
        return {
            "original": text,
            "translation": translation,
            "source_language": source_lang,
            "target_language": target_lang
        }
    except Exception as e:
        return {"error": str(e)}
