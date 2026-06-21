# Roadmap

Community contributions welcome on any of these. See [contributing_a_connector.md](contributing_a_connector.md) to get started.

---

## Connectors (Sources)

### v0.2 — Priority

| Connector | Status | Notes |
|-----------|--------|-------|
| Perplexity | 🔲 Planned | No official export yet — API workaround |
| Microsoft Copilot | 🔲 Planned | Privacy dashboard export |
| Mistral Le Chat | 🔲 Planned | Account settings export |
| Google AI Studio | 🔲 Planned | Google Takeout |

### v0.3 — Knowledge bases

| Connector | Status | Notes |
|-----------|--------|-------|
| Notion | 🔲 Planned | Pages, databases, AI responses |
| Obsidian | 🔲 Planned | As a source (vault → graph) |
| Logseq | 🔲 Planned | As a source (graph DB → graph) |
| Roam Research | 🔲 Planned | JSON export |

### Future

| Connector | Status | Notes |
|-----------|--------|-------|
| Slack (personal export) | 🔲 Future | Business+ required for full history |
| Discord | 🔲 Future | Personal data request |
| Telegram | 🔲 Future | Export chat history |
| WhatsApp | 🔲 Future | Export chat → txt |

---

## Exporters (Targets)

### v0.2

| Exporter | Status | Notes |
|----------|--------|-------|
| Logseq | 🔲 Planned | EDN/markdown with graph links |
| Roam Research | 🔲 Planned | JSON import format |
| JSON-LD | 🔲 Planned | Structured data, schema.org vocab |

### v0.3

| Exporter | Status | Notes |
|----------|--------|-------|
| Notion | 🔲 Planned | Notion import format |
| Git repository | 🔲 Planned | One commit per conversation, chronological |
| SQLite FTS5 | 🔲 Planned | Local full-text search database |
| Anki | 🔲 Planned | Flashcard deck from Q&A conversations |

---

## Features

### v0.2

- [ ] Duplicate detection across sources (same conversation exported from two platforms)
- [ ] `omigrate stats` — standalone statistics dashboard with charts
- [ ] Progress file output for large exports (>10k conversations)
- [ ] GitHub Actions release automation

### v0.3

- [ ] Timeline / heatmap visualization in HTML output
- [ ] Tag extraction from conversation content
- [ ] Conversation search via SQLite FTS5 (local, offline)
- [ ] `omigrate diff` — compare two exports, show what changed

### Future

- [ ] GUI (Electron or Tauri wrapper for the web UI)
- [ ] Plugin system for custom connectors/exporters without forking
- [ ] Sync mode — incrementally update an existing vault

---

## Won't build (by design)

- **Cloud sync** — Open Migration stays local-first. No uploading your conversations to any server.
- **AI-powered summarization** — out of scope; other tools do this. We focus on faithful representation.
- **Platform write-back** — read-only is simpler, safer, and more maintainable.
