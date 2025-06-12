#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    echo "GROQ_API_KEY=your_api_key_here" > .env
    echo "Please update the .env file with your actual Groq API key"
fi

echo "Setup complete! Don't forget to:"
echo "1. Update the .env file with your Groq API key"
echo "2. Activate the virtual environment: source .venv/bin/activate"
echo "3. Run the application: uvicorn app.main:app --reload" 