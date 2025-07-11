from flask import Flask, request, Response, render_template_string, jsonify
import requests
import psutil  # Library to get system usage
import time
import os

app = Flask(__name__)

# This template is now a full-fledged single-page application UI.
ADVANCED_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Streamer's Dashboard</title>
    <style>
        :root {
            --dark-bg: #1a1d24;
            --card-bg: #2c313a;
            --primary-color: #00aaff;
            --text-color: #e0e0e0;
            --text-muted: #888;
            --success-color: #28a745;
            --error-color: #dc3545;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--dark-bg);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
        }
        .dashboard {
            max-width: 800px;
            margin: 0 auto;
            display: grid;
            gap: 20px;
        }
        .card {
            background-color: var(--card-bg);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            border: 1px solid #3a4049;
        }
        h1, h2 {
            color: white;
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 10px;
            margin-top: 0;
        }
        .form-group { margin-bottom: 15px; }
        label {
            display: block;
            margin-bottom: 5px;
            color: var(--text-muted);
        }
        input[type="url"] {
            width: 100%;
            padding: 12px;
            background-color: #3a4049;
            border: 1px solid #555;
            border-radius: 6px;
            color: var(--text-color);
            box-sizing: border-box;
            font-size: 16px;
        }
        button {
            background-color: var(--primary-color);
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: background-color 0.3s ease;
        }
        button:hover { background-color: #0088cc; }
        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top: 4px solid var(--primary-color);
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: none; /* Hidden by default */
            margin-left: 15px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        #result-card, #info-card { display: none; }
        #result-link {
            padding: 10px;
            background: #3a4049;
            border-radius: 5px;
            word-wrap: break-word;
            margin-bottom: 10px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .info-item {
            background-color: #3a4049;
            padding: 10px;
            border-radius: 5px;
        }
        .info-item strong { color: var(--primary-color); }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .stat-item .label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .progress-bar {
            background-color: #3a4049;
            border-radius: 5px;
            overflow: hidden;
            height: 15px;
        }
        .progress-bar div {
            background-color: var(--primary-color);
            height: 100%;
            transition: width 0.5s ease-out;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="card">
            <h1>Streamer's Dashboard</h1>
            <div class="form-group">
                <label for="url-input">Video URL</label>
                <input type="url" id="url-input" placeholder="Paste direct video link here...">
            </div>
            <button id="generate-btn">Generate Link</button>
            <div class="spinner" id="spinner"></div>
        </div>

        <div class="card" id="info-card">
            <h2>URL Info</h2>
            <div id="info-content" class="info-grid"></div>
            <div id="info-error" style="color: var(--error-color);"></div>
        </div>

        <div class="card" id="result-card">
            <h2>Generated Proxy Link</h2>
            <div id="result-link"></div>
            <button id="copy-btn">Copy Link</button>
        </div>

        <div class="card">
            <h2>System Monitor</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="label"><span>CPU Usage</span><span id="cpu-percent">...</span></div>
                    <div class="progress-bar"><div id="cpu-bar" style="width: 0%;"></div></div>
                </div>
                <div class="stat-item">
                    <div class="label"><span>Memory Usage</span><span id="ram-percent">...</span></div>
                    <div class="progress-bar"><div id="ram-bar" style="width: 0%;"></div></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const generateBtn = document.getElementById('generate-btn');
        const urlInput = document.getElementById('url-input');
        const spinner = document.getElementById('spinner');

        const infoCard = document.getElementById('info-card');
        const infoContent = document.getElementById('info-content');
        const infoError = document.getElementById('info-error');

        const resultCard = document.getElementById('result-card');
        const resultLink = document.getElementById('result-link');
        const copyBtn = document.getElementById('copy-btn');
        
        // --- System Stats Monitoring ---
        const cpuPercent = document.getElementById('cpu-percent');
        const cpuBar = document.getElementById('cpu-bar');
        const ramPercent = document.getElementById('ram-percent');
        const ramBar = document.getElementById('ram-bar');

        async function updateStats() {
            try {
                const response = await fetch('/api/system-stats');
                const stats = await response.json();
                
                cpuPercent.textContent = `${stats.cpu_percent}%`;
                cpuBar.style.width = `${stats.cpu_percent}%`;
                
                ramPercent.textContent = `${stats.ram_percent}%`;
                ramBar.style.width = `${stats.ram_percent}%`;
            } catch (error) {
                console.error('Error fetching system stats:', error);
            }
        }
        // Update stats every 3 seconds
        setInterval(updateStats, 3000);
        updateStats(); // Initial call

        // --- Link Generation Logic ---
        generateBtn.addEventListener('click', async () => {
            const url = urlInput.value;
            if (!url) {
                alert('Please enter a URL.');
                return;
            }

            // Show spinner and reset previous results
            spinner.style.display = 'inline-block';
            generateBtn.disabled = true;
            infoCard.style.display = 'none';
            resultCard.style.display = 'none';
            infoError.textContent = '';
            infoContent.innerHTML = '';

            // 1. Fetch URL Info
            try {
                const infoResponse = await fetch(`/api/url-info?url=${encodeURIComponent(url)}`);
                const infoData = await infoResponse.json();
                infoCard.style.display = 'block';

                if (infoData.error) {
                    infoError.textContent = `Error: ${infoData.error}`;
                } else {
                    infoContent.innerHTML = `
                        <div class="info-item"><strong>Status:</strong> <span style="color: var(--success-color);">OK</span></div>
                        <div class="info-item"><strong>File Size:</strong> ${infoData.size_mb}</div>
                        <div class="info-item" style="grid-column: 1 / -1;"><strong>Content Type:</strong> ${infoData.content_type}</div>
                    `;
                    
                    // 2. If info is successful, generate and show the proxy link
                    const proxyUrl = `${window.location.origin}/proxy?url=${encodeURIComponent(url)}`;
                    resultLink.textContent = proxyUrl;
                    resultCard.style.display = 'block';
                }
            } catch (err) {
                infoCard.style.display = 'block';
                infoError.textContent = 'Failed to fetch URL info. The server might be down or the URL is invalid.';
            } finally {
                // Hide spinner
                spinner.style.display = 'none';
                generateBtn.disabled = false;
            }
        });

        // --- Copy to Clipboard ---
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(resultLink.textContent).then(() => {
                alert('Link copied to clipboard!');
            }).catch(err => {
                console.error('Failed to copy link: ', err);
            });
        });
    </script>
