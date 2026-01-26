#!/bin/bash

echo "Starting Alphable Replay Visualizer..."
echo ""

# Check if backend dependencies are installed
if [ ! -d "visualizer/backend/venv" ]; then
    echo "Setting up Python virtual environment..."
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Check if frontend dependencies are installed
if [ ! -d "visualizer/frontend/node_modules" ]; then
    echo "Installing Node.js dependencies..."
    cd visualizer/frontend
    npm install
    cd ../..
fi

# Start backend in background
echo "🔧 Starting Flask backend..."
cd visualizer/backend
# source venv/bin/activate
python app.py &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting React frontend..."
cd visualizer/frontend
npm start

# Cleanup on exit
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID; exit" INT TERM

wait
