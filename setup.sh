#!/bin/bash

# CSRD Extraction System - Quick Setup Script

echo "================================================"
echo "CSRD AI Data Extraction System - Quick Setup"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OpenAI API key"
fi

# Initialize system
echo ""
echo "Initializing system..."
python main.py init

echo ""
echo "================================================"
echo "✓ Setup completed successfully!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OpenAI API key:"
echo "   OPENAI_API_KEY=your_actual_key_here"
echo ""
echo "2. Download CSRD reports and place them in data/reports/"
echo "   - AIB: https://www.aib.ie"
echo "   - BBVA: https://shareholdersandinvestors.bbva.com"
echo "   - BPCE: https://www.groupebpce.com"
echo ""
echo "3. Process reports:"
echo "   python main.py process-all"
echo ""
echo "4. Export results:"
echo "   python main.py export-csv"
echo ""
echo "For help: python main.py --help"
echo ""
