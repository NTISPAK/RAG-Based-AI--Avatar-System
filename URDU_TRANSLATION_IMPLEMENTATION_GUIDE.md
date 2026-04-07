# Urdu Translation Layer Implementation Guide

## Overview

Add bidirectional Urdu translation to your RAG system:
- **Input Flow:** Urdu → English → RAG → English → Urdu
- **Output:** User speaks/types in Urdu, avatar responds in Urdu

---

## Approach Options

### Option 1: Google Translate API (Recommended - Easiest)
**Pros:**
- ✅ Excellent Urdu support
- ✅ Fast and reliable
- ✅ Easy integration
- ✅ Free tier: 500,000 characters/month
- ✅ Same Google Cloud account as Gemini

**Cons:**
- ⚠️ Requires API key
- ⚠️ Costs after free tier ($20/1M characters)

**Best For:** Production use, high quality needed

---

### Option 2: Google Gemini for Translation (Recommended - Cost-Effective)
**Pros:**
- ✅ Already using Gemini API
- ✅ Excellent Urdu support
- ✅ No additional API setup
- ✅ Can handle context-aware translation
- ✅ Free tier: 1,500 requests/day

**Cons:**
- ⚠️ Slightly slower than dedicated translation API
- ⚠️ Uses your Gemini quota

**Best For:** Quick implementation, cost-effective

---

### Option 3: Open-Source Models (Helsinki-NLP)
**Pros:**
- ✅ Free and unlimited
- ✅ Run locally or on your server
- ✅ No API dependencies
- ✅ Privacy-friendly

**Cons:**
- ⚠️ Lower quality for Urdu
- ⚠️ Requires more resources
- ⚠️ Slower inference

**Best For:** Privacy-critical applications, offline use

---

### Option 4: Azure Translator (Enterprise)
**Pros:**
- ✅ Enterprise-grade
- ✅ Good Urdu support
- ✅ High availability

**Cons:**
- ⚠️ More expensive
- ⚠️ Additional account setup

**Best For:** Enterprise deployments

---

## Recommended Architecture

### Translation Flow

```
┌─────────────────────────────────────────────────────────┐
│                    User Input (Urdu)                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Translation Service                        │
│              Urdu → English                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              RAG Pipeline (English)                     │
│  1. Embed query                                         │
│  2. Retrieve from Qdrant                                │
│  3. Generate with Gemini                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Translation Service                        │
│              English → Urdu                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Avatar Response (Urdu)                     │
│              + Urdu TTS (Edge TTS)                      │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Translation Service (Recommended: Gemini)

**Why Gemini?**
1. Already integrated in your system
2. Excellent Urdu support
3. No additional API setup
4. Context-aware translation
5. Cost-effective

**Implementation Steps:**

#### Step 1: Create Translation Module

```python
# translation_service.py
from langchain_google_genai import ChatGoogleGenerativeAI
import os

class TranslationService:
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3,  # Lower temp for consistent translation
            google_api_key=api_key,
        )
    
    def translate_urdu_to_english(self, urdu_text: str) -> str:
        """Translate Urdu text to English."""
        prompt = f"""Translate the following Urdu text to English. 
Provide ONLY the translation, no explanations.

Urdu text: {urdu_text}

English translation:"""
        
        response = self.llm.invoke(prompt)
        return response.content.strip()
    
    def translate_english_to_urdu(self, english_text: str) -> str:
        """Translate English text to Urdu."""
        prompt = f"""Translate the following English text to Urdu.
Use natural, conversational Urdu that sounds good when spoken aloud.
Provide ONLY the translation, no explanations.

English text: {english_text}

Urdu translation:"""
        
        response = self.llm.invoke(prompt)
        return response.content.strip()
```

#### Step 2: Update RAG Backend

```python
# main.py (updated)
from translation_service import TranslationService

# Initialize translation service
print("Initializing translation service...")
translator = TranslationService(api_key=GOOGLE_API_KEY)

