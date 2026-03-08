#!/usr/bin/env python3
"""TLDL — Too Long; Didn't Listen. Web UI for video transcription."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

import json

from flask import Flask, jsonify, render_template_string, request, send_file

app = Flask(__name__)

TLDL_DIR = Path.home() / ".tldl"
LIBRARY_DIR = TLDL_DIR / "library"
PROFILE_PATH = TLDL_DIR / "me.md"

# In-memory job store
jobs: dict[str, dict] = {}


def load_profile() -> str:
    """Load user profile from ~/.tldl/me.md."""
    if PROFILE_PATH.exists():
        text = PROFILE_PATH.read_text().strip()
        # Filter out comment-only lines
        lines = [l for l in text.split("\n") if not l.strip().startswith("<!--")]
        content = "\n".join(lines).strip()
        if content:
            return content
    return ""


def save_to_library(title: str, markdown: str):
    """Save transcript to ~/.tldl/library/."""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^\w\s-]', '', title)[:60].strip().replace(' ', '_').lower()
    if not safe:
        safe = "untitled"
    path = LIBRARY_DIR / f"{safe}.md"
    # Avoid overwriting — append a suffix
    counter = 1
    while path.exists():
        path = LIBRARY_DIR / f"{safe}_{counter}.md"
        counter += 1
    path.write_text(markdown)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TLDL</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    background: #0a0a0a;
    color: #e0e0e0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .container {
    width: 100%;
    max-width: 720px;
    padding: 48px 24px;
  }

  h1 {
    font-size: 2.4rem;
    font-weight: 700;
    letter-spacing: -1px;
    margin-bottom: 4px;
  }

  h1 span { color: #7c7c7c; }

  .tagline {
    color: #555;
    font-size: 0.85rem;
    margin-bottom: 40px;
  }

  .input-group {
    display: flex;
    gap: 0;
    margin-bottom: 12px;
  }

  input[type="text"], input[type="password"] {
    flex: 1;
    background: #141414;
    border: 1px solid #2a2a2a;
    color: #e0e0e0;
    padding: 14px 16px;
    font-family: inherit;
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
  }

  input[type="text"]:focus, input[type="password"]:focus {
    border-color: #444;
  }

  input[type="text"] {
    border-radius: 8px 0 0 8px;
  }

  button.go {
    background: #fff;
    color: #0a0a0a;
    border: 1px solid #fff;
    padding: 14px 28px;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    border-radius: 0 8px 8px 0;
    transition: opacity 0.2s;
  }

  button.go:hover { opacity: 0.85; }
  button.go:disabled { opacity: 0.3; cursor: not-allowed; }

  .options {
    display: flex;
    gap: 16px;
    margin-bottom: 32px;
    flex-wrap: wrap;
  }

  .options label {
    color: #666;
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  select, .options input {
    background: #141414;
    border: 1px solid #2a2a2a;
    color: #e0e0e0;
    padding: 6px 10px;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 4px;
    outline: none;
  }

  .options input { width: 160px; }

  .status {
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 24px;
    font-size: 0.85rem;
    display: none;
  }

  .status.active {
    display: block;
    background: #111;
    border: 1px solid #2a2a2a;
  }

  .status .spinner {
    display: inline-block;
    width: 12px; height: 12px;
    border: 2px solid #333;
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: 8px;
    vertical-align: middle;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .status.error { border-color: #442222; background: #1a0a0a; color: #cc6666; }
  .status.done { border-color: #224422; background: #0a1a0a; color: #66cc66; }

  .result {
    display: none;
  }

  .result.visible { display: block; }

  .toolbar {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }

  .toolbar button {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    color: #aaa;
    padding: 8px 16px;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .toolbar button:hover { background: #222; color: #fff; }

  .transcript {
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 8px;
    padding: 24px;
    max-height: 70vh;
    overflow-y: auto;
    line-height: 1.7;
    font-size: 0.88rem;
  }

  .transcript h1 { font-size: 1.4rem; margin-bottom: 8px; }
  .transcript hr { border: none; border-top: 1px solid #222; margin: 16px 0; }
  .transcript p { margin-bottom: 6px; }
  .transcript strong { color: #888; font-weight: 500; }

  .transcript::-webkit-scrollbar { width: 6px; }
  .transcript::-webkit-scrollbar-track { background: transparent; }
  .transcript::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 3px; }

  .search-bar {
    margin-bottom: 16px;
    display: none;
  }

  .search-bar.visible { display: block; }

  .search-bar input {
    width: 100%;
    background: #141414;
    border: 1px solid #2a2a2a;
    color: #e0e0e0;
    padding: 10px 14px;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 6px;
    outline: none;
  }

  mark {
    background: #3a3a00;
    color: #ffff66;
    padding: 1px 2px;
    border-radius: 2px;
  }

  .summary-box {
    display: none;
    background: #0f1a0f;
    border: 1px solid #1a3a1a;
    border-radius: 8px;
    margin-bottom: 16px;
    overflow: hidden;
  }

  .summary-box.visible { display: block; }

  .summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: #0a140a;
    border-bottom: 1px solid #1a3a1a;
    font-size: 0.8rem;
    color: #66cc66;
    font-weight: 600;
  }

  .summary-header button {
    background: none;
    border: none;
    color: #66cc66;
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0 4px;
  }

  .summary-content {
    padding: 16px;
    font-size: 0.88rem;
    line-height: 1.7;
    color: #c0d8c0;
  }

  .summary-content p { margin-bottom: 8px; }
  .summary-content ul, .summary-content ol { margin: 8px 0 8px 20px; }
  .summary-content li { margin-bottom: 4px; }
  .summary-content h1, .summary-content h2, .summary-content h3 {
    font-size: 1rem;
    margin: 12px 0 6px;
    color: #e0e0e0;
  }

  .chat-panel {
    display: none;
    background: #0a0f1a;
    border: 1px solid #1a2a3a;
    border-radius: 8px;
    margin-bottom: 16px;
    overflow: hidden;
  }

  .chat-panel.visible { display: block; }

  .chat-messages {
    max-height: 360px;
    overflow-y: auto;
    padding: 16px;
  }

  .chat-messages::-webkit-scrollbar { width: 6px; }
  .chat-messages::-webkit-scrollbar-track { background: transparent; }
  .chat-messages::-webkit-scrollbar-thumb { background: #1a2a3a; border-radius: 3px; }

  .chat-msg {
    margin-bottom: 14px;
    font-size: 0.85rem;
    line-height: 1.6;
  }

  .chat-msg.user {
    color: #7aa2f7;
  }

  .chat-msg.user::before {
    content: 'you: ';
    font-weight: 600;
    color: #5a82d7;
  }

  .chat-msg.assistant {
    color: #c0d0e8;
    padding-left: 0;
  }

  .chat-msg.assistant p { margin-bottom: 6px; }
  .chat-msg.assistant ul { margin: 6px 0 6px 18px; }
  .chat-msg.assistant li { margin-bottom: 3px; }
  .chat-msg.assistant strong { color: #9ab8e8; }

  .chat-msg.thinking {
    color: #555;
    font-style: italic;
  }

  .chat-input-row {
    display: flex;
    border-top: 1px solid #1a2a3a;
  }

  .chat-input-row input {
    flex: 1;
    background: #0d1220;
    border: none;
    color: #e0e0e0;
    padding: 12px 16px;
    font-family: inherit;
    font-size: 0.85rem;
    outline: none;
  }

  .chat-input-row button {
    background: #1a2a3a;
    border: none;
    color: #7aa2f7;
    padding: 12px 20px;
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .chat-input-row button:hover { background: #243a50; }
  .chat-input-row button:disabled { opacity: 0.3; cursor: not-allowed; }
</style>
</head>
<body>
<div class="container">
  <h1>TLDL<span>.</span></h1>
  <p class="tagline">too long; didn't listen</p>

  <div class="input-group">
    <input type="text" id="url" placeholder="paste a video url" autofocus>
    <button class="go" id="goBtn" onclick="start()">transcribe</button>
  </div>

  <div class="options">
    <label>model
      <select id="model">
        <option value="tiny">tiny</option>
        <option value="base" selected>base</option>
        <option value="small">small</option>
        <option value="medium">medium</option>
        <option value="large">large</option>
        <option value="turbo">turbo</option>
      </select>
    </label>
    <label>password
      <input type="password" id="password" placeholder="optional">
    </label>
  </div>

  <div class="status" id="status"></div>

  <div class="result" id="result">
    <div class="toolbar">
      <button onclick="copyText()">copy</button>
      <button onclick="downloadMd()">download .md</button>
      <button onclick="toggleSearch()">search</button>
      <button id="summarizeBtn" onclick="summarize()">summarize</button>
      <button id="chatBtn" onclick="toggleChat()">ask</button>
    </div>
    <div class="search-bar" id="searchBar">
      <input type="text" id="searchInput" placeholder="search transcript..." oninput="searchTranscript()">
    </div>
    <div class="summary-box" id="summaryBox">
      <div class="summary-header">
        <span>Summary</span>
        <button onclick="closeSummary()">&times;</button>
      </div>
      <div class="summary-content" id="summaryContent"></div>
    </div>
    <div class="chat-panel" id="chatPanel">
      <div class="chat-messages" id="chatMessages"></div>
      <div class="chat-input-row">
        <input type="text" id="chatInput" placeholder="ask anything about this video..." onkeydown="if(event.key==='Enter')sendChat()">
        <button onclick="sendChat()">send</button>
      </div>
    </div>
    <div class="transcript" id="transcript"></div>
  </div>
</div>

<script>
let currentJobId = null;
let rawMarkdown = '';
let rawHtml = '';

function start() {
  const url = document.getElementById('url').value.trim();
  if (!url) return;

  const model = document.getElementById('model').value;
  const password = document.getElementById('password').value;

  document.getElementById('goBtn').disabled = true;
  document.getElementById('result').classList.remove('visible');
  document.getElementById('chatPanel').classList.remove('visible');
  document.getElementById('chatMessages').innerHTML = '';
  chatHistory = [];

  const status = document.getElementById('status');
  status.className = 'status active';
  status.innerHTML = '<span class="spinner"></span> starting...';

  fetch('/api/transcribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, model, password: password || null })
  })
  .then(r => r.json())
  .then(data => {
    currentJobId = data.job_id;
    poll();
  })
  .catch(err => {
    status.className = 'status active error';
    status.textContent = 'failed to start: ' + err.message;
    document.getElementById('goBtn').disabled = false;
  });
}

function poll() {
  if (!currentJobId) return;

  fetch('/api/status/' + currentJobId)
  .then(r => r.json())
  .then(data => {
    const status = document.getElementById('status');

    if (data.status === 'running') {
      status.className = 'status active';
      status.innerHTML = '<span class="spinner"></span> ' + data.message;
      setTimeout(poll, 2000);
    } else if (data.status === 'done') {
      status.className = 'status active done';
      status.textContent = 'done';
      rawMarkdown = data.markdown;
      rawHtml = data.html;
      document.getElementById('transcript').innerHTML = rawHtml;
      document.getElementById('result').classList.add('visible');
      document.getElementById('goBtn').disabled = false;
    } else if (data.status === 'error') {
      status.className = 'status active error';
      status.textContent = data.message;
      document.getElementById('goBtn').disabled = false;
    }
  });
}

function copyText() {
  navigator.clipboard.writeText(rawMarkdown);
  event.target.textContent = 'copied!';
  setTimeout(() => event.target.textContent = 'copy', 1500);
}

function downloadMd() {
  const blob = new Blob([rawMarkdown], { type: 'text/markdown' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'tldl_transcript.md';
  a.click();
}

function toggleSearch() {
  const bar = document.getElementById('searchBar');
  bar.classList.toggle('visible');
  if (bar.classList.contains('visible')) {
    document.getElementById('searchInput').focus();
  } else {
    document.getElementById('searchInput').value = '';
    document.getElementById('transcript').innerHTML = rawHtml;
  }
}

function searchTranscript() {
  const q = document.getElementById('searchInput').value.trim().toLowerCase();
  if (!q) {
    document.getElementById('transcript').innerHTML = rawHtml;
    return;
  }
  const escaped = q.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
  const re = new RegExp('(' + escaped + ')', 'gi');
  document.getElementById('transcript').innerHTML = rawHtml.replace(re, '<mark>$1</mark>');
}

function summarize() {
  const btn = document.getElementById('summarizeBtn');
  const box = document.getElementById('summaryBox');
  const content = document.getElementById('summaryContent');

  if (box.classList.contains('visible')) {
    box.classList.remove('visible');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'summarizing...';
  content.innerHTML = '<span class="spinner"></span> asking claude...';
  box.classList.add('visible');

  fetch('/api/summarize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ markdown: rawMarkdown })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      content.textContent = 'error: ' + data.error;
    } else {
      content.innerHTML = data.html;
    }
    btn.disabled = false;
    btn.textContent = 'summarize';
  })
  .catch(err => {
    content.textContent = 'error: ' + err.message;
    btn.disabled = false;
    btn.textContent = 'summarize';
  });
}

function closeSummary() {
  document.getElementById('summaryBox').classList.remove('visible');
}

let chatHistory = [];

function toggleChat() {
  const panel = document.getElementById('chatPanel');
  panel.classList.toggle('visible');
  if (panel.classList.contains('visible')) {
    document.getElementById('chatInput').focus();
    if (chatHistory.length === 0) {
      const msgs = document.getElementById('chatMessages');
      msgs.innerHTML = '<div class="chat-msg thinking">ask anything about this video — answers are grounded in the transcript and your context from ~/.tldl/me.md</div>';
    }
  }
}

function sendChat() {
  const input = document.getElementById('chatInput');
  const q = input.value.trim();
  if (!q) return;

  const msgs = document.getElementById('chatMessages');
  const sendBtn = input.nextElementSibling;

  // Clear hint on first message
  if (chatHistory.length === 0) msgs.innerHTML = '';

  // Show user message
  const userDiv = document.createElement('div');
  userDiv.className = 'chat-msg user';
  userDiv.textContent = q;
  msgs.appendChild(userDiv);

  chatHistory.push({ role: 'user', content: q });
  input.value = '';
  input.disabled = true;
  sendBtn.disabled = true;

  // Show thinking
  const thinkDiv = document.createElement('div');
  thinkDiv.className = 'chat-msg thinking';
  thinkDiv.innerHTML = '<span class="spinner"></span> thinking...';
  msgs.appendChild(thinkDiv);
  msgs.scrollTop = msgs.scrollHeight;

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q, transcript: rawMarkdown, history: chatHistory })
  })
  .then(r => r.json())
  .then(data => {
    msgs.removeChild(thinkDiv);
    const aDiv = document.createElement('div');
    aDiv.className = 'chat-msg assistant';
    if (data.error) {
      aDiv.textContent = 'error: ' + data.error;
    } else {
      aDiv.innerHTML = data.html;
      chatHistory.push({ role: 'assistant', content: data.markdown });
    }
    msgs.appendChild(aDiv);
    msgs.scrollTop = msgs.scrollHeight;
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  })
  .catch(err => {
    msgs.removeChild(thinkDiv);
    const eDiv = document.createElement('div');
    eDiv.className = 'chat-msg assistant';
    eDiv.textContent = 'error: ' + err.message;
    msgs.appendChild(eDiv);
    input.disabled = false;
    sendBtn.disabled = false;
  });
}

document.getElementById('url').addEventListener('keydown', e => {
  if (e.key === 'Enter') start();
});
</script>
</body>
</html>
"""


