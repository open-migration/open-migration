# Changelog

All notable changes to Open Migration are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-06-19

### Added

**Core**
- Universal Knowledge Graph (`graph.py`) — platform-neutral node/edge representation for any AI conversation
- `GraphStats` — conversation count, message count, word count, date range, longest conversation
- Stable content-addressed node IDs (`stable_id`) — deterministic, collision-resistant

**Connectors**
- `ChatGPTConnector` — parses `conversations.json` (bare JSON, ZIP, directory); handles tree-walk message ordering, multi-part content, code blocks, attachments
- `ClaudeConnector` — parses Claude.ai exports; supports both flat-text and content-block message formats, tool use/tool result blocks, attachment metadata
- `GeminiConnector` — parses Google Takeout Gemini exports; supports structured message format and activity record format
- `AutoConnector` — heuristic format detection (filename, content sniffing); falls back through all connectors

**Exporters**
- `HtmlSiteExporter` — single self-contained HTML file; full-text search, source filter, dark-theme conversation viewer with syntax-highlighted code blocks, stats bar, zero external dependencies
- `ObsidianExporter` — Obsidian vault with YAML frontmatter, Obsidian callout blocks, wikilinks, `Index.md`, `.obsidian/` config
- `MarkdownExporter` — plain `.md` files, one per conversation, with `README.md` index table

**CLI (`omigrate`)**
- `omigrate convert` — convert a single export; `--source`, `--target`, `--output`, `--stats`, `--open`
- `omigrate merge` — merge multiple exports from different sources into one unified archive
- `omigrate serve` — local web UI with drag-and-drop upload, format selection, real-time progress, download link (requires `pip install "open-migration[web]"`)
- Legacy flag style (`omigrate --input X --target Y`) supported for backwards compatibility

**Web UI**
- Flask-based local server (`omigrate serve`) with beautiful dark-themed drag-and-drop interface
- Auto-opens browser on start
- Returns ZIP download of converted output

**Packaging**
- Zero required dependencies for core CLI
- Optional `rich` for beautiful terminal output
- Optional `flask` for web UI (`pip install "open-migration[web]"`)
- `omigrate` console script entry point
- `python -m open_migration` also works

**Tests**
- 38 tests across graph model, all connectors, all exporters, all CLI commands
- Cross-platform CI matrix: Python 3.11/3.12 × Ubuntu/Windows/macOS

---

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for planned connectors and exporters.
