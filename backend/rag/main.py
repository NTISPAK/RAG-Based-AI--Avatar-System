"""NIRA Policy RAG Backend.

FastAPI server that provides the /chat endpoint for the LiveTalking avatar.
Uses Qdrant for vector retrieval and Google Gemini for generation."""

import os
import re
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
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ur")
SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "en,ur").split(",")


SYSTEM_PROMPT = """You are Sara, the friendly female AI receptionist for Nauman International Recruitment Agency (NIRA). You are a woman. You assist visitors with questions about study visas, work permits, and agency services.

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

URDU_SYSTEM_PROMPT = """You are Sara, the friendly female AI receptionist for Nauman International Recruitment Agency (NIRA). You are a woman.

RESPONSE GUIDELINES:
- You MUST respond ENTIRELY in Urdu script. Do NOT use any English words.
- Use feminine gender forms throughout since you are a woman.
- Answer ONLY what was asked. Do NOT dump all available information.
- Keep responses to 3-5 sentences. Be concise but warm and conversational.
- Use natural spoken Urdu that sounds good when read aloud by a digital avatar.
- No markdown, no bullet points, no asterisks, no special formatting.
- End with a short offer to help further.

STRICT RULES:
1. Use ONLY the context below. Never invent information.
2. Stay precise to the question. Do not volunteer unrelated information.
3. If the answer is not in the context, say in Urdu: "I'm sorry, I don't have that specific information right now, but I can connect you with one of our consultants who can help."

CONTEXT:
{context}

QUESTION: {question}

ANSWER (in Urdu script only, 3-5 sentences, feminine forms, warm spoken tone):"""


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
    timeout=60,
)

prompt_template = PromptTemplate(
    template=SYSTEM_PROMPT,
    input_variables=["context", "question"]
)

urdu_prompt_template = PromptTemplate(
    template=URDU_SYSTEM_PROMPT,
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


def _invoke_with_retry(llm_instance, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return llm_instance.invoke(prompt)
        except Exception as e:
            err = str(e)
            if "RESOURCE_EXHAUSTED" in err or "429" in err or "503" in err or "UNAVAILABLE" in err:
                match = re.search(r'retry in (\d+\.?\d*)s', err)
                wait = min(float(match.group(1)) if match else 10, 15)
                print(f"[Retry] Rate limited, waiting {wait:.0f}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded for Gemini API call")


def run_rag_pipeline(message: str, language: str = "en") -> str:
    docs = retriever.invoke(message)
    print(f"[RAG] Retrieved {len(docs)} docs for query: {message!r}")
    for i, doc in enumerate(docs):
        print(f"  [Doc {i}] {doc.page_content[:120]!r}")
    context = "\n\n".join(doc.page_content for doc in docs)
    template = urdu_prompt_template if language == "ur" else prompt_template
    prompt = template.format(context=context, question=message)
    print(f"[RAG] Prompt length: {len(prompt)} chars, language: {language}")
    response = _invoke_with_retry(llm, prompt)
    answer = response.content if hasattr(response, "content") else str(response)
    print(f"[RAG] Answer: {answer[:200]!r}")
    return answer


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        start_time = time.time()
        original_message = request.message
        original_language = request.language
        
        print(f"[Chat] Received message in {original_language}: {original_message[:100]}...")
        
        # 1-call approach: send raw input directly to RAG + Gemini (no separate translation).
        # Gemini understands Romanized Urdu (e.g. "mujhay visa k baray may batao").
        # This is critical: free tier only allows ~20 RPD, so 1 call per query maximizes usage.
        if original_language == "ur":
            print(f"[Chat] Running RAG with direct Urdu output (1 API call)...")
            final_answer = run_rag_pipeline(original_message, language="ur")
        else:
            print(f"[Chat] Running RAG pipeline...")
            final_answer = run_rag_pipeline(original_message)
        
        total_time = time.time() - start_time
        print(f"[Chat] Total processing time: {total_time:.2f}s")
        
        return {
            "response": final_answer,
            "language": original_language,
            "processing_time": round(total_time, 2)
        }
        
    except Exception as exc:
        print(f"[Chat Error] {exc}")
        if request.language == "ur":
            error_message = "معذرت، آپ کی درخواست پر عمل کرنے میں خرابی ہوئی۔ براہ کرم دوبارہ کوشش کریں۔"
        else:
            error_message = "I'm sorry, I encountered an error processing your request."
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
