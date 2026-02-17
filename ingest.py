"""
PDF Ingestion Script for NTIS Policy RAG Chatbot
Loads PDF, chunks it, creates embeddings, and stores in Qdrant.
"""
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

load_dotenv()

# Configuration
PDF_PATH = os.path.join(os.path.dirname(__file__), "Accounts, Invoicing & Refund Policy.pdf")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "policy_docs"

def main():
    print("=" * 50)
    print("NTIS Policy Document Ingestion")
    print("=" * 50)
    
    # 1. Load PDF
    print(f"\n[1/5] Loading PDF: {PDF_PATH}")
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
    
    loader = PyPDFLoader(PDF_PATH)
    documents = loader.load()
    print(f"      Loaded {len(documents)} pages")
    
    # 2. Split into chunks
    print("\n[2/5] Splitting into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"      Created {len(chunks)} chunks")
    
    # 3. Initialize embeddings model
    print("\n[3/5] Loading embeddings model...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    print("      Model loaded: all-MiniLM-L6-v2")
    
    # 4. Connect to Qdrant and create collection
    print(f"\n[4/5] Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)
    
    # Delete existing collection if exists
    try:
        client.delete_collection(collection_name=COLLECTION_NAME)
        print(f"      Deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        pass
    
    # Create new collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"      Created collection: {COLLECTION_NAME}")
    
    # 5. Store vectors in Qdrant
    print("\n[5/5] Storing vectors in Qdrant...")
    vector_store = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
    )
    print(f"      Stored {len(chunks)} vectors")
    
    print("\n" + "=" * 50)
    print("SUCCESS! Document ingestion complete.")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Vectors: {len(chunks)}")
    print("=" * 50)

if __name__ == "__main__":
    main()
