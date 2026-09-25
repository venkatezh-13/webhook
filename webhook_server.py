import sys
import json
import os
import threading
import time
import urllib.request
from datetime import datetime
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import alert system modules
from matcher import KeywordMatcher
from storage import AlertStorage
from notifiers import NotificationRouter
from rss_poller import RSSCircularPoller

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PORT = 5000
RECEIVED_ALERTS = []
INGESTION_STATUS = {"running": False, "message": "", "processed": 0, "matched": 0}


HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Circular Webhook Alert Control Center</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #090d16;
            --card-bg: rgba(22, 31, 48, 0.75);
            --card-border: rgba(255, 255, 255, 0.08);
            --input-bg: rgba(15, 23, 42, 0.8);
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --danger-bg: rgba(239, 68, 68, 0.15);
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Outfit', -apple-system, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1.5rem;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(236, 72, 153, 0.08) 0%, transparent 40%);
            background-attachment: fixed;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2rem;
            padding-bottom: 1.25rem;
            border-bottom: 1px solid var(--card-border);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-icon {
            font-size: 2rem;
            background: linear-gradient(135deg, #6366f1, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .title-area h1 {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .title-area p {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 4px;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.1);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.2);
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* Config Form Panel */
        .panel {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        }

        .panel-header {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
            color: #e0e7ff;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.25rem;
        }

        @media (min-width: 768px) {
            .form-grid-2 {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1.25rem;
            }
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        label {
            font-size: 0.85rem;
            font-weight: 500;
            color: #d1d5db;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        input[type="text"], input[type="url"] {
            width: 100%;
            background: var(--input-bg);
            border: 1px solid var(--card-border);
            color: #ffffff;
            padding: 12px 14px;
            border-radius: 10px;
            font-family: inherit;
            font-size: 0.95rem;
            transition: all 0.2s ease;
        }

        input[type="text"]:focus, input[type="url"]:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }

        .btn-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 1.5rem;
        }

        .btn {
            background: linear-gradient(135deg, var(--primary), var(--primary-hover));
            color: white;
            border: none;
            padding: 12px 22px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
        }

        .btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-main);
            border: 1px solid var(--card-border);
            box-shadow: none;
        }

        .btn-secondary:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.12);
        }

        /* Stats Section */
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            backdrop-filter: blur(12px);
            padding: 1.25rem;
            border-radius: 14px;
        }

        .stat-card .label {
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .stat-card .value {
            font-size: 1.75rem;
            font-weight: 700;
            margin-top: 4px;
            font-family: 'JetBrains Mono', monospace;
            color: #ffffff;
        }

        /* Feed List */
        .feed-container {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            background: var(--card-bg);
            border: 1px dashed var(--card-border);
            border-radius: 16px;
            color: var(--text-muted);
        }

        .empty-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }

        .alert-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-left: 4px solid var(--primary);
            backdrop-filter: blur(12px);
            border-radius: 14px;
            padding: 1.25rem;
            transition: all 0.25s ease;
            position: relative;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .alert-card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            transform: translateY(-2px);
        }

        .alert-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }

        .alert-title {
            font-size: 1.05rem;
            font-weight: 600;
            line-height: 1.4;
            color: #ffffff;
        }

        .timestamp {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            white-space: nowrap;
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 8px;
            border-radius: 6px;
        }

        .kw-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 0.75rem;
        }

        .kw-pill {
            background: var(--danger-bg);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.3);
            font-size: 0.75rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .dest-badge {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
            font-size: 0.75rem;
            font-weight: 500;
            padding: 3px 10px;
            border-radius: 6px;
            margin-bottom: 0.75rem;
            display: inline-block;
        }

        .alert-snippet {
            font-size: 0.9rem;
            color: #d1d5db;
            line-height: 1.5;
            background: rgba(0, 0, 0, 0.25);
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.04);
            margin-bottom: 1rem;
        }

        .alert-snippet strong {
            color: #fbbf24;
            background: rgba(251, 191, 36, 0.15);
            padding: 2px 5px;
            border-radius: 4px;
        }

        .alert-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .category-tag {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .link-btn {
            color: #818cf8;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            transition: color 0.2s ease;
        }

        .link-btn:hover {
            color: #a5b4fc;
            text-decoration: underline;
        }

        .loader {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="brand">
            <div class="brand-icon">⚡</div>
            <div class="title-area">
                <h1>Circular Webhook Control Center</h1>
                <p>Configure keywords, RSS feed, and webhook destinations</p>
            </div>
        </div>
        <div class="status-badge">
            <div class="pulse-dot"></div> Live Control Center Active
        </div>
    </header>

    <!-- Configuration Form -->
    <div class="panel">
        <div class="panel-header">⚙️ Configuration & Execution Panel</div>
        <div class="form-grid">
            <div class="form-group">
                <label for="rss_url">📡 RSS Feed URL</label>
                <input type="url" id="rss_url" value="" placeholder="Enter RSS XML Feed URL (e.g. https://nsearchives.nseindia.com/content/RSS/Circulars.xml)...">
            </div>
            
            <div class="form-grid-2">
                <div class="form-group">
                    <label for="keywords">🎯 Keywords (Comma-separated)</label>
                    <input type="text" id="keywords" value="tax, RBI, MOCK, compliance, urgent, listing, mutual fund, Suspension, usdinr, ram" placeholder="e.g. tax, RBI, MOCK, compliance">
                </div>
                <div class="form-group">
                    <label for="webhook_url">🌐 Webhook Destination URL</label>
                    <input type="url" id="webhook_url" value="" placeholder="Enter Webhook Destination URL (e.g. Svix, Whatomate, or http://localhost:5000/webhook)...">
                </div>
            </div>

            <div class="btn-group">
                <button class="btn" id="run-btn" onclick="runIngestion()">
                    <span>🚀 Ingest RSS & Send Webhooks</span>
                </button>
                <button class="btn btn-secondary" onclick="triggerTest()">
                    <span>🧪 Send Test Webhook</span>
                </button>
                <button class="btn btn-secondary" style="margin-left: auto;" onclick="clearFeed()">
                    <span>🗑 Clear List</span>
                </button>
            </div>
        </div>
    </div>

    <!-- Stats Bar -->
    <div class="stats-bar">
        <div class="stat-card">
            <div class="label">Total Webhooks Dispatched</div>
            <div class="value" id="stat-total">0</div>
        </div>
        <div class="stat-card">
            <div class="label">Matched Keywords</div>
            <div class="value" id="stat-keywords">0</div>
        </div>
        <div class="stat-card">
            <div class="label">Last Dispatched</div>
            <div class="value" id="stat-last" style="font-size: 1.1rem; padding-top: 4px;">Never</div>
        </div>
    </div>

    <!-- Live Feed Container -->
    <div id="feed" class="feed-container">
        <div class="empty-state">
            <div class="empty-icon">📡</div>
            <h3>No Webhook Alerts Triggered Yet</h3>
            <p style="margin-top: 6px;">Click <b>Ingest RSS & Send Webhooks</b> or <b>Send Test Webhook</b> above!</p>
        </div>
    </div>
</div>

<script>
    let lastCount = -1;
    let isPollingStatus = false;

    async function fetchAlerts() {
        try {
            const res = await fetch('/api/received');
            const alerts = await res.json();

            if (alerts.length !== lastCount) {
                lastCount = alerts.length;
                renderFeed(alerts);
            }
        } catch (e) {
            console.error('Fetch error:', e);
        }
    }

    function renderFeed(alerts) {
        const feed = document.getElementById('feed');
        document.getElementById('stat-total').innerText = alerts.length;

        const uniqueKws = new Set();
        alerts.forEach(a => (a.matched_keywords || []).forEach(k => uniqueKws.add(k)));
        document.getElementById('stat-keywords').innerText = uniqueKws.size;

        if (alerts.length > 0) {
            document.getElementById('stat-last').innerText = alerts[0].received_at_formatted || 'Just now';
            
            feed.innerHTML = alerts.map(a => `
                <div class="alert-card">
                    <div class="alert-header">
                        <div class="alert-title">${escapeHtml(a.title || 'Untitled Circular')}</div>
                        <div class="timestamp">${a.received_at_formatted || ''}</div>
                    </div>
                    ${a.destination ? `<div class="dest-badge">🌐 Sent to: ${escapeHtml(a.destination)}</div>` : ''}
                    <div class="kw-pills">
                        ${(a.matched_keywords || []).map(k => `<span class="kw-pill">🎯 ${escapeHtml(k)}</span>`).join('')}
                    </div>
                    ${a.snippet ? `<div class="alert-snippet">${formatSnippet(a.snippet)}</div>` : ''}
                    <div class="alert-footer">
                        <div class="category-tag">${a.category ? '📁 ' + escapeHtml(a.category) : ''}</div>
                        ${a.url ? `<a href="${a.url}" target="_blank" class="link-btn">View Circular Document &rarr;</a>` : ''}
                    </div>
                </div>
            `).join('');
        } else {
            document.getElementById('stat-last').innerText = 'Never';
            feed.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📡</div>
                    <h3>No Webhook Alerts Triggered Yet</h3>
                    <p style="margin-top: 6px;">Click <b>Ingest RSS & Send Webhooks</b> or <b>Send Test Webhook</b> above!</p>
                </div>
            `;
        }
    }

    function escapeHtml(text) {
        return (text || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function formatSnippet(text) {
        const escaped = escapeHtml(text);
        return escaped.replace(/\\*\\*\\[(.*?)\\]\\*\\*/g, '<strong>[$1]</strong>');
    }

    async function runIngestion() {
        const rssUrlInput = document.getElementById('rss_url');
        const webhookUrlInput = document.getElementById('webhook_url');
        const rssUrl = rssUrlInput.value.trim();
        const webhookUrl = webhookUrlInput.value.trim();
        const keywordsStr = document.getElementById('keywords').value.trim();

        if (!rssUrl) {
            alert('⚠️ Please enter an RSS Feed URL before running ingestion.');
            rssUrlInput.focus();
            return;
        }

        if (!webhookUrl) {
            alert('⚠️ Please enter a Webhook Destination URL.');
            webhookUrlInput.focus();
            return;
        }

        const runBtn = document.getElementById('run-btn');
        runBtn.innerHTML = '<div class="loader"></div> Processing Ingestion...';
        runBtn.disabled = true;

        const keywords = keywordsStr.split(',').map(k => k.trim()).filter(k => k);

        try {
            const res = await fetch('/api/run-poll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    rss_url: rssUrl,
                    keywords: keywords,
                    webhook_url: webhookUrl
                })
            });
            
            pollIngestionStatus();
        } catch(e) {
            alert('❌ Ingestion Error: ' + e.message);
            runBtn.innerHTML = '<span>🚀 Ingest RSS & Send Webhooks</span>';
            runBtn.disabled = false;
        }
    }

    async function pollIngestionStatus() {
        if (isPollingStatus) return;
        isPollingStatus = true;

        const interval = setInterval(async () => {
            try {
                const res = await fetch('/api/poll-status');
                const status = await res.json();
                await fetchAlerts();

                if (!status.running) {
                    clearInterval(interval);
                    isPollingStatus = false;
                    const runBtn = document.getElementById('run-btn');
                    runBtn.innerHTML = '<span>🚀 Ingest RSS & Send Webhooks</span>';
                    runBtn.disabled = false;
                    await fetchAlerts();
                    alert(`✅ Ingestion Complete!\nEvaluated: ${status.processed} circulars.\nTriggered & Dispatched: ${status.matched} keyword alerts.`);
                }
            } catch(e) {
                clearInterval(interval);
                isPollingStatus = false;
                const runBtn = document.getElementById('run-btn');
                runBtn.innerHTML = '<span>🚀 Ingest RSS & Send Webhooks</span>';
                runBtn.disabled = false;
            }
        }, 600);
    }


    async function triggerTest() {
        const webhookUrlInput = document.getElementById('webhook_url');
        const webhookUrl = webhookUrlInput.value.trim();
        if (!webhookUrl) {
            alert('⚠️ Please enter a Webhook Destination URL to send a test alert.');
            webhookUrlInput.focus();
            return;
        }

        try {
            await fetch('/api/trigger-test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ webhook_url: webhookUrl })
            });
            fetchAlerts();
        } catch(e) {
            alert('Error triggering test webhook');
        }
    }

    async function clearFeed() {
        try {
            await fetch('/api/clear', { method: 'POST' });
            fetchAlerts();
        } catch(e) {}
    }

    setInterval(fetchAlerts, 1000);
    fetchAlerts();
</script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP Server to prevent deadlocks when dispatching local webhooks."""
    daemon_threads = True

class LocalWebhookReceiver(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path in ("/webhook", "/"):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                payload = json.loads(post_data.decode('utf-8'))
                payload["received_at_formatted"] = datetime.now().strftime("%H:%M:%S")
                payload["destination"] = "Local Receiver (http://localhost:5000/webhook)"
                
                PROCESSED_ALERTS.insert(0, payload)
                if len(PROCESSED_ALERTS) > 100:
                    PROCESSED_ALERTS.pop()

                print(f"📥 [Webhook Received] '{payload.get('title')[:50]}' | Keywords: {payload.get('matched_keywords')}")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Alert received"}).encode('utf-8'))

            except Exception as e:
                print(f"❌ Error parsing payload: {e}")
                self.send_response(400)
                self.end_headers()

        elif self.path == "/api/run-poll":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data.decode('utf-8')) if content_length > 0 else {}

            rss_url = params.get("rss_url") or "https://venkatezh-13.github.io/circulars/docs/rss/all.xml"
            keywords = params.get("keywords") or ["tax", "RBI", "MOCK", "compliance", "urgent"]
            webhook_url = params.get("webhook_url") or "http://localhost:5000/webhook"

            threading.Thread(target=self._async_run_ingestion, args=(rss_url, keywords, webhook_url), daemon=True).start()

            self.send_response(202)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started", "message": "Ingestion launched in background"}).encode('utf-8'))

        elif self.path == "/api/trigger-test":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data.decode('utf-8')) if content_length > 0 else {}

            webhook_url = params.get("webhook_url") or "http://localhost:5000/webhook"

            test_payload = {
                "event": "circular_alert",
                "title": "URGENT: Test RBI Circular on Tax Policy & Compliance Update",
                "matched_keywords": ["URGENT", "TAX", "COMPLIANCE"],
                "snippet": "This is a test notification payload verifying integration with **[URGENT]** **[TAX]** **[COMPLIANCE]** updates.",
                "url": "https://venkatezh-13.github.io/circulars",
                "category": "Regulatory Update",
                "received_at_formatted": datetime.now().strftime("%H:%M:%S"),
                "destination": webhook_url
            }

            if "localhost" in webhook_url or "127.0.0.1" in webhook_url:
                PROCESSED_ALERTS.insert(0, test_payload)
            else:
                try:
                    req = urllib.request.Request(webhook_url, data=json.dumps(test_payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
                    urllib.request.urlopen(req, timeout=5)
                    PROCESSED_ALERTS.insert(0, test_payload)
                except Exception as e:
                    print(f"Error dispatching test webhook: {e}")

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))

        elif self.path == "/api/clear":
            RECEIVED_ALERTS.clear()
            self.send_response(200)
            self.end_headers()

    def _async_run_ingestion(self, rss_url, keywords, webhook_url):
        global INGESTION_STATUS, RECEIVED_ALERTS
        INGESTION_STATUS["running"] = True
        INGESTION_STATUS["processed"] = 0
        INGESTION_STATUS["matched"] = 0

        def on_dispatch_callback(payload):
            item = {
                **payload,
                "received_at_formatted": datetime.now().strftime("%H:%M:%S")
            }
            if not any(a.get("title") == item.get("title") for a in RECEIVED_ALERTS[:20]):
                RECEIVED_ALERTS.insert(0, item)

        try:
            print(f"\n⚙️ ASYNC INGESTION THREAD: RSS={rss_url} | Keywords={keywords} | Webhook={webhook_url}")
            matcher = KeywordMatcher(keywords=keywords, match_mode="any")
            storage = AlertStorage(db_path=":memory:")
            router = NotificationRouter(
                config={"webhook_url": webhook_url, "rate_limit_delay_seconds": 0.1},
                env_vars={"WEBHOOK_URL": webhook_url},
                on_dispatch=on_dispatch_callback
            )
            poller = RSSCircularPoller(matcher=matcher, storage=storage, router=router, rss_url=rss_url)

            result = poller.fetch_and_process()
            INGESTION_STATUS["processed"] = result.get("processed", 0)
            INGESTION_STATUS["matched"] = result.get("matched", 0)

        except Exception as e:
            print(f"❌ Background Ingestion Error: {e}")
        finally:
            INGESTION_STATUS["running"] = False

    def do_GET(self):
        if self.path == "/api/received":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(RECEIVED_ALERTS).encode('utf-8'))
        elif self.path == "/api/poll-status":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(INGESTION_STATUS).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode('utf-8'))


def run_server():
    server_address = ('', PORT)
    httpd = ThreadedHTTPServer(server_address, LocalWebhookReceiver)
    print(f"🚀 Multi-Threaded Local Webhook Control Center running at: http://localhost:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local webhook server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
