# Contributing to Open Migration

Thank you for helping make AI data portability a reality.

## Ways to contribute

### 1. Build a connector (highest impact)

A connector reads one platform's export and returns a `KnowledgeGraph`. That's it.

See [docs/contributing_a_connector.md](docs/contributing_a_connector.md) for the full guide. The short version:

```python
from pathlib import Path
from open_migration.connectors.base import Connector
from open_migration.graph import KnowledgeGraph, Node, Edge, stable_id

class MyPlatformConnector(Connector):
    name = "myplatform"

    def extract(self, input_path: Path) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        # parse input_path, create nodes and edges
        return graph
```

Most connectors are 100–200 lines. ChatGPT and Claude connectors are good references.

Connectors we're looking for:
- Perplexity
- Notion (AI features / pages)
- Microsoft Copilot
- Mistral Le Chat
- Google AI Studio
- Slack DM exports
- Discord personal data request
- Obsidian (as a *source*)

### 2. Build an exporter

An exporter takes a `KnowledgeGraph` and writes files to a target directory.

```python
from open_migration.connectors.base import Exporter
from open_migration.graph import KnowledgeGraph
from pathlib import Path

class MyExporter(Exporter):
    name = "myformat"

    def write(self, graph: KnowledgeGraph, output_path: Path) -> None:
        output_path.mkdir(parents=True, exist_ok=True)
        # write files to output_path
```

Exporters we're looking for:
- Logseq
- Roam Research
- Notion (import CSV/JSON format)
- Git repository (one commit per conversation)
- SQLite full-text search database
- Anki flashcard deck

### 3. Fix bugs and improve existing connectors

Platform export formats change. If you find a conversation that doesn't parse correctly, open an issue with the relevant part of your export (redact any private content).

### 4. Write docs and examples

Clear docs make the project accessible to non-technical users. That's our core audience.

---

## Development setup

```bash
git clone https://github.com/open-migration/open-migration
cd open-migration
pip install -e ".[dev]"
pytest tests/ -v
```

## Pull request checklist

- [ ] Tests pass (`pytest tests/`)
- [ ] New connector/exporter has tests in `tests/test_suite.py`
- [ ] Code follows the existing style (run `ruff check open_migration/`)
- [ ] New connector is registered in `open_migration/connectors/__init__.py`
- [ ] New exporter is registered in `open_migration/exporters/__init__.py`
- [ ] README connector/exporter table updated

## Code style

- Python 3.11+
- Type hints on all public functions
- Descriptive variable names over comments
- No required third-party dependencies in core code
- Graceful handling of malformed/unexpected export data

## Questions?

Open an issue — there are no dumb questions about export formats. These things are undocumented and weird.