class ChatRequest(BaseModel):
    message: str
    language: str = "en"  # "en" or "ur" (Urdu)

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        original_message = request.message
        
        # If input is Urdu, translate to English first
        if request.language == "ur":
            print(f"[Translation] Urdu input: {original_message}")
            english_message = translator.translate_urdu_to_english(original_message)
            print(f"[Translation] English: {english_message}")
        else:
            english_message = original_message
        
        # Run RAG pipeline in English
        english_answer = run_rag_pipeline(english_message)
        
        # If output should be Urdu, translate response
        if request.language == "ur":
            print(f"[Translation] English response: {english_answer}")
            urdu_answer = translator.translate_english_to_urdu(english_answer)
            print(f"[Translation] Urdu response: {urdu_answer}")
            return {"response": urdu_answer, "language": "ur"}
        else:
            return {"response": english_answer, "language": "en"}
            
    except Exception as exc:
        print(f"Error: {exc}")
        return {"response": f"Error processing request: {exc}"}
```

#### Step 3: Update Frontend (LiveTalking)

```python
# llm.py (updated)
import requests
import json

class LLM:
    def __init__(self, opt):
        self.url = opt.url
        self.language = "ur"  # Set to "ur" for Urdu, "en" for English
    
    def chat(self, prompt):
        try:
            response = requests.post(
                self.url,
                json={
                    "message": prompt,
                    "language": self.language
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            print(f"LLM error: {e}")
            return "معذرت، میں آپ کی مدد نہیں کر سکتا۔"  # "Sorry, I cannot help you."
```

---

## Alternative: Google Translate API

If you prefer dedicated translation API:

### Step 1: Install Google Translate

```bash
pip install google-cloud-translate
```

### Step 2: Create Translation Service

```python
# translation_service_google.py
from google.cloud import translate_v2 as translate

class GoogleTranslationService:
    def __init__(self):
        self.client = translate.Client()
    
    def translate_urdu_to_english(self, urdu_text: str) -> str:
        """Translate Urdu to English."""
        result = self.client.translate(
            urdu_text,
            source_language='ur',
            target_language='en'
        )
        return result['translatedText']
    
    def translate_english_to_urdu(self, english_text: str) -> str:
        """Translate English to Urdu."""
        result = self.client.translate(
            english_text,
            source_language='en',
            target_language='ur'
        )
        return result['translatedText']
```

---

## Urdu TTS Support

Edge TTS already supports Urdu voices!

### Available Urdu Voices:
- `ur-PK-AsadNeural` (Male, Pakistan)
- `ur-PK-UzmaNeural` (Female, Pakistan)
- `ur-IN-GulNeural` (Female, India)
- `ur-IN-SalmanNeural` (Male, India)

### Update TTS Configuration:

```python
# In start_project.sh or app.py
--REF_FILE ur-PK-UzmaNeural  # For Urdu female voice
# or
--REF_FILE ur-PK-AsadNeural  # For Urdu male voice
```

---

## Complete Implementation Example

### File Structure:
```
Tester/
├── main.py (RAG backend with translation)
├── translation_service.py (new)
├── requirements.txt (updated)
└── LiveTalking/
    ├── llm.py (updated with language param)
    └── app.py (updated with Urdu TTS)
```

### Updated requirements.txt:
```txt
# Existing dependencies
fastapi
uvicorn
langchain
langchain-google-genai
langchain-huggingface
langchain-qdrant
qdrant-client
python-dotenv

# Optional: For Google Translate API
# google-cloud-translate
```

---

## Testing the Translation Layer

### Test 1: Urdu Input
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "کیا آپ مجھے ورک ویزا کے بارے میں بتا سکتے ہیں؟", "language": "ur"}'
```

Expected flow:
1. Input: "کیا آپ مجھے ورک ویزا کے بارے میں بتا سکتے ہیں؟"
2. Translated: "Can you tell me about work visa?"
3. RAG processes in English
4. Response: "A work visa allows you to..."
5. Translated back: "ورک ویزا آپ کو اجازت دیتا ہے..."

### Test 2: English Input (backward compatibility)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is a work visa?", "language": "en"}'
```

---

## Performance Considerations

### Latency Impact:
- **Without Translation:** ~2-3 seconds
- **With Translation (Gemini):** ~4-6 seconds
  - Urdu→English: +1-1.5s
  - RAG: 2-3s
  - English→Urdu: +1-1.5s

### Optimization Strategies:

1. **Parallel Translation** (Advanced):
```python
import asyncio

async def translate_and_rag(urdu_text):
    # Translate to English
    english = await translator.translate_async(urdu_text)
    # Run RAG
    english_response = await rag_pipeline_async(english)
    # Translate back
    urdu_response = await translator.translate_async(english_response)
    return urdu_response
```

2. **Caching Common Translations**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def translate_cached(text, direction):
    return translator.translate(text, direction)
```

3. **Batch Translation** (for multiple queries):
```python
def translate_batch(texts, source, target):
    return translator.translate_batch(texts, source, target)
```

---

## Cost Analysis

### Gemini Translation (Recommended):
- **Free Tier:** 1,500 requests/day
- **Cost:** $0.00 for most use cases
- **Estimate:** 
  - 100 conversations/day = 200 translation calls
  - Well within free tier

### Google Translate API:
- **Free Tier:** 500,000 characters/month
- **Cost:** $20 per 1M characters after free tier
- **Estimate:**
  - Average query: 50 characters
  - Average response: 200 characters
  - 100 conversations/day = 25,000 chars/day = 750,000 chars/month
  - **Cost:** ~$15/month after free tier

---

## Multilingual Support (Future)

Easy to extend to other languages:

```python
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ur": "Urdu",
    "ar": "Arabic",
    "hi": "Hindi",
    "pa": "Punjabi",
}

class ChatRequest(BaseModel):
    message: str
    language: str = "en"  # Default to English
    
    @validator('language')
    def validate_language(cls, v):
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v
```

---

## Edge Cases to Handle

### 1. Mixed Language Input
```python
def detect_language(text):
    """Detect if text is Urdu or English."""
    # Simple heuristic: check for Urdu Unicode range
    urdu_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return "ur" if urdu_chars > len(text) * 0.3 else "en"
```

### 2. Technical Terms
```python
# Keep technical terms in English
TECHNICAL_TERMS = ["visa", "NIRA", "passport", "embassy"]

def preserve_technical_terms(text, terms):
    # Implementation to preserve specific terms during translation
    pass
```

### 3. Numbers and Dates
```python
# Ensure numbers remain consistent
def normalize_numbers(text):
    # Convert Urdu numerals to Arabic numerals
    urdu_to_arabic = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return text.translate(urdu_to_arabic)
```

---

## Deployment Considerations

### Docker Configuration:

Update `docker-compose.yml`:
```yaml
rag-backend:
  environment:
    - GEMINI_API_KEY=${GEMINI_API_KEY}
    - ENABLE_TRANSLATION=true
    - DEFAULT_LANGUAGE=ur
```

### Environment Variables:

Add to `.env`:
```env
# Translation settings
ENABLE_TRANSLATION=true
DEFAULT_LANGUAGE=ur
SUPPORTED_LANGUAGES=en,ur
```

---

## Monitoring and Logging

Add translation metrics:

```python
import time

class TranslationMetrics:
    def __init__(self):
        self.translation_times = []
        self.translation_count = 0
    
    def log_translation(self, duration, direction):
        self.translation_times.append(duration)
        self.translation_count += 1
        print(f"[Metrics] Translation {direction}: {duration:.2f}s")
        print(f"[Metrics] Avg translation time: {sum(self.translation_times)/len(self.translation_times):.2f}s")
```

---

## Recommendation Summary

### For Your Use Case (NIRA):

**Best Approach: Gemini-based Translation**

**Why:**
1. ✅ Already using Gemini API
2. ✅ No additional setup
3. ✅ Excellent Urdu quality
4. ✅ Cost-effective (free tier sufficient)
5. ✅ Context-aware translation
6. ✅ Easy to implement (< 100 lines of code)

**Implementation Time:** 2-3 hours

**Steps:**
1. Create `translation_service.py` (30 min)
2. Update `main.py` with translation layer (30 min)
3. Update `LiveTalking/llm.py` with language param (15 min)
4. Configure Urdu TTS voice (15 min)
5. Test and debug (1 hour)

---

## Next Steps

1. **Choose approach** (Recommend: Gemini)
2. **Implement translation service**
3. **Update RAG backend**
4. **Configure Urdu TTS**
5. **Test end-to-end flow**
6. **Deploy and monitor**

Would you like me to implement this for you?
