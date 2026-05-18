#!/bin/bash

# RPIStepper Setup Script for Raspberry Pi
# This script sets up the virtual environment and installs dependencies

set -e  # Exit on any error

echo "================================================"
echo "RPIStepper Setup Script"
echo "================================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please run: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
fi

echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate
echo "   ✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "📥 Upgrading pip..."
pip install --upgrade pip
echo "   ✓ pip upgraded"
echo ""

# Install requirements
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt
echo "   ✓ Dependencies installed"
echo ""

echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Edit config.py to match your HAT pinout"
echo ""
echo "3. Test the installation:"
echo "   python3 example.py basic"
echo ""
echo "4. To run on boot, follow instructions in README.md"
echo ""
