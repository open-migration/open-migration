# Architecture

Open Migration uses a three-layer pipeline that completely decouples sources from targets.

```
Input File(s)
     │
     ▼
┌─────────────┐
│  Connector  │  Reads one platform's export format
└──────┬──────┘
       │  list[Node], list[Edge]
       ▼
┌──────────────────┐
│ Knowledge Graph  │  Universal, platform-neutral representation
│                  │  Nodes: conversations, messages, documents
│                  │  Edges: contains, next, links_to, parent_of
└──────┬───────────┘
       │  KnowledgeGraph
       ▼
┌─────────────┐
│  Exporter   │  Writes to target format
└─────────────┘
       │
       ▼
  Output Files
```

## Why a graph?

Every platform is just a different skin on the same underlying structure: items (nodes) with relationships between them (edges).

| Platform concept | Graph equivalent |
|-----------------|-----------------|
| ChatGPT conversation | Node (type: conversation) |
| ChatGPT message | Node (type: message) |
| "message belongs to conversation" | Edge (type: contains) |
| "message comes after message" | Edge (type: next) |
| Attachment | Attachment on a Node |
| Notion page | Node (type: page) |
| Notion block | Node (type: block) |
| Jira ticket | Node (type: ticket) |
| Jira comment | Node (type: comment), Edge (type: replies_to) |

The graph model lets us write one exporter that works for any source — the Obsidian exporter doesn't know or care whether the data came from Claude or ChatGPT.

## Node

```python
@dataclass
class Node:
    id: str              # stable SHA-256 content hash
    type: str            # conversation | message | document | ticket | page | ...
    title: str | None
    body: str | None
    created_at: str | None   # ISO 8601
    updated_at: str | None
    source: str | None       # chatgpt | claude | gemini | notion | ...
    source_id: str | None    # original platform ID
    url: str | None          # link back to original
    metadata: dict           # platform-specific extras
    attachments: list[Attachment]
```

## Edge

```python
@dataclass
class Edge:
    id: str
    type: str           # contains | next | replies_to | links_to | parent_of | ...
    from_id: str
    to_id: str
    metadata: dict      # order, weight, etc.
```

## Connector interface

```python
class Connector(ABC):
    name: str   # "chatgpt", "claude", "gemini", ...

    def extract(self, input_path: Path) -> KnowledgeGraph: ...
    def supports(self, path: Path) -> bool: ...  # optional hint
```

A connector reads one format and populates a KnowledgeGraph. It should:
- Be robust to missing/malformed fields (platforms change their export format)
- Preserve all metadata in `node.metadata` even if not explicitly modelled
- Generate stable IDs using `stable_id()` so that re-running a migration doesn't duplicate nodes

## Exporter interface

```python
class Exporter(ABC):
    name: str   # "html", "obsidian", "markdown", ...

    def write(self, graph: KnowledgeGraph, output_path: Path) -> None: ...
```

An exporter reads a KnowledgeGraph and writes files to a directory. It should:
- Call `output_path.mkdir(parents=True, exist_ok=True)` first
- Work with any source — never assume `node.source == "chatgpt"`
- Use `graph.by_type("conversation")` to iterate conversations
- Use `graph.children(conv.id, "contains")` to get messages in order

## ID stability

Node IDs are generated with `stable_id(*parts)` — a 24-character hex prefix of SHA-256. The same content always produces the same ID, so:

- Re-running a migration on the same export produces identical output
- Merging two graphs is safe: duplicate nodes are merged, not duplicated
- Node IDs can be used as filenames and wikilinks safely

## Merge semantics

When merging two KnowledgeGraphs, `graph.add_node(node)` is idempotent for the same ID:
- If the node already exists, missing fields from the new node are copied over
- Metadata is merged (new keys added, existing keys preserved)
- Attachments are deduplicated by ID

This makes `omigrate merge` safe to run multiple times on overlapping exports.

## Adding a connector

See [contributing_a_connector.md](contributing_a_connector.md).

## Adding an exporter

See [CONTRIBUTING.md](../CONTRIBUTING.md).
