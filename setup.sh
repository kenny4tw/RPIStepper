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

# Install system-level GPIO library (cannot be built via pip without swig)
echo "📡 Installing system GPIO library..."
sudo apt-get install -y python3-lgpio
echo "   ✓ python3-lgpio installed"
echo ""

# Create virtual environment with access to system site-packages
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   Removing old venv to ensure --system-site-packages is set..."
    rm -rf venv
fi
python3 -m venv --system-site-packages venv
echo "   ✓ Virtual environment created (with system site-packages)"
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

# Install remaining requirements (rpi-lgpio only, lgpio comes from system)
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
