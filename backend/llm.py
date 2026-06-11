import time
import os
import re
import requests
from basereal import BaseReal
from logger import logger

# RAG Backend URL - modify this if your backend is on a different host/port
RAG_BACKEND_URL = os.getenv("RAG_BACKEND_URL", "http://127.0.0.1:8000")

# Language setting - set to 'ur' for Urdu, 'en' for English
CHAT_LANGUAGE = os.getenv("CHAT_LANGUAGE", "en")

def get_rag_answer(message):
    """
    Call the RAG backend and return the full answer text.
    Returns (answer_text, error_msg). error_msg is None on success.
    """
    try:
        response = requests.post(
            f"{RAG_BACKEND_URL}/chat",
            json={"message": message, "language": CHAT_LANGUAGE},
            timeout=180
        )
        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "")
            if answer:
                logger.info(f"RAG answer length: {len(answer)} chars")
                return answer, None
            return None, "Empty response from RAG backend"
        return None, f"RAG backend error: {response.status_code}"
    except requests.exceptions.Timeout:
        return None, "RAG backend request timed out"
    except requests.exceptions.ConnectionError:
        return None, f"Could not connect to RAG backend at {RAG_BACKEND_URL}"
    except Exception as e:
        return None, f"Error calling RAG backend: {e}"


def llm_response(message, nerfreal: BaseReal):
    """
    Call the RAG backend API and stream the response to the digital human.
    Modified to use NTIS Policy RAG backend instead of OpenAI/Qwen.
    """
    start = time.perf_counter()

    answer, error = get_rag_answer(message)
    end = time.perf_counter()
    logger.info(f"RAG backend response time: {end-start}s")

    if error:
        logger.error(error)
        fallback = (
            "معذرت، میں جواب تیار نہیں کر سکی۔ براہ کرم دوبارہ کوشش کریں۔"
            if CHAT_LANGUAGE == "ur" else
            "I apologize, but I couldn't generate a response."
        )
        nerfreal.put_msg_txt(fallback)
        return

    if not answer:
        fallback = (
            "معذرت، میں جواب تیار نہیں کر سکی۔ براہ کرم دوبارہ کوشش کریں۔"
            if CHAT_LANGUAGE == "ur" else
            "I apologize, but I couldn't generate a response."
        )
        nerfreal.put_msg_txt(fallback)
        return

    # Split at sentence boundaries for high-quality TTS output.
    sentences = re.split(r'(?<=[.!?۔])\s+', answer.strip())

    # Merge very short sentences together for smoother speech
    chunks = []
    buf = ""
    for s in sentences:
        if buf and len(buf) + len(s) > 200:
            chunks.append(buf.strip())
            buf = s
        else:
            buf = (buf + " " + s).strip() if buf else s
    if buf.strip():
        chunks.append(buf.strip())

    for chunk in chunks:
        if not chunk:
            continue
        logger.info(f"Sending chunk ({len(chunk)} chars): {chunk[:80]}")
        nerfreal.put_msg_txt(chunk)    