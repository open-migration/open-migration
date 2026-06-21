# Examples

## Try it right now — no installation needed

Open [`demo/index.html`](demo/index.html) in any browser.

You'll see a live example of the HTML output with conversations from both
ChatGPT and Claude samples — searchable, filterable, fully navigable.

---

## Sample export files

| File | Source | Conversations | Description |
|------|--------|--------------|-------------|
| `sample_chatgpt.json` | ChatGPT | 2 | CSS centering, Python performance |
| `sample_claude.json` | Claude | 1 | REST API design discussion |

These are synthetic examples safe to share publicly. They show the exact JSON
structure that ChatGPT and Claude use in their real exports.

---

## Run the samples yourself

```bash
# Install
pip install open-migration

# Convert ChatGPT sample to HTML (opens in browser)
omigrate convert --input examples/sample_chatgpt.json --target html --open

# Convert Claude sample to Obsidian vault
omigrate convert --input examples/sample_claude.json --target obsidian --output ./vault/

# Merge both into one archive
omigrate merge --inputs examples/sample_chatgpt.json examples/sample_claude.json --target html --open
```

---

## Using your real export

**ChatGPT:** chatgpt.com → Settings → Data controls → Export data → Download ZIP

**Claude:** claude.ai → Settings (bottom left) → Privacy → Export Data

**Gemini:** [takeout.google.com](https://takeout.google.com) → select "Gemini Apps Activity" → Download

```bash
# Auto-detects format
omigrate convert --input ~/Downloads/chatgpt_export.zip --target html --open
```
