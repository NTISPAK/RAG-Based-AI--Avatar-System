#!/bin/bash
# Start script for NTIS Policy RAG with LiveTalking Frontend

echo "=== NTIS Policy RAG + LiveTalking Startup Script ==="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check if Qdrant is running
if ! curl -s http://localhost:6333 > /dev/null 2>&1; then
    echo "❌ ERROR: Qdrant is not running on localhost:6333"
    echo "Please start Qdrant first"
    exit 1
fi
echo "✅ Qdrant is running"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found"
    echo "Please create .env with GOOGLE_API_KEY"
    exit 1
fi
echo "✅ .env file exists"

# Check if models exist
if [ ! -f "LiveTalking/models/wav2lip.pth" ]; then
    echo "❌ ERROR: wav2lip.pth not found in LiveTalking/models/"
    echo "Please download the model first"
    exit 1
fi
echo "✅ wav2lip.pth found"

if [ ! -d "LiveTalking/data/avatars/wav2lip256_avatar1" ]; then
    echo "❌ ERROR: Avatar files not found"
    echo "Please extract wav2lip256_avatar1 to LiveTalking/data/avatars/"
    exit 1
fi
echo "✅ Avatar files found"

echo ""
echo "All prerequisites met!"
echo ""
echo "Starting servers..."
echo ""

# Start RAG Backend
echo "Starting RAG Backend on http://127.0.0.1:8000..."
cd /Users/naumanrashid/Desktop/Tester
source .venv/bin/activate
python -m uvicorn main:app --reload &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 5

# Start LiveTalking Frontend
echo ""
echo "Starting LiveTalking Frontend on http://localhost:8010..."
cd /Users/naumanrashid/Desktop/Tester/LiveTalking
source livetalking_env/bin/activate
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 --REF_FILE en-US-JennyNeural --batch_size 4 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "=== Servers Started ==="
echo "RAG Backend: http://127.0.0.1:8000 (PID: $BACKEND_PID)"
echo "LiveTalking: http://localhost:8010 (PID: $FRONTEND_PID)"
echo ""
echo "Open: http://localhost:8010/webrtcapi.html"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt
wait
