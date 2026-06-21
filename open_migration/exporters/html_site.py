"""
HTML Site Exporter.
Generates a beautiful, self-contained single-file HTML archive of all your
AI conversations — searchable, filterable, and openable in any browser.
Zero dependencies. No server needed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any

from open_migration.connectors.base import Exporter
from open_migration.graph import KnowledgeGraph, Node


def _role_label(role: str) -> str:
    return {
        "human": "You", "user": "You",
        "assistant": "AI", "claude": "AI", "model": "AI",
        "system": "System", "tool": "Tool",
    }.get(str(role).lower(), str(role).title())


def _role_class(role: str) -> str:
    r = str(role).lower()
    if r in ("human", "user"):
        return "user"
    if r in ("assistant", "claude", "model"):
        return "assistant"
    return "system"


def _safe_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _source_icon(source: str | None) -> str:
    icons = {
        "chatgpt": "🤖",
        "claude": "⚡",
        "gemini": "✨",
    }
    return icons.get(str(source).lower(), "💬")


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso[:10]


def _fmt_date_long(iso: str | None) -> str:
    if not iso:
        return "Unknown date"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception:
        return iso


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def _markdown_to_html(text: str) -> str:
    """
    Minimal Markdown→HTML for conversation bodies.
    Handles: code blocks, inline code, bold, italic, links, headers, line breaks.
    """
    # Fenced code blocks ```lang\n...\n```
    def replace_codeblock(m: re.Match) -> str:
        lang = _escape_html(m.group(1).strip())
        code = _escape_html(m.group(2))
        label = f'<span class="code-lang">{lang}</span>' if lang else ""
        return f'<div class="code-block">{label}<pre><code>{code}</code></pre></div>'

    text = re.sub(r"```(\w*)\n?(.*?)```", replace_codeblock, text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r"`([^`\n]+)`", lambda m: f'<code class="inline-code">{_escape_html(m.group(1))}</code>', text)

    # Escape remaining HTML (after code blocks are done)
    # Already safe because we haven't escaped the non-code text yet —
    # but we need to escape everything we haven't converted yet.
    # We do this per-line below.

    lines = text.split("\n")
    out: list[str] = []
    in_list = False

    for line in lines:
        # Check if line contains our placeholder HTML (code blocks)
        if line.strip().startswith('<div class="code-block">') or line.strip().startswith('</div>'):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(line)
            continue

        # Headings
        if line.startswith("### "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h4>{_escape_html(line[4:])}</h4>")
            continue
        if line.startswith("## "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h3>{_escape_html(line[3:])}</h3>")
            continue
        if line.startswith("# "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h2>{_escape_html(line[2:])}</h2>")
            continue

        # Bullet lists
        if re.match(r"^[-*+] ", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            content = _inline_format(_escape_html(line[2:]))
            out.append(f"<li>{content}</li>")
            continue
        elif in_list and line.strip():
            out.append("</ul>")
            in_list = False

        # Numbered lists
        if re.match(r"^\d+\. ", line):
            content = _inline_format(_escape_html(re.sub(r"^\d+\. ", "", line)))
            out.append(f"<p>{content}</p>")
            continue

        # Horizontal rule
        if re.match(r"^---+$", line.strip()):
            if in_list: out.append("</ul>"); in_list = False
            out.append("<hr>")
            continue

        # Empty line = paragraph break
        if not line.strip():
            if in_list: out.append("</ul>"); in_list = False
            out.append("<br>")
            continue

        out.append(f"<p>{_inline_format(_escape_html(line))}</p>")

    if in_list:
        out.append("</ul>")

    return "\n".join(out)


def _inline_format(text: str) -> str:
    """Apply bold, italic, link formatting to already-escaped text."""
    # Bold **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic *text* or _text_
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_([^_]+)_", r"<em>\1</em>", text)
    # Links [text](url) — already escaped so &amp; etc.
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


# ── Main HTML Template ──────────────────────────────────────────────────────

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<style>
:root {{
  --bg: #0a0a0f;
  --surface: #111118;
  --surface2: #18181f;
  --surface3: #1e1e28;
  --border: #2a2a38;
  --border2: #333344;
  --text: #e0e0ef;
  --text2: #9090a8;
  --text3: #5a5a72;
  --accent: #7c6af7;
  --accent2: #5b4de0;
  --accent-glow: rgba(124,106,247,0.15);
  --user-bg: #1a1a2e;
  --user-border: #2a2a4e;
  --ai-bg: #0f1a1a;
  --ai-border: #1a2f2f;
  --sys-bg: #1a1a14;
  --sys-border: #2f2f1a;
  --green: #4ade80;
  --blue: #60a5fa;
  --purple: #c084fc;
  --orange: #fb923c;
  --red: #f87171;
  --radius: 10px;
  --sidebar-w: 320px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ font-size: 15px; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  line-height: 1.6;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}}

/* ── Top bar ── */
#topbar {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  height: 56px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  z-index: 10;
}}
#topbar .logo {{
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 8px;
}}
#topbar .logo span {{
  background: linear-gradient(135deg, var(--accent), #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
#search-wrap {{
  flex: 1;
  max-width: 480px;
  position: relative;
}}
#search {{
  width: 100%;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 0.9rem;
  padding: 8px 14px 8px 36px;
  outline: none;
  transition: border-color 0.2s;
}}
#search:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }}
#search::placeholder {{ color: var(--text3); }}
.search-icon {{
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text3);
  font-size: 0.85rem;
  pointer-events: none;
}}
#topbar .stats-pill {{
  font-size: 0.78rem;
  color: var(--text2);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 100px;
  padding: 4px 12px;
  white-space: nowrap;
}}

/* ── Layout ── */
#layout {{
  display: flex;
  flex: 1;
  overflow: hidden;
}}

/* ── Sidebar ── */
#sidebar {{
  width: var(--sidebar-w);
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
#sidebar-filters {{
  padding: 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}}
.filter-btn {{
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text2);
  border-radius: 100px;
  padding: 4px 12px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}}
.filter-btn:hover, .filter-btn.active {{
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}}
#conv-count {{
  padding: 8px 12px;
  font-size: 0.75rem;
  color: var(--text3);
  border-bottom: 1px solid var(--border);
}}
#conv-list {{
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}}
#conv-list::-webkit-scrollbar {{ width: 4px; }}
#conv-list::-webkit-scrollbar-track {{ background: transparent; }}
#conv-list::-webkit-scrollbar-thumb {{ background: var(--border2); border-radius: 4px; }}

.conv-item {{
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.1s;
  position: relative;
}}
.conv-item:hover {{ background: var(--surface2); }}
.conv-item.active {{ background: var(--surface3); }}
.conv-item.active::before {{
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--accent);
  border-radius: 0 2px 2px 0;
}}
.conv-title {{
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text);
  line-height: 1.4;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}}
.conv-meta {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
  color: var(--text3);
}}
.conv-source {{
  font-size: 0.7rem;
  background: var(--surface3);
  border: 1px solid var(--border2);
  border-radius: 4px;
  padding: 1px 6px;
  color: var(--text2);
}}

/* ── Main content ── */
#main {{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}}
#conv-header {{
  padding: 20px 28px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}}
#conv-header h1 {{
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
  line-height: 1.3;
}}
#conv-header .meta-row {{
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.78rem;
  color: var(--text2);
}}
.meta-badge {{
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.72rem;
  color: var(--text2);
}}
#messages {{
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px;
}}
#messages::-webkit-scrollbar {{ width: 5px; }}
#messages::-webkit-scrollbar-track {{ background: transparent; }}
#messages::-webkit-scrollbar-thumb {{ background: var(--border2); border-radius: 4px; }}

.message {{
  margin-bottom: 20px;
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid transparent;
  animation: fadeIn 0.2s ease;
}}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; }} }}

.message.user {{ background: var(--user-bg); border-color: var(--user-border); }}
.message.assistant {{ background: var(--ai-bg); border-color: var(--ai-border); }}
.message.system {{ background: var(--sys-bg); border-color: var(--sys-border); opacity: 0.7; }}

.msg-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  font-size: 0.78rem;
  font-weight: 600;
}}
.msg-header .role {{
  display: flex;
  align-items: center;
  gap: 5px;
}}
.role-dot {{
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.message.user .role-dot {{ background: var(--blue); }}
.message.assistant .role-dot {{ background: var(--green); }}
.message.system .role-dot {{ background: var(--orange); }}
.message.user .msg-header {{ color: #93c5fd; }}
.message.assistant .msg-header {{ color: #86efac; }}
.message.system .msg-header {{ color: #fbbf24; }}
.msg-time {{ margin-left: auto; color: var(--text3); font-weight: 400; font-size: 0.72rem; }}

.msg-body {{
  padding: 14px 16px;
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--text);
}}
.msg-body p {{ margin-bottom: 8px; }}
.msg-body p:last-child {{ margin-bottom: 0; }}
.msg-body h2, .msg-body h3, .msg-body h4 {{
  margin: 14px 0 8px;
  color: var(--text);
  font-weight: 600;
}}
.msg-body ul {{ margin: 8px 0 8px 20px; }}
.msg-body li {{ margin-bottom: 4px; }}
.msg-body hr {{ border: none; border-top: 1px solid var(--border); margin: 12px 0; }}
.msg-body br {{ display: block; content: ''; margin-bottom: 4px; }}
.msg-body strong {{ color: var(--text); font-weight: 600; }}
.msg-body em {{ color: var(--text2); font-style: italic; }}
.msg-body a {{ color: var(--accent); text-decoration: none; }}
.msg-body a:hover {{ text-decoration: underline; }}

.code-block {{
  margin: 10px 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border2);
  background: #0d0d18;
  position: relative;
}}
.code-block pre {{
  padding: 14px 16px;
  overflow-x: auto;
  font-size: 0.82rem;
  line-height: 1.5;
  font-family: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', 'Courier New', monospace;
}}
.code-block pre::-webkit-scrollbar {{ height: 3px; }}
.code-block pre::-webkit-scrollbar-thumb {{ background: var(--border2); }}
.code-lang {{
  display: block;
  padding: 5px 14px;
  font-size: 0.7rem;
  font-family: monospace;
  color: var(--accent);
  background: rgba(124,106,247,0.08);
  border-bottom: 1px solid var(--border);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.inline-code {{
  background: var(--surface3);
  border: 1px solid var(--border2);
  border-radius: 4px;
  padding: 1px 5px;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  font-size: 0.82em;
  color: #c4b5fd;
}}

.attachment-list {{
  margin: 10px 0 0;
  padding: 10px 14px;
  background: var(--surface3);
  border-radius: 6px;
  border: 1px solid var(--border2);
}}
.attachment-list p {{ margin-bottom: 5px; font-size: 0.78rem; color: var(--text3); font-weight: 600; }}
.attachment-list span {{
  display: inline-block;
  margin: 2px 4px 2px 0;
  padding: 2px 8px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 0.72rem;
  color: var(--text2);
}}

/* ── Empty / welcome state ── */
#welcome {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 40px;
  text-align: center;
}}
#welcome .big-icon {{ font-size: 3rem; margin-bottom: 16px; }}
#welcome h2 {{ font-size: 1.3rem; color: var(--text); margin-bottom: 8px; font-weight: 600; }}
#welcome p {{ font-size: 0.88rem; color: var(--text2); max-width: 360px; line-height: 1.6; }}

/* ── Stats dashboard ── */
#stats-bar {{
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
  overflow-x: auto;
}}
.stat-card {{
  padding: 12px 24px;
  border-right: 1px solid var(--border);
  flex-shrink: 0;
}}
.stat-card .val {{
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
  margin-bottom: 3px;
  font-variant-numeric: tabular-nums;
}}
.stat-card .lbl {{
  font-size: 0.7rem;
  color: var(--text3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

/* ── No results ── */
#no-results {{
  padding: 32px;
  text-align: center;
  color: var(--text3);
  font-size: 0.88rem;
}}

/* ── Scrollbar global ── */
* {{ scrollbar-width: thin; scrollbar-color: var(--border2) transparent; }}

@media (max-width: 700px) {{
  :root {{ --sidebar-w: 100vw; }}
  #layout {{ flex-direction: column; }}
  #sidebar {{ width: 100%; height: 220px; }}
  body {{ overflow: auto; }}
}}
</style>
</head>
<body>

<div id="topbar">
  <div class="logo">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>
    </svg>
    <span>Open Migration</span> Archive
  </div>
  <div id="search-wrap">
    <span class="search-icon">&#x2315;</span>
    <input id="search" type="search" placeholder="Search conversations…" autocomplete="off">
  </div>
  <div class="stats-pill" id="topbar-pill"></div>
</div>

<div id="stats-bar">
  <div class="stat-card"><div class="val" id="s-convs">—</div><div class="lbl">Conversations</div></div>
  <div class="stat-card"><div class="val" id="s-msgs">—</div><div class="lbl">Messages</div></div>
  <div class="stat-card"><div class="val" id="s-words">—</div><div class="lbl">Words</div></div>
  <div class="stat-card"><div class="val" id="s-sources">—</div><div class="lbl">Sources</div></div>
  <div class="stat-card"><div class="val" id="s-daterange">—</div><div class="lbl">Date Range</div></div>
</div>

<div id="layout">
  <div id="sidebar">
    <div id="sidebar-filters"></div>
    <div id="conv-count"></div>
    <div id="conv-list"></div>
  </div>
  <div id="main">
    <div id="welcome">
      <div class="big-icon">💬</div>
      <h2>Select a conversation</h2>
      <p>Your AI conversations are archived here. Browse the list on the left or search above.</p>
    </div>
    <div id="conv-view" style="display:none;flex-direction:column;flex:1;overflow:hidden;">
      <div id="conv-header">
        <h1 id="conv-title"></h1>
        <div class="meta-row" id="conv-meta"></div>
      </div>
      <div id="messages"></div>
    </div>
  </div>
</div>

<script>
const RAW = {data_json};
const STATS = {stats_json};

// ── Format numbers ──────────────────────────────────────────────────────────
function fmt(n) {{
  if (n >= 1_000_000) return (n/1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n/1_000).toFixed(1) + 'K';
  return String(n);
}}

function fmtDate(iso) {{
  if (!iso) return '';
  try {{
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', {{month: 'short', day: 'numeric', year: 'numeric'}});
  }} catch(e) {{ return iso.slice(0,10); }}
}}

function fmtDateLong(iso) {{
  if (!iso) return 'Unknown date';
  try {{
    const d = new Date(iso);
    return d.toLocaleString('en-US', {{
      month: 'long', day: 'numeric', year: 'numeric',
      hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
    }});
  }} catch(e) {{ return iso; }}
}}

// ── Populate stats bar ──────────────────────────────────────────────────────
(function() {{
  document.getElementById('s-convs').textContent = fmt(STATS.total_conversations);
  document.getElementById('s-msgs').textContent = fmt(STATS.total_messages);
  document.getElementById('s-words').textContent = fmt(STATS.total_words);
  const sources = Object.keys(STATS.sources || {{}}).join(', ') || '—';
  document.getElementById('s-sources').textContent = sources;
  const dr = STATS.date_range || [];
  const drText = (dr[0] && dr[1]) ? fmtDate(dr[0]) + ' – ' + fmtDate(dr[1]) : '—';
  document.getElementById('s-daterange').textContent = drText;
  document.getElementById('topbar-pill').textContent =
    `${{STATS.total_conversations}} convs · ${{fmt(STATS.total_words)}} words`;
}})();

// ── Build conversation index ────────────────────────────────────────────────
const nodeMap = {{}};
RAW.nodes.forEach(n => nodeMap[n.id] = n);

const edgesByParent = {{}};  // from_id → [{{to_id, order, type}}]
RAW.edges.forEach(e => {{
  if (!edgesByParent[e.from_id]) edgesByParent[e.from_id] = [];
  edgesByParent[e.from_id].push(e);
}});

function getChildren(parentId, edgeType) {{
  const edges = (edgesByParent[parentId] || [])
    .filter(e => !edgeType || e.type === edgeType)
    .sort((a,b) => (a.metadata.order||0) - (b.metadata.order||0));
  return edges.map(e => nodeMap[e.to_id]).filter(Boolean);
}}

const conversations = RAW.nodes
  .filter(n => n.type === 'conversation')
  .sort((a,b) => {{
    const da = a.created_at || ''; const db = b.created_at || '';
    return db.localeCompare(da);
  }});

// ── Filter state ─────────────────────────────────────────────────────────────
let activeSource = 'all';
let searchQuery = '';
let activeConvId = null;

// ── Sidebar filters ──────────────────────────────────────────────────────────
const sources = ['all', ...new Set(conversations.map(c => c.source).filter(Boolean))];
const filterWrap = document.getElementById('sidebar-filters');
sources.forEach(src => {{
  const btn = document.createElement('button');
  btn.className = 'filter-btn' + (src === 'all' ? ' active' : '');
  const icons = {{chatgpt:'🤖', claude:'⚡', gemini:'✨', all:'💬'}};
  btn.textContent = (icons[src] || '💬') + ' ' + (src === 'all' ? 'All' : src.charAt(0).toUpperCase() + src.slice(1));
  btn.dataset.src = src;
  btn.addEventListener('click', () => {{
    activeSource = src;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b.dataset.src === src));
    renderList();
  }});
  filterWrap.appendChild(btn);
}});

// ── Search ───────────────────────────────────────────────────────────────────
const searchEl = document.getElementById('search');
let searchTimer;
searchEl.addEventListener('input', () => {{
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {{
    searchQuery = searchEl.value.toLowerCase().trim();
    renderList();
  }}, 180);
}});

// ── List rendering ────────────────────────────────────────────────────────────
function scoreConv(conv) {{
  if (!searchQuery) return true;
  const title = (conv.title || '').toLowerCase();
  if (title.includes(searchQuery)) return true;
  const msgs = getChildren(conv.id, 'contains');
  return msgs.some(m => (m.body || '').toLowerCase().includes(searchQuery));
}}

function renderList() {{
  const list = document.getElementById('conv-list');
  const countEl = document.getElementById('conv-count');
  list.innerHTML = '';
  const filtered = conversations.filter(c => {{
    if (activeSource !== 'all' && c.source !== activeSource) return false;
    return scoreConv(c);
  }});
  countEl.textContent = filtered.length === conversations.length
    ? `${{conversations.length}} conversations`
    : `${{filtered.length}} of ${{conversations.length}} conversations`;

  if (filtered.length === 0) {{
    list.innerHTML = '<div id="no-results">No conversations match your search.</div>';
    return;
  }}

  filtered.forEach(conv => {{
    const msgs = getChildren(conv.id, 'contains');
    const preview = msgs[0]?.body?.trim().slice(0, 120) || 'No preview';
    const icons = {{chatgpt:'🤖', claude:'⚡', gemini:'✨'}};
    const icon = icons[conv.source] || '💬';

    const item = document.createElement('div');
    item.className = 'conv-item' + (conv.id === activeConvId ? ' active' : '');
    item.dataset.id = conv.id;
    item.innerHTML = `
      <div class="conv-title">${{escHtml(conv.title || 'Untitled')}}</div>
      <div class="conv-meta">
        <span class="conv-source">${{icon}} ${{conv.source || 'unknown'}}</span>
        <span>${{fmtDate(conv.created_at)}}</span>
        <span>·</span>
        <span>${{msgs.length}} msg${{msgs.length !== 1 ? 's' : ''}}</span>
      </div>
    `;
    item.addEventListener('click', () => openConv(conv.id));
    list.appendChild(item);
  }});
}}

// ── Conversation viewer ────────────────────────────────────────────────────────
function roleLabel(role) {{
  const map = {{human:'You',user:'You',assistant:'AI',claude:'AI',model:'AI',system:'System',tool:'Tool'}};
  return map[(role||'').toLowerCase()] || (role||'Unknown');
}}
function roleClass(role) {{
  const r = (role||'').toLowerCase();
  if (['human','user'].includes(r)) return 'user';
  if (['assistant','claude','model'].includes(r)) return 'assistant';
  return 'system';
}}

function escHtml(s) {{
  return String(s||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}}

function openConv(convId) {{
  activeConvId = convId;
  const conv = nodeMap[convId];
  if (!conv) return;

  document.querySelectorAll('.conv-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === convId));

  const messages = getChildren(convId, 'contains');
  document.getElementById('welcome').style.display = 'none';
  const view = document.getElementById('conv-view');
  view.style.display = 'flex';

  document.getElementById('conv-title').textContent = conv.title || 'Untitled conversation';

  const icons = {{chatgpt:'🤖', claude:'⚡', gemini:'✨'}};
  const icon = icons[conv.source] || '💬';
  document.getElementById('conv-meta').innerHTML = `
    <span class="meta-badge">${{icon}} ${{(conv.source||'unknown').charAt(0).toUpperCase()+(conv.source||'').slice(1)}}</span>
    <span>${{fmtDateLong(conv.created_at)}}</span>
    <span class="meta-badge">${{messages.length}} messages</span>
  `;

  const msgContainer = document.getElementById('messages');
  msgContainer.innerHTML = '';
  messages.forEach(msg => {{
    const role = msg.metadata?.role || 'unknown';
    const rc = roleClass(role);
    const rl = roleLabel(role);
    const time = fmtDate(msg.created_at);

    const attachHtml = msg.attachments?.length
      ? `<div class="attachment-list">
          <p>📎 Attachments</p>
          ${{msg.attachments.map(a => `<span>${{escHtml(a.name)}}</span>`).join('')}}
        </div>` : '';

    const div = document.createElement('div');
    div.className = `message ${{rc}}`;
    div.innerHTML = `
      <div class="msg-header">
        <span class="role"><span class="role-dot"></span>${{rl}}</span>
        ${{time ? `<span class="msg-time">${{time}}</span>` : ''}}
      </div>
      <div class="msg-body">
        ${{renderBody(msg.body || '')}}
        ${{attachHtml}}
      </div>
    `;
    msgContainer.appendChild(div);
  }});
  msgContainer.scrollTop = 0;
}}

function renderBody(text) {{
  // Very lightweight markdown→HTML
  // Code blocks
  text = text.replace(/```(\\w*)\\n?([\\s\\S]*?)```/g, (_, lang, code) => {{
    const l = lang ? `<span class="code-lang">${{escHtml(lang)}}</span>` : '';
    return `<div class="code-block">${{l}}<pre><code>${{escHtml(code.trim())}}</code></pre></div>`;
  }});
  // Inline code (only outside code blocks)
  text = text.replace(/`([^`\\n]+)`/g, (_, c) => `<code class="inline-code">${{escHtml(c)}}</code>`);
  // Split into lines for paragraph/heading/list handling
  const lines = text.split('\\n');
  let html = '';
  let inPre = false;
  for (let i = 0; i < lines.length; i++) {{
    const line = lines[i];
    if (line.includes('<div class="code-block">')) {{ inPre = true; html += line + '\\n'; continue; }}
    if (inPre) {{
      html += line + '\\n';
      if (line.includes('</div>')) inPre = false;
      continue;
    }}
    if (line.startsWith('### ')) {{ html += `<h4>${{inlineFormat(escHtml(line.slice(4)))}}</h4>`; continue; }}
    if (line.startsWith('## ')) {{ html += `<h3>${{inlineFormat(escHtml(line.slice(3)))}}</h3>`; continue; }}
    if (line.startsWith('# ')) {{ html += `<h2>${{inlineFormat(escHtml(line.slice(2)))}}</h2>`; continue; }}
    if (/^[-*+] /.test(line)) {{ html += `<li>${{inlineFormat(escHtml(line.slice(2)))}}</li>`; continue; }}
    if (/^---+$/.test(line.trim())) {{ html += '<hr>'; continue; }}
    if (!line.trim()) {{ html += '<br>'; continue; }}
    html += `<p>${{inlineFormat(escHtml(line))}}</p>`;
  }}
  return html;
}}

function inlineFormat(s) {{
  s = s.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
  s = s.replace(/__(.+?)__/g, '<strong>$1</strong>');
  s = s.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
  s = s.replace(/_([^_]+)_/g, '<em>$1</em>');
  s = s.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return s;
}}

// ── Init ─────────────────────────────────────────────────────────────────────
renderList();
if (conversations.length > 0) {{
  openConv(conversations[0].id);
}}
</script>
</body>
</html>
"""


