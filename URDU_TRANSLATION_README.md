# Urdu Translation Layer - Quick Start Guide

## Overview

Your AI Avatar System now supports **bidirectional Urdu-English translation**! Users can interact with the avatar in Urdu, and the avatar will respond in Urdu with proper Urdu TTS voice.

## How It Works

```
User Input (Urdu) → Translate to English → RAG Pipeline → Translate to Urdu → Avatar Response (Urdu)
```

## Quick Start

### 1. Enable Urdu Mode

Edit your `.env` file:

```env
# Enable translation
ENABLE_TRANSLATION=true

# Set default language to Urdu
DEFAULT_LANGUAGE=ur

# For LiveTalking frontend
CHAT_LANGUAGE=ur
```

### 2. Configure Urdu TTS Voice

For Urdu speech output, update your LiveTalking startup:

```bash
# Female Urdu voice (Pakistan)
python app.py --REF_FILE ur-PK-UzmaNeural

# Male Urdu voice (Pakistan)
python app.py --REF_FILE ur-PK-AsadNeural
```

Or in `docker-compose.yml`:

```yaml
livetalking:
  environment:
    - REF_FILE=ur-PK-UzmaNeural  # Urdu female voice
    - CHAT_LANGUAGE=ur            # Urdu language
```

### 3. Start the System

```bash
# Start all services
docker-compose up -d

# Or manually
uvicorn main:app --reload  # Backend
cd LiveTalking && python app.py --REF_FILE ur-PK-UzmaNeural  # Frontend
```

### 4. Test Translation

```bash
# Run test suite
python test_translation.py
```

## Available Urdu TTS Voices

| Voice | Gender | Region | Code |
|-------|--------|--------|------|
| Uzma | Female | Pakistan | `ur-PK-UzmaNeural` |
| Asad | Male | Pakistan | `ur-PK-AsadNeural` |
| Gul | Female | India | `ur-IN-GulNeural` |
| Salman | Male | India | `ur-IN-SalmanNeural` |

## API Usage

### Chat Endpoint

**English:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What services does NIRA offer?", "language": "en"}'
```

**Urdu:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "NIRA کیا خدمات پیش کرتا ہے؟", "language": "ur"}'
```

**Response:**
```json
{
  "response": "نعمان انٹرنیشنل ریکروٹمنٹ ایجنسی...",
  "language": "ur",
  "processing_time": 5.2
}
```

### Direct Translation Endpoint

```bash
# English to Urdu
curl -X POST "http://localhost:8000/translate?text=Hello&source_lang=en&target_lang=ur"

# Urdu to English
curl -X POST "http://localhost:8000/translate?text=ہیلو&source_lang=ur&target_lang=en"
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TRANSLATION` | `true` | Enable/disable translation |
| `DEFAULT_LANGUAGE` | `en` | Default language for API |
| `SUPPORTED_LANGUAGES` | `en,ur` | Comma-separated language codes |
| `CHAT_LANGUAGE` | `en` | Language for LiveTalking frontend |

### Language Codes

- `en` - English
- `ur` - Urdu (اردو)

## Performance

### Expected Latency

| Operation | Time |
|-----------|------|
| English-only | 2-3 seconds |
| With Urdu translation | 4-6 seconds |
| - Urdu→English | +1-1.5s |
| - RAG processing | 2-3s |
| - English→Urdu | +1-1.5s |

### Optimization Tips

1. **Use faster model** (already using gemini-2.5-flash)
2. **Reduce RAG retrieval** (k=4 is optimal)
3. **Enable caching** for common queries
4. **Use GPU** for faster processing

## Switching Between Languages

### For Testing/Development

**English Mode:**
```bash
# In .env
CHAT_LANGUAGE=en
REF_FILE=en-US-JennyNeural
```

**Urdu Mode:**
```bash
# In .env
CHAT_LANGUAGE=ur
REF_FILE=ur-PK-UzmaNeural
```

### For Production

