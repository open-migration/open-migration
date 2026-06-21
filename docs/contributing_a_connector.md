# Contributing a Connector

A connector reads one platform's export format and returns a `KnowledgeGraph`.
Most connectors are 100–250 lines of Python.

---

## Minimal template

```python
# open_migration/connectors/myplatform.py

from pathlib import Path
from open_migration.connectors.base import Connector
from open_migration.graph import KnowledgeGraph, Node, Edge, stable_id


class MyPlatformConnector(Connector):
    name = "myplatform"

    def supports(self, path: Path) -> bool:
        """Optional: return True if this connector recognises the file."""
        return "myplatform" in path.name.lower()

    def extract(self, input_path: Path) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        data = _load(input_path)   # parse JSON/ZIP/directory

        for conv in data:
            conv_id = stable_id("myplatform", "conversation", conv["id"])
            graph.add_node(Node(
                id=conv_id,
                type="conversation",
                title=conv.get("title"),
                created_at=conv.get("created_at"),
                source="myplatform",
                source_id=conv["id"],
            ))

            for order, msg in enumerate(conv["messages"]):
                msg_id = stable_id("myplatform", "message", msg["id"])
                graph.add_node(Node(
                    id=msg_id,
                    type="message",
                    body=msg["text"],
                    source="myplatform",
                    source_id=msg["id"],
                    metadata={"role": msg.get("role", "unknown")},
                ))
                graph.add_edge("contains", conv_id, msg_id, order=order)

        return graph
```

## Register it

In `open_migration/connectors/__init__.py`:

```python
from open_migration.connectors.myplatform import MyPlatformConnector

CONNECTORS = {
    ...
    "myplatform": MyPlatformConnector,
}
```

## Rules

**Be defensive.** Export formats change without notice. Always use `.get()` with defaults:

```python
# Bad
title = conv["title"]

# Good
title = conv.get("title") or f"Conversation {idx + 1}"
```

**Wrap silently for individual items.** If one conversation is malformed, skip it:

```python
for conv in conversations:
    try:
        process(conv)
    except Exception:
        pass  # don't fail the whole export for one bad entry
```

**Use `stable_id()` for all IDs.** Never use `hash()` or `uuid.uuid4()`. IDs must be:
- Deterministic (same input → same ID)
- Unique across platforms (prefix with platform name)
- Safe as filenames

```python
# Correct
node_id = stable_id("myplatform", "conversation", source_id)

# Wrong — not deterministic across runs
node_id = str(uuid.uuid4())
```

**Preserve metadata.** Store any field you don't explicitly model in `node.metadata`:

```python
skip = {"id", "title", "messages", "created_at"}
extra = {k: v for k, v in conv.items() if k not in skip}
graph.add_node(Node(..., metadata=extra))
```

**Handle all common file shapes:**

```python
def _load(path: Path):
    if path.suffix == ".zip":
        # extract JSON from ZIP
        ...
    if path.is_dir():
        # find JSON inside directory
        ...
    # plain JSON file
    with path.open(encoding="utf-8") as f:
        return json.load(f)
```

## Write tests

Add a sample fixture and tests to `tests/test_suite.py`:

```python
MY_PLATFORM_SAMPLE = [{"id": "c1", "title": "Test", "messages": [...]}]

class TestMyPlatformConnector:
    def test_parse(self, tmp_path):
        f = tmp_path / "myplatform.json"
        f.write_text(json.dumps(MY_PLATFORM_SAMPLE))
        graph = MyPlatformConnector().extract(f)
        convs = list(graph.by_type("conversation"))
        assert len(convs) == 1
        assert convs[0].source == "myplatform"
```

## Checklist before opening a PR

- [ ] Connector file in `open_migration/connectors/myplatform.py`
- [ ] Registered in `open_migration/connectors/__init__.py`
- [ ] `supports()` method implemented
- [ ] Defensive `.get()` throughout
- [ ] `stable_id()` used for all node/edge IDs
- [ ] Tests added to `tests/test_suite.py`
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] Export format documented in the connector's module docstring (how to get it)

---

## Getting the export format

The hardest part is often finding the actual export. Here are starting points:

| Platform | Where to export |
|----------|----------------|
| ChatGPT | Settings → Data controls → Export data |
| Claude | claude.ai → Settings → Privacy → Export Data |
| Gemini | takeout.google.com → Gemini Apps Activity |
| Perplexity | No official export yet — check their settings page |
| Copilot | microsoft.com/en-us/privacy → Download your data |
| Mistral | Account settings → Data export |

If a platform has no export feature, check if they have an API that lets you retrieve conversation history.