class HtmlSiteExporter(Exporter):
    """
    Export all conversations to a single self-contained HTML file.
    Open it in any browser — no server, no install, works offline.
    """
    name = "html"

    def __init__(self, filename: str = "archive.html") -> None:
        self.filename = filename

    def write(self, graph: KnowledgeGraph, output_path: Path) -> None:
        output_path.mkdir(parents=True, exist_ok=True)

        stats = graph.compute_stats()
        graph_dict = graph.to_dict()

        # Slimmed-down data for embedding in HTML
        # (we don't need all fields, just what the UI uses)
        slim_nodes = []
        for node in graph.nodes.values():
            slim_nodes.append({
                "id": node.id,
                "type": node.type,
                "title": node.title,
                "body": node.body or "",
                "created_at": node.created_at,
                "updated_at": node.updated_at,
                "source": node.source,
                "source_id": node.source_id,
                "metadata": node.metadata,
                "attachments": [
                    {"name": a.name, "mime_type": a.mime_type}
                    for a in node.attachments
                ],
            })

        slim_edges = [
            {
                "id": e.id,
                "type": e.type,
                "from_id": e.from_id,
                "to_id": e.to_id,
                "metadata": e.metadata,
            }
            for e in graph.edges.values()
        ]

        data = {"nodes": slim_nodes, "edges": slim_edges}

        sources = list(set(
            n.source for n in graph.nodes.values()
            if n.type == "conversation" and n.source
        ))
        page_title = f"Open Migration Archive — {stats.total_conversations} conversations"

        html = _HTML_TEMPLATE.format(
            page_title=page_title,
            data_json=json.dumps(data, ensure_ascii=False),
            stats_json=json.dumps(stats.to_dict(), ensure_ascii=False),
        )

        out_file = output_path / self.filename
        out_file.write_text(html, encoding="utf-8")

        # Also write sidecar graph JSON
        graph.write_json(str(output_path / "open-migration.graph.json"))
