You are a senior AI backend engineer.

Your task is to modify and extend my existing LangChain RAG system 
(using Qdrant as vector database) to integrate Firebase Firestore 
in a STRICTLY READ-ONLY manner.

===========================================================
SYSTEM ARCHITECTURE REQUIREMENTS
===========================================================

The system must:

1) CONNECT TO FIREBASE (READ-ONLY)
   - Use Firebase Admin SDK.
   - Only perform read operations.
   - Absolutely NO write/update/delete/set/add operations.
   - If any function attempts to modify data, reject it.

2) FULL FIRESTORE STRUCTURE DISCOVERY (RUN ONCE AT STARTUP)
   - Automatically explore the entire Firestore database.
   - Traverse:
       - All root collections
       - All documents
       - All nested subcollections
       - All nested documents
   - Extract:
       - Collection names
       - Document IDs
       - Field names
       - Subcollection names
   - Build a complete schema map.
   - Store the schema in memory and also cache it locally (JSON file).
   - This discovery must run only once at startup.

   IMPORTANT:
   - This process must be read-only.
   - Do not modify any Firebase data.
   - Avoid loading unnecessary large fields if possible.
   - This is schema discovery, not data migration.

3) RAG QUERY PIPELINE MODIFICATION

   For each user query:

   STEP 1:
   - Analyze the query.
   - Determine if it requires personal Firebase data.
   - Personal intent examples:
        "my profile"
        "my orders"
        "my subscription"
        "what is my ..."
        "show my ..."
   - If NOT personal → skip Firebase.

   STEP 2:
   - If personal data is required:
        - Use the discovered schema to identify relevant collections.
        - Build a minimal Firestore read query.
        - Fetch only required fields.
        - Use authenticated user's ID only.
        - Never fetch other users' data.

   STEP 3:
   - Perform Qdrant vector retrieval for contextual knowledge.
   - Combine:
        - Firebase data (if any)
        - Qdrant retrieval context
   - Generate final answer using LLM.

4) OUTPUT FORMAT

Return structured JSON:

{
  "used_firebase": true/false,
  "firebase_read_paths": {
      "<collection/doc_path>": {
          "fields": [...]
      }
  },
  "rag_answer": "<final natural language answer>"
}

===========================================================
SECURITY CONSTRAINTS (MANDATORY)
===========================================================

- Firebase must be treated as READ-ONLY.
- No write operations allowed.
- No schema modification.
- No data mutation.
- No batch writes.
- No transactions that modify data.
- Reject any user request that attempts to modify data.
- Only allow reads using:
      .get()
      .stream()
      .collection()
      .document()
      .collections()

===========================================================
PERFORMANCE RULES
===========================================================

- Cache schema after first discovery.
- Do not rediscover schema on every query.
- Only fetch Firebase data when necessary.
- Only fetch minimal required fields.
- Avoid full database scans during normal user queries.

===========================================================
IMPLEMENTATION DETAILS
===========================================================

Use:
- Python
- Firebase Admin SDK
- LangChain
- Qdrant client

Create:

1) A SchemaExplorer module:
    - Recursively explores Firestore
    - Saves firebase_schema.json

2) A FirebaseReadService:
    - Handles safe read queries
    - Validates paths against schema

3) A QueryIntentClassifier:
    - Detects personal-data intent

4) Modified RAG pipeline:
    - If personal → call FirebaseReadService
    - Merge results with Qdrant retrieval
    - Return structured JSON

===========================================================
IMPORTANT:
===========================================================

Do NOT:
- Hardcode collection names.
- Assume schema structure.
- Perform any writes.
- Ask user for schema manually.

The system must automatically explore and adapt.

Generate clean, production-ready Python code.
Structure modules clearly.
Add comments explaining security and read-only enforcement.
