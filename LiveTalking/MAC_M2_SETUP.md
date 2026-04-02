# LiveTalking Setup for Mac M2 (Apple Silicon)

## ⚠️ Important Limitations

**LiveTalking is designed for NVIDIA GPUs and will NOT work optimally on Mac M2:**

1. **No GPU Acceleration**: Mac M2 uses Apple Silicon (Metal), not NVIDIA CUDA
2. **Performance Issues**: The digital human models (wav2lip, musetalk) require GPU inference
3. **CPU-only Mode**: Will be extremely slow and likely unusable for real-time video

## What Was Installed

✅ Dependencies installed successfully in virtual environment:
- Location: `/Users/naumanrashid/Desktop/Tester/LiveTalking/livetalking_env/`
- PyTorch (CPU version for Mac)
- All LiveTalking requirements
- Requests library for RAG backend integration

## Alternative Approach for Mac M2

Since LiveTalking requires GPU, I recommend **keeping your current setup** instead:

### Current Working Setup (Recommended for Mac)
Your existing frontend with lipsync-engine works well on Mac M2:
- ✅ Browser-based (no GPU needed)
- ✅ Real-time lip sync with SVG rendering
- ✅ Audio playback via gTTS
- ✅ RAG backend integration working

**To use your current setup:**
```bash
# Terminal 1: Start RAG backend
cd /Users/naumanrashid/Desktop/Tester
source .venv/bin/activate
python -m uvicorn main:app --reload

# Terminal 2: Start frontend
cd /Users/naumanrashid/Desktop/Tester/frontend
npm run dev
```

Access at: http://localhost:5173

## If You Still Want to Try LiveTalking

You'll need to:

1. **Download Models** (large files, ~2GB+):
   - wav2lip.pth from: https://pan.quark.cn/s/83a750323ef0
   - Avatar files: wav2lip256_avatar1.tar.gz
   - Place in `LiveTalking/models/` and `LiveTalking/data/avatars/`

2. **Run LiveTalking** (will be VERY slow on CPU):
   ```bash
   cd /Users/naumanrashid/Desktop/Tester/LiveTalking
   source livetalking_env/bin/activate
   python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
   ```

3. **Expected Issues**:
   - Extremely slow inference (minutes per frame instead of real-time)
   - High CPU usage
   - Likely crashes or timeouts
   - Not suitable for interactive use

## Recommendation

**For Mac M2 users**: Use the existing lipsync-engine frontend (already working)

**For LiveTalking**: Deploy on a cloud GPU instance (AWS, Google Cloud, etc.) or a machine with NVIDIA GPU

The RAG backend integration is ready in `LiveTalking/llm.py` and will work when you have proper GPU hardware.

## What's Already Working

Your current system has:
- ✅ RAG backend with Qdrant + Gemini
- ✅ Frontend with Ready Player Me avatar
- ✅ Lip sync via lipsync-engine
- ✅ Text-to-speech via gTTS
- ✅ Voice input via Web Speech API

This is a complete, working solution for Mac M2!