def run_transcription(job_id: str, url: str, model: str, password: str | None):
    """Background worker for a transcription job."""
    job = jobs[job_id]

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Get title
            job["message"] = "fetching video info..."
            cmd = ["yt-dlp", "--get-title", "--no-playlist", url]
            if password:
                cmd.extend(["--video-password", password])
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            title = r.stdout.strip() if r.returncode == 0 else "Untitled Video"

            # Step 2: Download audio
            job["message"] = "downloading audio..."
            audio_path = os.path.join(tmpdir, "audio.wav")
            cmd = [
                "yt-dlp", "-x",
                "--audio-format", "wav",
                "--audio-quality", "0",
                "-o", audio_path,
                "--no-playlist",
                "--no-check-certificates",
            ]
            if password:
                cmd.extend(["--video-password", password])
            cmd.append(url)

            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                job["status"] = "error"
                job["message"] = f"download failed: {r.stderr.splitlines()[-1] if r.stderr else 'unknown error'}"
                return

            # Find the actual audio file
            audio_file = None
            base = Path(audio_path).stem
            for f in Path(tmpdir).iterdir():
                if f.stem == base:
                    audio_file = str(f)
                    break

            if not audio_file:
                job["status"] = "error"
                job["message"] = "audio file not found after download"
                return

            # Step 3: Transcribe
            job["message"] = f"transcribing with whisper ({model})..."
            import whisper as w

            model_obj = w.load_model(model)
            result = model_obj.transcribe(audio_file, verbose=False)

            # Step 4: Format markdown
            lines = [f"# {title}\n", f"**Source:** {url}\n", "---\n", "## Transcript\n"]
            segments = result.get("segments", [])
            if not segments:
                lines.append(result.get("text", ""))
            else:
                for seg in segments:
                    s = seg["start"]
                    h, m, sec = int(s // 3600), int((s % 3600) // 60), int(s % 60)
                    ts = f"{h:02d}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"
                    lines.append(f"**[{ts}]** {seg['text'].strip()}\n")

            lines.extend(["\n---\n", f"*Transcribed with Whisper ({model}) — language: {result.get('language', '?')}*\n"])

            markdown = "\n".join(lines)

            # Convert to simple HTML for display
            html = markdown_to_html(markdown)

            job["status"] = "done"
            job["markdown"] = markdown
            job["html"] = html
            job["message"] = "done"

            # Auto-save to library
            try:
                save_to_library(title, markdown)
            except Exception:
                pass  # non-critical

    except Exception as e:
        job["status"] = "error"
        job["message"] = str(e)


def markdown_to_html(md: str) -> str:
    """Minimal markdown to HTML."""
    lines = md.split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        is_list_item = stripped.startswith("- ") or stripped.startswith("* ") or re.match(r'^\d+\. ', stripped)

        if is_list_item and not in_list:
            html_lines.append("<ul>")
            in_list = True
        elif not is_list_item and in_list:
            html_lines.append("</ul>")
            in_list = False

        if line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif stripped == "---":
            html_lines.append("<hr>")
        elif is_list_item:
            text = re.sub(r'^[-*]\s+', '', stripped)
            text = re.sub(r'^\d+\.\s+', '', text)
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
            text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
            html_lines.append(f"<li>{text}</li>")
        elif stripped:
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
            html_lines.append(f"<p>{line}</p>")

    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400

    model = data.get("model", "base")
    password = data.get("password")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "message": "starting...", "markdown": "", "html": ""}

    t = threading.Thread(target=run_transcription, args=(job_id, url, model, password))
    t.daemon = True
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    data = request.json
    markdown = data.get("markdown", "").strip()
    if not markdown:
        return jsonify({"error": "no transcript to summarize"}), 400

    prompt = (
        "Summarize this video transcript concisely. Include: key points, "
        "main takeaways, and any important details. Use markdown formatting "
        "with bullet points. Be direct — no preamble.\n\n"
        f"{markdown}"
    )

    try:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        r = subprocess.run(
            ["claude", "--print", "--model", "sonnet", prompt],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if r.returncode != 0:
            return jsonify({"error": r.stderr.strip() or "claude CLI failed"}), 500

        summary_md = r.stdout.strip()
        summary_html = markdown_to_html(summary_md)
        return jsonify({"markdown": summary_md, "html": summary_html})

    except subprocess.TimeoutExpired:
        return jsonify({"error": "summarization timed out"}), 500
    except FileNotFoundError:
        return jsonify({"error": "claude CLI not found — install it first"}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    question = data.get("question", "").strip()
    transcript = data.get("transcript", "").strip()
    history = data.get("history", [])

    if not question or not transcript:
        return jsonify({"error": "question and transcript required"}), 400

    # Build the prompt with context layers
    profile = load_profile()

    system_parts = [
        "You are helping the user understand a video they watched.",
        "Answer their questions grounded in the transcript below.",
        "Be concise and direct. Use markdown formatting.",
        "If the transcript doesn't contain enough info to answer, say so.",
        "When relevant, connect ideas to the user's background.",
    ]

    if profile:
        system_parts.append(f"\nHere is who the user is:\n{profile}")

    system_parts.append(f"\nHere is the transcript:\n{transcript}")

    # Build conversation for Claude
    # We pass the full context as a single prompt with conversation history
    prompt_parts = ["\n".join(system_parts), ""]

    # Add conversation history (skip the current question, it's last)
    for msg in history[:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        prompt_parts.append(f"{role}: {msg['content']}")

    prompt_parts.append(f"User: {question}")
    prompt_parts.append("Assistant:")

    full_prompt = "\n\n".join(prompt_parts)

    try:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        r = subprocess.run(
            ["claude", "--print", "--model", "sonnet", full_prompt],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if r.returncode != 0:
            return jsonify({"error": r.stderr.strip() or "claude CLI failed"}), 500

        answer_md = r.stdout.strip()
        answer_html = markdown_to_html(answer_md)
        return jsonify({"markdown": answer_md, "html": answer_html})

    except subprocess.TimeoutExpired:
        return jsonify({"error": "request timed out"}), 500
    except FileNotFoundError:
        return jsonify({"error": "claude CLI not found"}), 500


@app.route("/api/status/<job_id>")
def api_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    print("\n  TLDL — too long; didn't listen")
    print("  http://localhost:4983\n")
    app.run(host="127.0.0.1", port=4983, debug=False)
