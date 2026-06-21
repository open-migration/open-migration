"""
omigrate serve — Local web UI for Open Migration.

Install: pip install "open-migration[web]"
Run:     omigrate serve
Opens:   http://localhost:7337
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    from flask import Flask, Response, jsonify, render_template_string, request, send_file
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

_WEB_UI = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Open Migration</title>
<style>
:root {
  --bg: #0a0a0f;
  --surface: #111118;
  --surface2: #18181f;
  --surface3: #1e1e28;
  --border: #2a2a38;
  --text: #e0e0ef;
  --text2: #9090a8;
  --text3: #5a5a72;
  --accent: #7c6af7;
  --accent2: #5b4de0;
  --accent-glow: rgba(124,106,247,0.2);
  --green: #4ade80;
  --red: #f87171;
  --radius: 12px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.logo-icon {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, var(--accent), #a78bfa);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.2rem;
}
.logo-text {
  font-size: 1.4rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent), #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.tagline { color: var(--text2); font-size: 0.9rem; margin-bottom: 40px; }

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  width: 100%;
  max-width: 560px;
  overflow: hidden;
}
.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text);
}

/* Drop zone */
.drop-zone {
  padding: 40px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid var(--border);
  position: relative;
}
.drop-zone.dragover { background: var(--surface2); }
.drop-zone.has-file { background: rgba(74,222,128,0.04); }
.drop-icon {
  font-size: 2.5rem;
  line-height: 1;
}
.drop-title { font-size: 1rem; font-weight: 500; }
.drop-sub { font-size: 0.8rem; color: var(--text3); }
.drop-badge {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 4px;
}
.platform-badge {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 0.75rem;
  color: var(--text2);
}
#file-input { display: none; }
.file-selected {
  display: none;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--surface2);
  border-radius: 8px;
  font-size: 0.85rem;
  color: var(--green);
  border: 1px solid rgba(74,222,128,0.2);
  width: 100%;
  max-width: 340px;
}
.file-selected.show { display: flex; }
.file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.remove-file { cursor: pointer; color: var(--text3); font-size: 1.1rem; flex-shrink: 0; }
.remove-file:hover { color: var(--red); }

/* Options */
.options { padding: 20px 24px; border-bottom: 1px solid var(--border); }
.opt-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text3);
  margin-bottom: 10px;
}
.opt-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.opt-btn {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text2);
  padding: 10px 8px;
  cursor: pointer;
  text-align: center;
  font-size: 0.8rem;
  transition: all 0.15s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.opt-btn:hover { border-color: var(--accent); color: var(--text); }
.opt-btn.selected { background: var(--accent-glow); border-color: var(--accent); color: var(--text); }
.opt-btn .icon { font-size: 1.2rem; }
.opt-btn .label { font-weight: 500; }
.opt-btn .desc { font-size: 0.68rem; color: var(--text3); }
.opt-btn.selected .desc { color: var(--text2); }

/* Action */
.action { padding: 20px 24px; }
.convert-btn {
  width: 100%;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 0.95rem;
  font-weight: 600;
  padding: 13px;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.convert-btn:hover:not(:disabled) { background: var(--accent2); }
.convert-btn:active:not(:disabled) { transform: scale(0.99); }
.convert-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Progress */
#progress-wrap {
  display: none;
  padding: 20px 24px;
  border-top: 1px solid var(--border);
  flex-direction: column;
  gap: 12px;
}
#progress-wrap.show { display: flex; }
.progress-bar-wrap {
  background: var(--surface2);
  border-radius: 100px;
  height: 5px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #a78bfa);
  border-radius: 100px;
  transition: width 0.4s ease;
  width: 0%;
}
.progress-bar.indeterminate {
  width: 40%;
  animation: slide 1.4s ease-in-out infinite;
}
@keyframes slide {
  0% { transform: translateX(-200%); }
  100% { transform: translateX(400%); }
}
#progress-msg { font-size: 0.85rem; color: var(--text2); }

/* Result */
#result-wrap {
  display: none;
  padding: 20px 24px;
  border-top: 1px solid var(--border);
  flex-direction: column;
  gap: 12px;
}
#result-wrap.show { display: flex; }
.result-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.stat-mini {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  text-align: center;
}
.stat-mini .val { font-size: 1.2rem; font-weight: 700; color: var(--text); }
.stat-mini .lbl { font-size: 0.68rem; color: var(--text3); text-transform: uppercase; letter-spacing: 0.04em; }
.download-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(74,222,128,0.1);
  border: 1px solid rgba(74,222,128,0.3);
  border-radius: 8px;
  color: var(--green);
  font-size: 0.9rem;
  font-weight: 600;
  padding: 12px;
  text-decoration: none;
  transition: background 0.15s;
}
.download-btn:hover { background: rgba(74,222,128,0.18); }
.error-msg {
  background: rgba(248,113,113,0.08);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: 8px;
  color: var(--red);
  font-size: 0.85rem;
  padding: 12px 16px;
  display: none;
}
.error-msg.show { display: block; }

/* Footer */
.footer {
  margin-top: 32px;
  font-size: 0.75rem;
  color: var(--text3);
  text-align: center;
}
.footer a { color: var(--accent); text-decoration: none; }
.footer a:hover { text-decoration: underline; }
</style>
</head>
<body>

<div class="logo">
  <div class="logo-icon">⚡</div>
  <div class="logo-text">Open Migration</div>
</div>
<div class="tagline">Own your AI conversations. Move anywhere.</div>

<div class="card">
  <div class="card-header">📁 Upload your export file</div>

  <div class="drop-zone" id="drop-zone">
    <input type="file" id="file-input" accept=".json,.zip">
    <div class="drop-icon" id="drop-icon">☁️</div>
    <div class="drop-title" id="drop-title">Drop your export here or click to browse</div>
    <div class="drop-sub">Supports .json, .zip, and directories</div>
    <div class="drop-badge">
      <span class="platform-badge">🤖 ChatGPT</span>
      <span class="platform-badge">⚡ Claude</span>
      <span class="platform-badge">✨ Gemini</span>
    </div>
    <div class="file-selected" id="file-selected">
      <span>✓</span>
      <span class="file-name" id="file-name-display"></span>
      <span class="remove-file" id="remove-file">✕</span>
    </div>
  </div>

  <div class="options">
    <div class="opt-label">Output format</div>
    <div class="opt-grid">
      <div class="opt-btn selected" data-target="html">
        <span class="icon">🌐</span>
        <span class="label">HTML Site</span>
        <span class="desc">Open in browser, search, no server</span>
      </div>
      <div class="opt-btn" data-target="obsidian">
        <span class="icon">🔮</span>
        <span class="label">Obsidian</span>
        <span class="desc">Vault with wikilinks & frontmatter</span>
      </div>
      <div class="opt-btn" data-target="markdown">
        <span class="icon">📝</span>
        <span class="label">Markdown</span>
        <span class="desc">Plain .md files, works anywhere</span>
      </div>
    </div>
  </div>

  <div class="action">
    <button class="convert-btn" id="convert-btn" disabled>
      <span>Convert</span>
    </button>
  </div>

  <div id="progress-wrap">
    <div id="progress-msg">Reading export…</div>
    <div class="progress-bar-wrap">
      <div class="progress-bar indeterminate" id="progress-bar"></div>
    </div>
  </div>

  <div class="error-msg" id="error-msg"></div>

  <div id="result-wrap">
    <div class="result-stats" id="result-stats"></div>
    <a class="download-btn" id="download-link" href="#" download>
      ⬇ Download your archive
    </a>
  </div>
</div>

<div class="footer">
  Running locally on <strong>localhost:{{ port }}</strong> &nbsp;·&nbsp;
  Your data never leaves this machine &nbsp;·&nbsp;
  <a href="https://github.com/open-migration/open-migration" target="_blank">GitHub</a>
</div>

<script>
let selectedFile = null;
let selectedTarget = 'html';

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileSelected = document.getElementById('file-selected');
const fileNameDisplay = document.getElementById('file-name-display');
const removeFile = document.getElementById('remove-file');
const convertBtn = document.getElementById('convert-btn');
const progressWrap = document.getElementById('progress-wrap');
const progressMsg = document.getElementById('progress-msg');
const progressBar = document.getElementById('progress-bar');
const errorMsg = document.getElementById('error-msg');
const resultWrap = document.getElementById('result-wrap');

// Drop zone
dropZone.addEventListener('click', (e) => {
  if (e.target === removeFile) return;
  fileInput.click();
});
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const f = e.dataTransfer.files[0];
  if (f) setFile(f);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});
removeFile.addEventListener('click', (e) => {
  e.stopPropagation();
  clearFile();
});

function setFile(f) {
  selectedFile = f;
  fileNameDisplay.textContent = f.name;
  fileSelected.classList.add('show');
  dropZone.classList.add('has-file');
  document.getElementById('drop-icon').textContent = '✅';
  document.getElementById('drop-title').textContent = 'File selected';
  convertBtn.disabled = false;
  hideResults();
}
function clearFile() {
  selectedFile = null;
  fileSelected.classList.remove('show');
  dropZone.classList.remove('has-file');
  document.getElementById('drop-icon').textContent = '☁️';
  document.getElementById('drop-title').textContent = 'Drop your export here or click to browse';
  convertBtn.disabled = true;
  fileInput.value = '';
  hideResults();
}
function hideResults() {
  resultWrap.classList.remove('show');
  errorMsg.classList.remove('show');
  progressWrap.classList.remove('show');
}

// Format selector
document.querySelectorAll('.opt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.opt-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    selectedTarget = btn.dataset.target;
  });
});

// Convert
function fmt(n) {
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n/1000).toFixed(1) + 'K';
  return String(n);
}

convertBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  convertBtn.disabled = true;
  progressWrap.classList.add('show');
  progressMsg.textContent = 'Uploading…';
  progressBar.classList.add('indeterminate');
  errorMsg.classList.remove('show');
  resultWrap.classList.remove('show');

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('target', selectedTarget);

  try {
    progressMsg.textContent = 'Converting…';
    const resp = await fetch('/api/convert', { method: 'POST', body: formData });
    const data = await resp.json();

    progressBar.classList.remove('indeterminate');
    progressWrap.classList.remove('show');

    if (!resp.ok || data.error) {
      errorMsg.textContent = data.error || 'Conversion failed. Check your export file.';
      errorMsg.classList.add('show');
    } else {
      const stats = data.stats;
      document.getElementById('result-stats').innerHTML = `
        <div class="stat-mini"><div class="val">${fmt(stats.total_conversations)}</div><div class="lbl">Conversations</div></div>
        <div class="stat-mini"><div class="val">${fmt(stats.total_messages)}</div><div class="lbl">Messages</div></div>
        <div class="stat-mini"><div class="val">${fmt(stats.total_words)}</div><div class="lbl">Words</div></div>
      `;
      const dl = document.getElementById('download-link');
      dl.href = '/api/download/' + data.job_id;
      dl.download = 'open-migration-' + selectedTarget + '.zip';
      resultWrap.classList.add('show');
    }
  } catch (err) {
    progressWrap.classList.remove('show');
    errorMsg.textContent = 'Network error: ' + err.message;
    errorMsg.classList.add('show');
  }

  convertBtn.disabled = false;
});
</script>
</body>
</html>
"""