</body>
</html>
"""

# --- Backend API Endpoints ---

@app.route('/api/system-stats')
def system_stats():
    """Provides real-time CPU and RAM usage."""
    return jsonify({
        'cpu_percent': psutil.cpu_percent(interval=None),
        'ram_percent': psutil.virtual_memory().percent
    })

@app.route('/api/url-info')
def url_info():
    """Fetches headers of a target URL to get its info without downloading it."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is missing.'}), 400
    
    try:
        # Use a HEAD request to be efficient
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.head(url, timeout=5, allow_redirects=True, headers=headers)
        res.raise_for_status() # Raise an exception for bad status codes

        content_type = res.headers.get('content-type', 'N/A')
        content_length = res.headers.get('content-length')

        if content_length:
            size_mb = f"{int(content_length) / (1024 * 1024):.2f} MB"
        else:
            size_mb = "Unknown (not specified by server)"
            
        return jsonify({
            'content_type': content_type,
            'size_mb': size_mb
        })

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Could not reach URL. {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


# --- Main Application Routes ---

@app.route('/')
def home():
    """Renders the main dashboard UI."""
    return render_template_string(ADVANCED_UI_TEMPLATE)

@app.route('/proxy')
def proxy():
    """The core streaming proxy endpoint. Logs performance to the console."""
    # (This proxy logic is from the previous step and works great)
    video_url = request.args.get('url')
    if not video_url:
        return "Error: 'url' parameter is missing.", 400

    try:
        req = requests.get(video_url, stream=True)
        req.raise_for_status()
        
        # Generator for streaming with console logging
        def stream_with_stats(req):
            print(f"[LOG] Starting stream for: {req.url}")
            for chunk in req.iter_content(chunk_size=1024*1024): # 1MB chunks
                yield chunk
            print(f"[LOG] Stream finished for: {req.url}")

        return Response(stream_with_stats(req), content_type=req.headers['content-type'])

    except Exception as e:
        print(f"[ERROR] Proxy failed for URL {video_url}. Reason: {e}")
        return f"Proxy error: {e}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
