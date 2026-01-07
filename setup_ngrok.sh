#!/bin/bash

# Setup script for ngrok tunneling
# This script helps you set up ngrok for local development

echo "Voice Agent - ngrok Setup"
echo "========================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "ngrok is not installed. Please install it from https://ngrok.com/download"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please edit .env with your API keys and ngrok URL"
    else
        echo ".env.example not found. Please create your .env file manually."
        exit 1
    fi
fi

echo "Starting ngrok tunnel on port 8000..."
echo "Once ngrok starts, copy the HTTPS URL and update PUBLIC_HOST in your .env file"
echo ""
echo "Example:"
echo "PUBLIC_HOST=abc123.ngrok.io"
echo ""
echo "Then start your FastAPI server:"
echo "python app.py"
echo ""

# Start ngrok
ngrok http 8000
