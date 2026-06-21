# Launch Strategy

This document is for the maintainer — not part of the public docs.

## Goal

Get enough visibility for the Claude OSS program application and build
a sustainable community around the project.

---

## Launch checklist (do all in one 2-hour window)

### Before launch
- [ ] Push to GitHub, make repo public
- [ ] Enable GitHub Pages (Settings → Pages → Deploy from `/docs`)
- [ ] Verify demo loads at `https://open-migration.github.io/open-migration/demo/`
- [ ] Verify CI passes (green badge on README)
- [ ] Pin the repo on your GitHub profile

### Launch posts (post within 60 minutes of each other)

**Hacker News — Show HN**
```
Show HN: Open Migration – export your Claude/ChatGPT/Gemini history to Obsidian or searchable HTML

I built this because I had 2 years of Claude conversations I couldn't search or use.
The export is just a JSON blob. This tool turns it into something actually useful.

- HTML: single file, full-text search, dark theme, works offline
- Obsidian: vault with YAML frontmatter, wikilinks, callout blocks
- Markdown: plain files, works anywhere
- Merge: combine ChatGPT + Claude + Gemini into one archive

Zero dependencies. Local-first. One command.

GitHub: https://github.com/open-migration/open-migration
Demo: https://open-migration.github.io/open-migration/demo/
```

**r/ClaudeAI**
Title: "I built a tool to export your Claude conversation history to Obsidian or a searchable HTML archive"
Link to demo first, then GitHub.

**r/ChatGPT**
Same title adapted. Lead with ChatGPT angle since that's their audience.

**r/ObsidianMD**
Title: "Export your AI conversations (Claude, ChatGPT, Gemini) directly to an Obsidian vault — free, local, zero config"
This community specifically will love the Obsidian output.

**r/LocalLLaMA**
Title: "Open Migration: own your AI conversation history — export Claude/ChatGPT/Gemini to Obsidian/HTML/Markdown"

**X/Twitter thread**
1. "I had 2 years of Claude conversations I couldn't search. So I built Open Migration."
2. "It takes your export file and turns it into [gif of demo]"
3. "Zero dependencies. Runs locally. Your data never leaves your machine."
4. "Also merges ChatGPT + Claude + Gemini into one archive."
5. "GitHub: [link] — Demo: [link]"

**Product Hunt**
Submit day after HN to capture second wave.

---

## Timing

Best windows (IST):
- Tuesday or Wednesday
- 9:00 PM – 11:00 PM IST (HN US morning peak)

Avoid: Monday, Friday, weekends.

---

## The one asset that carries everything

A demo GIF. Record:
1. `omigrate convert --input conversations.json --open`
2. The HTML archive opening in browser
3. Typing in the search bar
4. Clicking through a conversation

Tools: OBS (free), or Windows Xbox Game Bar (Win+G), or macOS QuickTime.
Target: 10-15 seconds, < 5MB, high contrast so it reads on GitHub.

Add it to the README just below the install block.
