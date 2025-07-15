from flask import Flask, request, Response, render_template_string, jsonify
import requests
import psutil
import time
import json
import threading

app = Flask(__name__)

# --- Global Data Store for Live Stream Stats ---
# This dictionary will hold the status of active streams.
# We use a lock to make it thread-safe, which is good practice.
STREAM_STATUS = {}
status_lock = threading.Lock()

# --- The Advanced UI Template ---
# This HTML, CSS, and JavaScript is now a full-fledged dashboard.
ADVANCED_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Stream Dashboard</title>
    <style>
        :root {
            --bg-dark: #121417;
            --bg-card: #1c1f24;
            --bg-input: #2d3138;
            --border-color: #363b44;
            --primary: #00aaff;
            --primary-light: #66d9ff;
            --text-light: #f1f1f1;
            --text-muted: #8c96a5;
            --success: #28a745;
            --error: #e53935;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background-color: var(--bg-dark);
            color: var(--text-light);
            margin: 0;
            padding: 24px;
        }
        .dashboard {
            max-width: 850px;
            margin: auto;
            display: grid;
            gap: 24px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }
        h1, h2 {
            margin-top: 0;
            color: white;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
        }
        h1 { font-size: 2.2em; text-align: center; border: none; }
        .icon-title { display: flex; align-items: center; gap: 12px; }
        .icon-title svg { width: 24px; height: 24px; stroke: var(--primary); }
        input[type="url"] {
            width: 100%;
            padding: 14px;
            font-size: 1em;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            color: var(--text-light);
            border-radius: 8px;
            box-sizing: border-box;
        }
        button {
            background: var(--primary);
            color: white;
            padding: 14px 22px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        button:hover { filter: brightness(1.2); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .stat-item .label { display: flex; justify-content: space-between; margin-bottom: 8px; color: var(--text-muted); }
        .progress-bar { background-color: var(--bg-input); border-radius: 5px; height: 10px; overflow: hidden; }
        .progress-bar div { background-color: var(--primary); height: 100%; width: 0; transition: width 0.4s ease-out; }
        .hidden { display: none; }
        #stream-status-card {
            border-left: 4px solid var(--primary);
        }
        .stream-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
        .stream-stat { background: var(--bg-input); padding: 16px; border-radius: 8px; text-align: center; }
        .stream-stat .value { font-size: 1.5em; color: white; font-weight: 600; }
        .stream-stat .label { font-size: 0.9em; color: var(--text-muted); margin-top: 5px; }
        #result-link { padding: 12px; background: var(--bg-input); border-radius: 8px; word-wrap: break-word; user-select: all; }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="card">
            <h1>Nexus Stream Dashboard</h1>
            <input type="url" id="url-input" placeholder="Paste direct video link here...">
            <button id="generate-btn" style="width: 100%; margin-top: 16px;">Generate Proxy Link</button>
        </div>

        <div class="card hidden" id="stream-status-card">
            <h2 class="icon-title">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>
                Live Stream Status
            </h2>
            <div class="stream-grid">
                <div class="stream-stat"><div id="bandwidth-value" class="value">--</div><div class="label">Bandwidth</div></div>
                <div class="stream-stat"><div id="downloaded-value" class="value">--</div><div class="label">Downloaded</div></div>
                <div class="stream-stat"><div id="total-size-value" class="value">--</div><div class="label">Total Size</div></div>
            </div>
            <div class="stat-item" style="margin-top: 20px;">
                <div class="label"><span>Progress</span><span id="progress-percent">0%</span></div>
                <div class="progress-bar"><div id="progress-bar-inner"></div></div>
            </div>
        </div>

        <div class="card hidden" id="result-card">
            <h2 class="icon-title">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" /></svg>
                Generated Link
            </h2>
            <div id="result-link"></div>
            <button id="copy-btn" style="width: 100%; margin-top: 16px;">Copy to Clipboard</button>
        </div>

        <div class="card">
            <h2 class="icon-title">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V7.5a2.25 2.25 0 00-2.25-2.25H7.5A2.25 2.25 0 005.25 7.5v9.75a2.25 2.25 0 002.25 2.25z" /></svg>
                Server Monitor
            </h2>
            <div class="grid">
                <div class="stat-item">
                    <div class="label"><span>CPU Usage</span><span id="cpu-percent">--%</span></div>
                    <div class="progress-bar"><div id="cpu-bar"></div></div>
                </div>
                <div class="stat-item">
                    <div class="label"><span>Memory Usage</span><span id="ram-percent">--%</span></div>
                    <div class="progress-bar"><div id="ram-bar"></div></div>
                </div>
            </div>
        </div>
    </div>

<script>
    let eventSource = null;

    // DOM Elements
    const elements = {
        generateBtn: document.getElementById('generate-btn'),
        urlInput: document.getElementById('url-input'),
        streamStatusCard: document.getElementById('stream-status-card'),
        resultCard: document.getElementById('result-card'),
        resultLink: document.getElementById('result-link'),
        copyBtn: document.getElementById('copy-btn'),
        bandwidthValue: document.getElementById('bandwidth-value'),
        downloadedValue: document.getElementById('downloaded-value'),
        totalSizeValue: document.getElementById('total-size-value'),
        progressPercent: document.getElementById('progress-percent'),
        progressBarInner: document.getElementById('progress-bar-inner'),
        cpuPercent: document.getElementById('cpu-percent'),
        cpuBar: document.getElementById('cpu-bar'),
        ramPercent: document.getElementById('ram-percent'),
        ramBar: document.getElementById('ram-bar'),
    };

    // Update Server Stats
    async function updateServerStats() {
        try {
            const response = await fetch('/api/system-stats');
            const stats = await response.json();
            elements.cpuPercent.textContent = `${stats.cpu_percent}%`;
            elements.cpuBar.style.width = `${stats.cpu_percent}%`;
            elements.ramPercent.textContent = `${stats.ram_percent}%`;
            elements.ramBar.style.width = `${stats.ram_percent}%`;
        } catch (error) { console.error('Error fetching system stats:', error); }
    }
    setInterval(updateServerStats, 2000);
    updateServerStats();

    // Generate Link Logic
    elements.generateBtn.addEventListener('click', () => {
        const url = elements.urlInput.value;
        if (!url) { alert('Please enter a URL.'); return; }

        if (eventSource) { eventSource.close(); } // Close previous connection

        // Reset UI
        elements.streamStatusCard.classList.remove('hidden');
        elements.resultCard.classList.add('hidden');
        ['bandwidthValue', 'downloadedValue', 'totalSizeValue'].forEach(key => elements[key].textContent = '--');
        elements.progressPercent.textContent = '0%';
        elements.progressBarInner.style.width = '0%';

        // Generate and display the link immediately
        const proxyUrl = `${window.location.origin}/proxy?url=${encodeURIComponent(url)}`;
        elements.resultLink.textContent = proxyUrl;
        elements.resultCard.classList.remove('hidden');

        // Start listening for real-time stream updates
        eventSource = new EventSource(`/api/stream-events?url=${encodeURIComponent(url)}`);
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.status === 'streaming') {
                elements.bandwidthValue.textContent = `${data.speed_mbps.toFixed(2)} Mbps`;
                elements.downloadedValue.textContent = `${data.downloaded_mb.toFixed(2)} MB`;
                elements.totalSizeValue.textContent = `${data.total_size_mb.toFixed(2)} MB`;
                elements.progressPercent.textContent = `${data.progress.toFixed(1)}%`;
                elements.progressBarInner.style.width = `${data.progress}%`;
            } else if (data.status === 'finished' || data.status === 'error') {
                eventSource.close();
            }
        };

        eventSource.onerror = function() {
            // Stop trying to reconnect if there's an error
            eventSource.close();
        };
    });
    
    // Copy Button
    elements.copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(elements.resultLink.textContent)
            .then(() => alert('Link copied!'))
            .catch(err => console.error('Failed to copy: ', err));
    });
