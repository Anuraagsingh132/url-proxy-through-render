#!/bin/bash

echo "[1/6] Installing Python dependencies..."
pip install flask flask-ngrok psutil requests

echo "[2/6] Downloading ngrok v3..."
wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz

echo "[3/6] Extracting ngrok..."
tar -xvzf ngrok-v3-stable-linux-amd64.tgz
chmod +x ngrok

echo "[4/6] Configuring ngrok authtoken..."
./ngrok config add-authtoken 2zv9iW0LAHsUktJJ2u6TC8am6zE_4GdigGStqxk7RwqSX7yHQ

echo "[5/6] Starting Flask app in background..."
nohup python3 app.py > flask.log 2>&1 &
sleep 2

echo "[6/6] Starting ngrok tunnel on port 5001..."
./ngrok http 5001
