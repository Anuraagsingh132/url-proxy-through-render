#!/bin/bash

echo "[1/5] Installing Python dependencies..."
pip install flask flask-ngrok psutil requests

echo "[2/5] Starting Flask app in background..."
nohup python3 app.py > flask.log 2>&1 &
sleep 2

echo "[3/5] Downloading Cloudflared (HTTP/2 tunnel tool)..."
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

echo "[4/5] Installing Cloudflared..."
sudo dpkg -i cloudflared-linux-amd64.deb

echo "[5/5] Launching tunnel over HTTP/2..."
cloudflared tunnel --url http://localhost:5001 --protocol http2