def create_app(port: int = 7337) -> "Flask":
    if not HAS_FLASK:
        raise ImportError(
            "Flask is required for the web UI.\n"
            "Install it with: pip install \"open-migration[web]\""
        )

    from open_migration.connectors.auto import AutoConnector
    from open_migration.exporters import EXPORTERS

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

    # In-memory job store: {job_id: Path(zip_output)}
    _jobs: dict[str, Path] = {}
    _lock = threading.Lock()

    @app.route("/")
    def index() -> str:
        return render_template_string(_WEB_UI, port=port)

    @app.route("/api/convert", methods=["POST"])
    def convert() -> tuple[Any, int]:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        target = request.form.get("target", "html")

        if target not in EXPORTERS:
            return jsonify({"error": f"Unknown target: {target}"}), 400

        # Save upload to temp dir
        work_dir = Path(tempfile.mkdtemp(prefix="omigrate_"))
        upload_path = work_dir / (file.filename or "upload.json")
        file.save(str(upload_path))

        try:
            graph = AutoConnector().extract(upload_path)
        except Exception as exc:
            return jsonify({"error": f"Could not parse export: {exc}"}), 422

        if not graph.nodes:
            return jsonify({"error": "No conversations found in this export."}), 422

        stats = graph.compute_stats()

        # Export to temp output dir, then zip it
        out_dir = work_dir / "output"
        EXPORTERS[target]().write(graph, out_dir)

        zip_path = work_dir / f"open-migration-{target}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in out_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(out_dir))

        # Store job
        import uuid
        job_id = uuid.uuid4().hex
        with _lock:
            _jobs[job_id] = zip_path

        return jsonify({
            "job_id": job_id,
            "stats": stats.to_dict(),
            "target": target,
        })

    @app.route("/api/download/<job_id>")
    def download(job_id: str) -> Any:
        with _lock:
            path = _jobs.get(job_id)
        if not path or not path.exists():
            return jsonify({"error": "Job not found or expired"}), 404
        return send_file(str(path), as_attachment=True, download_name=path.name)

    @app.route("/api/health")
    def health() -> Any:
        from open_migration import __version__
        return jsonify({"status": "ok", "version": __version__})

    return app


def run_server(port: int = 7337, no_open: bool = False) -> None:
    if not HAS_FLASK:
        raise ImportError(
            "Flask is required for the web UI.\n"
            "Install it with:  pip install \"open-migration[web]\""
        )

    app = create_app(port=port)

    if not no_open:
        def _open() -> None:
            time.sleep(0.8)
            import webbrowser
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open, daemon=True).start()

    print(f"\n  Open Migration Web UI")
    print(f"  Running at  http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
