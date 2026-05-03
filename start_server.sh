#!/bin/bash

# Load environment variables and start Django server

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env file with your GROQ_API_KEY"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if GROQ_API_KEY is set
if [ -z "$GROQ_API_KEY" ] || [ "$GROQ_API_KEY" = "your-groq-api-key-here" ]; then
    echo "Error: GROQ_API_KEY not set in .env file!"
    echo "Please edit .env file and add your actual Groq API key"
    exit 1
fi

echo "✅ Environment variables loaded"
echo "✅ GROQ_API_KEY is configured"
echo "🚀 Starting Django development server..."

# Activate virtual environment and start server
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000