#!/bin/bash

echo "🧪 Testing Alphable Replay Visualizer Components"
echo ""

# Test 1: Check if game_logger.py works
echo "📝 Test 1: Testing game_logger.py..."
python3 -c "
from game_logger import GameLogger
import json

# Create a test game
logger = GameLogger('Player A', 'Player B')
logger.set_metadata(test=True)
logger.log_move(0, 0, 'PLAY', 42, 'HELLO', (7, 7), 'Across', 24, 
                rack_before=['H','E','L','L','O','X','Y'],
                rack_after=['X','Y','A','B','C','D','E'],
                tiles_in_bag=94)
logger.set_final_score([100, 95])

# Save test file
logger.save_json('data/results/test_game.json')

# Verify
with open('data/results/test_game.json', 'r') as f:
    data = json.load(f)
    print(f'✅ Game logger works! Created game with {len(data[\"turns\"])} turn(s)')
" && echo "" || echo "❌ Game logger test failed"

# Test 2: Check if backend dependencies are available
echo "🔧 Test 2: Checking backend dependencies..."
python3 -c "
import flask
import flask_cors
print('✅ Flask and flask-cors are installed')
" 2>/dev/null || echo "⚠️  Backend dependencies not installed. Run: cd visualizer/backend && pip install -r requirements.txt"
echo ""

# Test 3: Check if backend can start
echo "🌐 Test 3: Testing backend API..."
cd visualizer/backend
python3 -c "
import sys
sys.path.insert(0, '.')
from app import app
print('✅ Backend app can be imported successfully')
" 2>/dev/null || echo "⚠️  Backend import failed"
cd ../..
echo ""

# Test 4: Check if frontend structure is valid
echo "🎨 Test 4: Checking frontend structure..."
if [ -f "visualizer/frontend/package.json" ] && \
   [ -f "visualizer/frontend/src/App.tsx" ] && \
   [ -f "visualizer/frontend/src/components/Board.tsx" ]; then
    echo "✅ Frontend files are in place"
else
    echo "❌ Some frontend files are missing"
fi
echo ""

# Test 5: Count available JSON games
echo "🎮 Test 5: Scanning for game files..."
GAME_COUNT=$(find data/vs_greedy data/vs_random data/results -name "*.json" 2>/dev/null | wc -l)
echo "Found $GAME_COUNT game replay file(s)"
if [ $GAME_COUNT -gt 0 ]; then
    echo "✅ Game files available for viewing"
else
    echo "⚠️  No game files found. Run evaluation scripts to generate games:"
    echo "   python evaluate_vs_greedy.py"
    echo "   python evaluate_vs_random.py"
    echo "   python watch_bot.py"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Ready to start visualizer?"
echo ""
echo "1. Install dependencies (if not done):"
echo "   cd visualizer/backend && pip install -r requirements.txt"
echo "   cd visualizer/frontend && npm install"
echo ""
echo "2. Start the visualizer:"
echo "   ./start_visualizer.sh"
echo ""
echo "   OR manually:"
echo "   Terminal 1: cd visualizer/backend && python app.py"
echo "   Terminal 2: cd visualizer/frontend && npm start"
echo ""
