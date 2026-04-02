import time
import os
import re
import requests
from basereal import BaseReal
from logger import logger

# RAG Backend URL - modify this if your backend is on a different host/port
RAG_BACKEND_URL = os.getenv("RAG_BACKEND_URL", "http://127.0.0.1:8000")

def llm_response(message, nerfreal: BaseReal):
    """
    Call the RAG backend API and stream the response to the digital human.
    Modified to use NTIS Policy RAG backend instead of OpenAI/Qwen.
    """
    start = time.perf_counter()
    
    try:
        # Call the RAG backend
        response = requests.post(
            f"{RAG_BACKEND_URL}/chat",
            json={"message": message},
            timeout=30
        )
        
        end = time.perf_counter()
        logger.info(f"RAG backend response time: {end-start}s")
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "")
            
            if not answer:
                logger.warning("Empty response from RAG backend")
                nerfreal.put_msg_txt("I apologize, but I couldn't generate a response.")
                return
            
            logger.info(f"RAG answer length: {len(answer)} chars")
            
            # Split at sentence boundaries for high-quality TTS output.
            # Larger chunks produce better intonation and prosody from edge_tts.
            sentences = re.split(r'(?<=[.!?])\s+', answer.strip())
            
            # Merge very short sentences together (< 40 chars) for smoother speech
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
        else:
            logger.error(f"RAG backend error: {response.status_code} - {response.text}")
            nerfreal.put_msg_txt("I apologize, but I encountered an error processing your request.")
            
    except requests.exceptions.Timeout:
        logger.error("RAG backend request timed out")
        nerfreal.put_msg_txt("I apologize, but the request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        logger.error(f"Could not connect to RAG backend at {RAG_BACKEND_URL}")
        nerfreal.put_msg_txt("I apologize, but I cannot connect to the backend service.")
    except Exception as e:
        logger.exception(f"Error calling RAG backend: {e}")
        nerfreal.put_msg_txt("I apologize, but an unexpected error occurred.")    