Set up language selection in your frontend UI to allow users to choose their preferred language.

## Monitoring

### Check Translation Metrics

```bash
curl http://localhost:8000/health
```

Response includes:
```json
{
  "status": "ok",
  "translation_enabled": true,
  "supported_languages": ["en", "ur"],
  "translation_metrics": {
    "total_translations": 42,
    "total_time": 63.5,
    "average_time": 1.51
  }
}
```

### Check Supported Languages

```bash
curl http://localhost:8000/languages
```

## Troubleshooting

### Issue: Translation not working

**Check:**
1. `ENABLE_TRANSLATION=true` in `.env`
2. `GOOGLE_API_KEY` is set correctly
3. Backend logs show "Translation enabled"

```bash
# Check logs
docker-compose logs rag-backend | grep Translation
```

### Issue: Urdu text not displaying

**Solution:** Ensure your terminal/browser supports Urdu Unicode (U+0600 to U+06FF)

### Issue: TTS not speaking Urdu

**Check:**
1. `REF_FILE` is set to Urdu voice (e.g., `ur-PK-UzmaNeural`)
2. Edge TTS is working: `edge-tts --list-voices | grep ur-PK`

### Issue: Slow response time

**Solutions:**
1. Reduce batch size: `BATCH_SIZE=1`
2. Use GPU if available
3. Check network latency to Gemini API

## Docker Deployment

### With Urdu Support

```yaml
# docker-compose.yml
services:
  rag-backend:
    environment:
      - ENABLE_TRANSLATION=true
      - DEFAULT_LANGUAGE=ur
      - SUPPORTED_LANGUAGES=en,ur
  
  livetalking:
    environment:
      - CHAT_LANGUAGE=ur
      - REF_FILE=ur-PK-UzmaNeural
```

Start:
```bash
docker-compose up -d
```

## Testing

### Run Full Test Suite

```bash
python test_translation.py
```

Tests include:
- ✅ English chat
- ✅ Urdu chat
- ✅ Direct translation (both directions)
- ✅ Health check with metrics
- ✅ Languages endpoint

### Manual Testing

1. **Test English:**
   - Message: "What is a work visa?"
   - Expected: English response

2. **Test Urdu:**
   - Message: "ورک ویزا کیا ہے؟"
   - Expected: Urdu response

3. **Test Translation:**
   - Verify Urdu input is translated to English
   - Verify English response is translated to Urdu
   - Check logs for translation steps

## Cost Estimation

### Gemini API Usage

**Free Tier:**
- 1,500 requests/day
- Sufficient for most use cases

**Translation Cost:**
- 2 translations per conversation (input + output)
- 100 conversations/day = 200 translations
- Well within free tier ✅

**Estimated Monthly Cost:** $0 (free tier)

## Adding More Languages

To add support for other languages (e.g., Arabic, Hindi):

1. **Update environment:**
```env
SUPPORTED_LANGUAGES=en,ur,ar,hi
```

2. **Update translation service:**
```python
# translation_service.py
def translate_to_language(self, text: str, target_lang: str) -> str:
    # Add language-specific prompts
    pass
```

3. **Add TTS voices:**
```bash
# Check available voices
edge-tts --list-voices | grep ar-  # Arabic
edge-tts --list-voices | grep hi-  # Hindi
```

## Best Practices

1. **Always test** both English and Urdu modes
2. **Monitor metrics** via `/health` endpoint
3. **Use appropriate TTS voice** for the language
4. **Handle errors gracefully** with fallback to original language
5. **Log translation steps** for debugging

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Test translation: `python test_translation.py`
- Review guide: `URDU_TRANSLATION_IMPLEMENTATION_GUIDE.md`

## Summary

✅ **Translation enabled** with Gemini API  
✅ **Urdu TTS voices** available via Edge TTS  
✅ **Docker support** with environment variables  
✅ **Testing tools** included  
✅ **Production ready** with monitoring  

Your AI Avatar now speaks Urdu! 🎉