</script>
</body>
</html>
"""

# --- Backend Logic ---

def stream_with_stats_reporting(video_url, req):
    """Generator that streams content and reports stats to the global dictionary."""
    url_key = video_url  # Use the URL as a unique key
    start_time = time.time()
    total_bytes = int(req.headers.get('content-length', 0))
    downloaded_bytes = 0

    try:
        for chunk in req.iter_content(chunk_size=1024 * 1024): # 1MB chunks
            if chunk:
                downloaded_bytes += len(chunk)
                elapsed_time = time.time() - start_time
                speed_bps = (downloaded_bytes * 8) / elapsed_time if elapsed_time > 0 else 0

                with status_lock:
                    STREAM_STATUS[url_key] = {
                        'status': 'streaming',
                        'speed_mbps': speed_bps / (1024 * 1024),
                        'downloaded_mb': downloaded_bytes / (1024 * 1024),
                        'total_size_mb': total_bytes / (1024 * 1024),
                        'progress': (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0
                    }
                yield chunk
        
        with status_lock:
            STREAM_STATUS[url_key]['status'] = 'finished'

    finally:
        # Clean up the status dictionary after a delay
        time.sleep(10) 
        with status_lock:
            if url_key in STREAM_STATUS:
                del STREAM_STATUS[url_key]
        print(f"[LOG] Cleaned up status for {url_key}")

@app.route('/api/stream-events')
def stream_events():
    """Server-Sent Events endpoint to push live stream stats to the client."""
    def event_generator():
        url_key = request.args.get('url')
        if not url_key:
            yield f"data: {json.dumps({'status': 'error', 'message': 'No URL specified'})}\n\n"
            return

        print(f"[SSE] Client connected for URL: {url_key}")
        try:
            while True:
                with status_lock:
                    status = STREAM_STATUS.get(url_key)
                
                if status:
                    yield f"data: {json.dumps(status)}\n\n"
                    if status.get('status') in ['finished', 'error']:
                        break
                time.sleep(1) # Send update every second
        except GeneratorExit:
            # This happens when the client disconnects
            print(f"[SSE] Client disconnected for URL: {url_key}")

    return Response(event_generator(), mimetype='text/event-stream')

@app.route('/api/system-stats')
def system_stats():
    """API for server CPU and RAM."""
    return jsonify({
        'cpu_percent': psutil.cpu_percent(interval=None),
        'ram_percent': psutil.virtual_memory().percent
    })

@app.route('/proxy')
def proxy():
    """The core proxy endpoint that initiates the streaming and reporting."""
    video_url = request.args.get('url')
    if not video_url:
        return "Error: 'url' parameter is missing.", 400

    try:
        req = requests.get(video_url, stream=True)
        req.raise_for_status()
        
        return Response(stream_with_stats_reporting(video_url, req), content_type=req.headers.get('content-type'))
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Proxy failed for URL {video_url}. Reason: {e}")
        return f"Proxy error: {e}", 500

@app.route('/')
def home():
    """Renders the main dashboard UI."""
    return render_template_string(ADVANCED_UI_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

