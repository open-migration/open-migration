# Claude for OSS — Application

**Project:** Open Migration
**GitHub:** https://github.com/zoroabc2602-pixel/open-migration
**PyPI:** https://pypi.org/project/open-migration/
**Live demo:** https://open-migration.github.io/open-migration/demo/

---

## What does this project do?

Open Migration converts AI conversation exports (Claude, ChatGPT, Gemini) into usable formats: a self-contained searchable HTML archive, an Obsidian vault with proper frontmatter and wikilinks, or plain Markdown files.

One command:
```
omigrate convert --input conversations.json --target html --open
```

It also ships a local web UI (`omigrate serve`) for non-technical users — drag and drop your export, pick a format, download the result. No cloud. No accounts. No configuration.

---

## Why does this matter to Anthropic's ecosystem specifically?

Every serious Claude user eventually has the same problem: years of valuable conversations — debugging sessions, architecture decisions, research threads, creative drafts — are locked inside claude.ai with no practical way to use them.

Claude does have an export feature. But the output is a JSON file that requires a developer to make sense of. Most users can't search it, can't organize it, can't take it anywhere.

**Open Migration fixes this specifically for Claude users.** The Claude connector handles content blocks, tool use/tool result messages, and attachment metadata — formats that tools built only for ChatGPT handle badly or not at all.

The broader argument: data portability reduces lock-in anxiety, which increases long-term trust in Claude. Users who know they can leave are more likely to commit deeply to a tool. This is not an argument against Anthropic — it's an argument that users who feel ownership of their data become better, longer-term users.

---

## Concrete ecosystem dependency

There is no well-maintained, multi-platform, open-source tool that does this.

The existing tools I found:
- **chatgpt-to-markdown**: ChatGPT only, no Obsidian support, not actively maintained
- **ChatKeeper**: Paid for most features, no Claude support
- **Various single-platform scripts**: Fragmented, unmaintained, no common architecture

Open Migration is the first tool to:
1. Support Claude, ChatGPT, and Gemini in one package
2. Use a proper Knowledge Graph intermediate representation that makes adding new connectors ~150 lines of Python
3. Ship a local web UI that non-technical users can actually operate
4. Have zero required dependencies (works immediately after `pip install`)
5. Include merge functionality across sources

The architecture (source → Knowledge Graph → target) means the project scales with community contributions. Each new connector benefits all exporters. Each new exporter benefits all connectors. This is infrastructure, not a one-shot script.

---

## How Claude Max would accelerate this project

**1. Connector development**

Each new platform connector requires reading undocumented export formats, writing defensive parsers, and testing against real edge cases. These sessions are long — parsing a complex format like Notion's export requires hours of iterative refinement in a single context window. At Pro limits, these sessions get cut off mid-work. At Max, they'd complete.

**2. Community PR review**

When contributors open PRs for new connectors, reviewing them thoroughly (checking for defensive parsing, stable ID generation, edge cases, proper tests) is a multi-file analysis task. Claude Max enables doing this without losing context across files.

**3. Exporter quality**

The Obsidian and HTML exporters have significant complexity — the HTML exporter is a self-contained single-file app with its own JavaScript, search, and CSS. Iterating on it requires holding the full file in context while making surgical changes. This is exactly where Max's context headroom matters.

**4. Documentation**

Writing docs that are actually clear to non-technical users (the core audience for this tool) requires multiple revision passes with sustained context. Short sessions produce generic docs. Longer sessions produce docs that actually work.

---

## Current metrics

- **Stars:** Applied as a new project — see below
- **PyPI installs:** Early stage
- **Tests:** 38 passing, CI on Python 3.11/3.12 × Ubuntu/Windows/macOS
- **Languages:** Python
- **License:** Apache 2.0

---

## Note on the "new project" situation

This project is new. It doesn't have 5,000 stars or 1M downloads yet.

I'm applying under the ecosystem impact exception because:

1. The project solves a problem that affects a large fraction of Claude power users and has no good existing open-source solution
2. The architecture is designed for long-term community growth — the connector/exporter separation means the project compound-grows with each contribution
3. The tool directly benefits Claude's own ecosystem (portability = trust = retention)
4. The quality is production-grade: real tests, CI/CD, docs, zero dependencies, working web UI — not a prototype

I understand this is a judgment call on Anthropic's part. I'm making the case that the ecosystem impact is real and the engineering is serious, even without the star count to prove it yet.

---

## Project maintainer

This project is actively developed and will be maintained long-term. I use it myself — my own Claude conversation history is the primary test case.

GitHub: [your-username]
