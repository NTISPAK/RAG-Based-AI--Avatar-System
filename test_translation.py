"""Test script for Urdu translation functionality.

This script tests the translation layer by sending requests to the RAG backend
in both English and Urdu.
"""

import requests
import json
import time

# Configuration
RAG_BACKEND_URL = "http://localhost:8000"

def test_english_chat():
    """Test chat in English."""
    print("\n" + "="*60)
    print("TEST 1: English Chat")
    print("="*60)
    
    message = "What services does NIRA offer?"
    print(f"\nSending English message: {message}")
    
    start = time.time()
    response = requests.post(
        f"{RAG_BACKEND_URL}/chat",
        json={"message": message, "language": "en"},
        timeout=30
    )
    duration = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Response received in {duration:.2f}s")
        print(f"Language: {data.get('language')}")
        print(f"Processing time: {data.get('processing_time')}s")
        print(f"\nResponse:\n{data.get('response')}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)

def test_urdu_chat():
    """Test chat in Urdu."""
    print("\n" + "="*60)
    print("TEST 2: Urdu Chat")
    print("="*60)
    
    message = "NIRA کیا خدمات پیش کرتا ہے؟"  # "What services does NIRA offer?"
    print(f"\nSending Urdu message: {message}")
    
    start = time.time()
    response = requests.post(
        f"{RAG_BACKEND_URL}/chat",
        json={"message": message, "language": "ur"},
        timeout=30
    )
    duration = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Response received in {duration:.2f}s")
        print(f"Language: {data.get('language')}")
        print(f"Processing time: {data.get('processing_time')}s")
        print(f"\nResponse:\n{data.get('response')}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)

def test_direct_translation():
    """Test direct translation endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Direct Translation (English → Urdu)")
    print("="*60)
    
    text = "Hello, how can I help you today?"
    print(f"\nTranslating: {text}")
    
    response = requests.post(
        f"{RAG_BACKEND_URL}/translate",
        params={
            "text": text,
            "source_lang": "en",
            "target_lang": "ur"
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Translation successful")
        print(f"Original: {data.get('original')}")
        print(f"Translation: {data.get('translation')}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
    
    print("\n" + "="*60)
    print("TEST 4: Direct Translation (Urdu → English)")
    print("="*60)
    
    text = "آپ کا دن اچھا گزرے"  # "Have a good day"
    print(f"\nTranslating: {text}")
    
    response = requests.post(
        f"{RAG_BACKEND_URL}/translate",
        params={
            "text": text,
            "source_lang": "ur",
            "target_lang": "en"
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Translation successful")
        print(f"Original: {data.get('original')}")
        print(f"Translation: {data.get('translation')}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)

def test_health_check():
    """Test health endpoint with translation metrics."""
    print("\n" + "="*60)
    print("TEST 5: Health Check & Metrics")
    print("="*60)
    
    response = requests.get(f"{RAG_BACKEND_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Service Status: {data.get('status')}")
        print(f"Service: {data.get('service')}")
        print(f"Translation Enabled: {data.get('translation_enabled')}")
        print(f"Supported Languages: {data.get('supported_languages')}")
        
        if 'translation_metrics' in data:
            metrics = data['translation_metrics']
            print(f"\nTranslation Metrics:")
            print(f"  Total Translations: {metrics.get('total_translations')}")
            print(f"  Total Time: {metrics.get('total_time')}s")
            print(f"  Average Time: {metrics.get('average_time')}s")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)

def test_languages_endpoint():
    """Test languages endpoint."""
    print("\n" + "="*60)
    print("TEST 6: Languages Endpoint")
    print("="*60)
    
    response = requests.get(f"{RAG_BACKEND_URL}/languages")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Languages Configuration:")
        print(f"Supported Languages: {data.get('supported_languages')}")
        print(f"Default Language: {data.get('default_language')}")
        print(f"Translation Enabled: {data.get('translation_enabled')}")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("URDU TRANSLATION LAYER - TEST SUITE")
    print("="*60)
    print(f"\nTesting RAG Backend at: {RAG_BACKEND_URL}")
    
    # Check if backend is running
    try:
        response = requests.get(f"{RAG_BACKEND_URL}/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Backend is not responding correctly!")
            print("Please start the backend with: uvicorn main:app --reload")
            return
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to backend!")
        print("Please start the backend with: uvicorn main:app --reload")
        return
    
    # Run tests
    try:
        test_languages_endpoint()
        test_health_check()
        test_english_chat()
        test_urdu_chat()
        test_direct_translation()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        
        # Final metrics
        test_health_check()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
