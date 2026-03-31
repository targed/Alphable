#!/bin/bash
set -e

echo "Starting post-create setup..."

# Update pip
pip install --upgrade pip

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Install Node.js dependencies for Visualizer Frontend
if [ -d "visualizer/frontend" ]; then
    echo "Installing frontend dependencies..."
    cd visualizer/frontend
    npm install
    cd ../..
fi

# Build Cython extensions
if [ -f "setup.py" ]; then
    echo "Building Cython extensions..."
    python setup.py build_ext --inplace
fi

echo "Post-create setup complete!"
