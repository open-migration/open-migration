<div align="center">

<img src="https://raw.githubusercontent.com/open-migration/open-migration/main/docs/assets/logo.svg" width="80" alt="Open Migration logo" />

# Open Migration

**Your AI conversations belong to you.**

[![CI](https://github.com/open-migration/open-migration/actions/workflows/ci.yml/badge.svg)](https://github.com/open-migration/open-migration/actions)
[![PyPI](https://img.shields.io/pypi/v/open-migration?color=%237c6af7)](https://pypi.org/project/open-migration/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://pypi.org/project/open-migration/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-38%20passing-brightgreen)](tests/)

[**Live Demo →**](https://open-migration.github.io/open-migration/demo/) · [Quick Start](#quick-start) · [Docs](docs/) · [Contributing](CONTRIBUTING.md)

</div>

---

You've spent months building knowledge with Claude, ChatGPT, and Gemini.

Debugging sessions. Architecture decisions. Research threads. Writing drafts. Ideas you'd never have remembered on your own.

**All of it is locked inside platforms you don't control.**

Export your ChatGPT history and you get a ZIP with a JSON file you can't read.  
Export from Claude and you get the same.  
The relationships, the context, the searchability — gone.

**Open Migration converts your AI export files into formats you can actually use:**
a beautiful searchable HTML archive, an Obsidian vault with wikilinks, or plain Markdown files.
One command. Zero cloud. Your data stays on your machine.

---

## Demo

**[→ Open the live demo in your browser](https://open-migration.github.io/open-migration/demo/)**  
*(No install needed — this is real output generated from sample conversations)*

Or run it on your own data in 60 seconds:

```bash
pip install open-migration
omigrate convert --input conversations.json --target html --open
```

---

## Quick Start

### Step 1 — Get your export

| Platform | Where to export |
|----------|----------------|
| 🤖 **ChatGPT** | chatgpt.com → Settings → Data controls → Export data |
| ⚡ **Claude** | claude.ai → Settings → Privacy → Export Data |
| ✨ **Gemini** | [takeout.google.com](https://takeout.google.com) → Gemini Apps Activity |

### Step 2 — Install

```bash
pip install open-migration
```

No dependencies. Works on Windows, macOS, Linux. Python 3.11+.

### Step 3 — Convert

```bash
# Auto-detect format, produce searchable HTML site (recommended)
omigrate convert --input conversations.json --open

# Obsidian vault
omigrate convert --input chatgpt_export.zip --target obsidian --output ./my-vault/

# Plain Markdown
omigrate convert --input claude_export.zip --target markdown --output ./notes/

# Merge ChatGPT + Claude + Gemini into one archive
omigrate merge --inputs chatgpt.json claude.zip gemini_takeout/ --target html --open

# Web UI — drag and drop in your browser
pip install "open-migration[web]"
omigrate serve
```

---

## What you get

### HTML Archive (default)

A single self-contained `.html` file. Open it in any browser.

- Full-text search across all conversations
- Filter by source (ChatGPT / Claude / Gemini)
- Stats bar: total conversations, messages, words, date range
- Syntax-highlighted code blocks
- Dark theme, zero external dependencies
- Works completely offline

### Obsidian Vault

A proper vault you can open directly in Obsidian.

- YAML frontmatter with date, source, word count, tags
- Obsidian callout blocks for each message role
- `Index.md` with full conversation list grouped by source
- Wikilinks between notes
- `.obsidian/` config pre-configured

### Markdown

Plain `.md` files. One per conversation, plus a `README.md` index.  
Works with any editor, any static site generator, any version control system.

---

## Web UI

For non-technical users (or if you just want drag-and-drop):

```bash
pip install "open-migration[web]"
omigrate serve
```

Opens at `http://localhost:7337`. Drag your export file, pick a format, download the result. Your data never leaves your machine — the server only runs locally.

---

## Architecture

Open Migration uses a three-layer pipeline designed for community extensibility:

```
Input file(s)
     │
     ▼
┌─────────────┐
│  Connector  │  Reads one platform's export format (~150 lines each)
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Knowledge Graph  │  Platform-neutral: Nodes + Edges + Metadata
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│  Exporter   │  Writes to target format (~200 lines each)
└─────────────┘
```

The Knowledge Graph is the key insight: every platform is just nodes with relationships between them. Decoupling sources from targets means **adding a new connector doesn't require changing any exporter**, and vice versa.

**Adding a new connector is ~150 lines of Python.** See [docs/contributing_a_connector.md](docs/contributing_a_connector.md).

---

## Python API

```python
from open_migration.connectors import ChatGPTConnector, ClaudeConnector
from open_migration.exporters import HtmlSiteExporter, ObsidianExporter
from pathlib import Path

# Parse
graph = ChatGPTConnector().extract(Path("conversations.json"))

# Inspect
stats = graph.compute_stats()
print(f"{stats.total_conversations} conversations, {stats.total_words:,} words")

for conv in graph.by_type("conversation"):
    messages = graph.children(conv.id, "contains")
    print(f"  {conv.title}: {len(messages)} messages ({conv.source})")

# Export
HtmlSiteExporter().write(graph, Path("./archive"))
ObsidianExporter().write(graph, Path("./vault"))
```

---

## Supported platforms

| Source | Format | Status |
|--------|--------|--------|
| ChatGPT | `conversations.json` / `.zip` | ✅ Full |
| Claude | `conversations.json` / `.zip` | ✅ Full — incl. content blocks, tool use |
| Gemini | Google Takeout directory / `.zip` | ✅ Full |
| Perplexity | — | 🗓 Planned |
| Copilot | — | 🗓 Planned |
| Mistral Le Chat | — | 🗓 Planned |
| Notion | — | 🗓 Planned |

| Target | Description | Status |
|--------|-------------|--------|
| HTML site | Self-contained, searchable, offline | ✅ |
| Obsidian vault | Frontmatter, callouts, wikilinks | ✅ |
| Markdown | Plain files, any editor | ✅ |
| Logseq | — | 🗓 Planned |
| Roam Research | — | 🗓 Planned |
| JSON-LD | Structured data | 🗓 Planned |

---

## Comparison

| Feature | open-migration | chatgpt-to-markdown | ChatKeeper |
|---------|---------------|--------------------|-|
| ChatGPT | ✅ | ✅ | ✅ |
| Claude | ✅ | ❌ | ❌ |
| Gemini | ✅ | ❌ | ❌ |
| Merge multiple sources | ✅ | ❌ | ❌ |
| HTML archive with search | ✅ | ❌ | ✅ (paid) |
| Obsidian vault | ✅ | partial | ❌ |
| Web UI | ✅ | ❌ | ✅ (paid) |
| Local-first, no cloud | ✅ | ✅ | ❌ |
| Zero required dependencies | ✅ | ❌ | ❌ |
| Open source | ✅ | ✅ | ❌ |
| Extensible (add connectors) | ✅ | ❌ | ❌ |

---

## CLI reference

```
omigrate convert   Convert a single export file
  -i, --input      Export file, directory, or .zip (required)
  -s, --source     chatgpt | claude | gemini | auto (default: auto)
  -t, --target     html | obsidian | markdown (default: html)
  -o, --output     Output directory (default: ./open-migration-output/)
  --open           Open output in browser/finder when done
  --stats          Show stats only, don't export

omigrate merge     Merge multiple exports into one archive
  -i, --inputs     Two or more export files/directories
  -t, --target     Output format (default: html)
  -o, --output     Output directory
  --open           Open when done

omigrate serve     Start local web UI
  --port           Port number (default: 7337)
  --no-open        Don't auto-open browser

omigrate --version Print version
```

---

## Contributing

The most valuable contributions are new connectors and exporters.

- **New connector** — adds support for a new AI platform as a source
- **New exporter** — adds support for a new target format

Both are small, focused, independently testable. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/contributing_a_connector.md](docs/contributing_a_connector.md).

Good first issues are labelled `good first issue` on the issues page.

---

## Why this exists

Data portability is not a nice-to-have. It's a prerequisite for trust.

When your AI conversations are locked in a platform, you make a trade: get the convenience of the tool in exchange for permanent dependency. You can't search your own history the way you want. You can't take your knowledge base elsewhere. You can't even reliably back it up.

Open Migration is infrastructure for the opposite of that. The goal is a connector for every major AI platform and an exporter for every major knowledge management tool — community-maintained, permanently free and open source.

---

## License

[Apache 2.0](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

**Built by the community, for everyone who uses AI.**

If this saved you time, a ⭐ helps others find it.

[Report a bug](https://github.com/open-migration/open-migration/issues/new?template=bug_report.yml) · [Request a connector](https://github.com/open-migration/open-migration/issues/new?template=connector_request.yml) · [Read the docs](docs/)

</div>
