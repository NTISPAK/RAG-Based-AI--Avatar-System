"""NIRA Policy RAG Backend.

FastAPI server that provides the /chat endpoint for the LiveTalking avatar.
Uses Qdrant for vector retrieval and Google Gemini for generation."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
from qdrant_client import QdrantClient


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "policy_docs")


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
        answer = run_rag_pipeline(request.message)
        return {"response": answer}
    except Exception as exc:
        print(f"Error: {exc}")
        return {"response": f"Error processing request: {exc}"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "NIRA Policy Assistant"}
