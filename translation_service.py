"""Translation Service for Urdu ↔ English translation using Google Gemini.

This service provides bidirectional translation between Urdu and English
for the RAG chatbot system.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
import time
from typing import Optional


class TranslationService:
    """Translation service using Google Gemini for Urdu-English translation."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """Initialize the translation service.
        
        Args:
            api_key: Google API key for Gemini
            model: Gemini model to use (default: gemini-2.5-flash)
        """
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=0.3,  # Lower temperature for consistent translation
            google_api_key=api_key,
        )
        self.translation_count = 0
        self.total_translation_time = 0.0
    
    def translate_urdu_to_english(self, urdu_text: str) -> str:
        """Translate Urdu text to English.
        
        Args:
            urdu_text: Text in Urdu to translate
            
        Returns:
            Translated English text
        """
        start_time = time.time()
        
        prompt = f"""Translate the following Urdu text to English. 
Provide ONLY the translation, no explanations or additional text.
Keep the meaning and tone natural and conversational.

Urdu text: {urdu_text}

English translation:"""
        
        try:
            response = self.llm.invoke(prompt)
            translation = response.content.strip()
            
            # Log metrics
            duration = time.time() - start_time
            self.translation_count += 1
            self.total_translation_time += duration
            
            print(f"[Translation] Urdu→English: {duration:.2f}s")
            print(f"[Translation] Input: {urdu_text[:100]}...")
            print(f"[Translation] Output: {translation[:100]}...")
            
            return translation
            
        except Exception as e:
            print(f"[Translation Error] Urdu→English failed: {e}")
            # Return original text if translation fails
            return urdu_text
    
    def translate_english_to_urdu(self, english_text: str) -> str:
        """Translate English text to Urdu.
        
        Args:
            english_text: Text in English to translate
            
        Returns:
            Translated Urdu text
        """
        start_time = time.time()
        
        prompt = f"""Translate the following English text to Urdu.
Use natural, conversational Urdu that sounds good when spoken aloud.
Provide ONLY the translation, no explanations or additional text.
Use proper Urdu script (not Roman Urdu).

English text: {english_text}

Urdu translation:"""
        
        try:
            response = self.llm.invoke(prompt)
            translation = response.content.strip()
            
            # Log metrics
            duration = time.time() - start_time
            self.translation_count += 1
            self.total_translation_time += duration
            
            print(f"[Translation] English→Urdu: {duration:.2f}s")
            print(f"[Translation] Input: {english_text[:100]}...")
            print(f"[Translation] Output: {translation[:100]}...")
            
            return translation
            
        except Exception as e:
            print(f"[Translation Error] English→Urdu failed: {e}")
            # Return original text if translation fails
            return english_text
    
    def detect_language(self, text: str) -> str:
        """Detect if text is primarily Urdu or English.
        
        Args:
            text: Text to analyze
            
        Returns:
            'ur' for Urdu, 'en' for English
        """
        # Simple heuristic: check for Urdu Unicode range (U+0600 to U+06FF)
        urdu_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            return 'en'
        
        urdu_ratio = urdu_chars / total_chars
        
        # If more than 30% of characters are Urdu, consider it Urdu text
        return 'ur' if urdu_ratio > 0.3 else 'en'
    
    def get_metrics(self) -> dict:
        """Get translation service metrics.
        
        Returns:
            Dictionary with translation metrics
        """
        avg_time = (self.total_translation_time / self.translation_count 
                   if self.translation_count > 0 else 0)
        
        return {
            'total_translations': self.translation_count,
            'total_time': round(self.total_translation_time, 2),
            'average_time': round(avg_time, 2)
        }
    
    def reset_metrics(self):
        """Reset translation metrics."""
        self.translation_count = 0
        self.total_translation_time = 0.0


# Singleton instance (optional, for convenience)
_translator_instance: Optional[TranslationService] = None


def get_translator(api_key: str) -> TranslationService:
    """Get or create the global translator instance.
    
    Args:
        api_key: Google API key for Gemini
        
    Returns:
        TranslationService instance
    """
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = TranslationService(api_key)
    return _translator_instance
