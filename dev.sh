#!/bin/bash

# Development script to run both backend and frontend
echo "Starting Voice Agent Development Environment"
echo "============================================"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please create it with your API keys."
    echo "   Copy .env.example to .env and fill in your credentials."
    exit 1
fi

# Start backend in background
echo "🚀 Starting FastAPI backend on http://localhost:8000"
python app.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "🎨 Starting Next.js frontend on http://localhost:3000"
cd voice-agent-ui
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Both services are running:"
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both services"

# Function to kill both processes on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
