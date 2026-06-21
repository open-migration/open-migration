"""
Open Migration — Universal Knowledge Graph
Platform-neutral representation for any AI conversation, doc, ticket, or note.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Iterable
import hashlib
import json


def stable_id(*parts: object) -> str:
    raw = "::".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:24]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Attachment:
    id: str
    name: str
    source_uri: str | None = None
    local_path: str | None = None
    mime_type: str | None = None
    size: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    id: str
    type: str  # conversation | message | document | ticket | page | ...
    title: str | None = None
    body: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    source: str | None = None
    source_id: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    attachments: list[Attachment] = field(default_factory=list)


@dataclass
class Edge:
    id: str
    type: str  # contains | next | replies_to | links_to | parent_of | ...
    from_id: str
    to_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationReport:
    source: str
    target: str
    started_at: str = field(default_factory=now_iso)
    finished_at: str | None = None
    nodes_in: int = 0
    edges_in: int = 0
    nodes_out: int = 0
    warnings: list[str] = field(default_factory=list)
    losses: list[dict[str, Any]] = field(default_factory=list)

    def finish(self) -> None:
        self.finished_at = now_iso()


@dataclass
class GraphStats:
    total_conversations: int = 0
    total_messages: int = 0
    total_words: int = 0
    total_chars: int = 0
    sources: dict[str, int] = field(default_factory=dict)
    date_range: tuple[str | None, str | None] = (None, None)
    avg_messages_per_conv: float = 0.0
    longest_conversation: str | None = None  # title

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_conversations": self.total_conversations,
            "total_messages": self.total_messages,
            "total_words": self.total_words,
            "total_chars": self.total_chars,
            "sources": self.sources,
            "date_range": list(self.date_range),
            "avg_messages_per_conv": round(self.avg_messages_per_conv, 1),
            "longest_conversation": self.longest_conversation,
        }


class KnowledgeGraph:
    """
    Platform-neutral representation for documents, messages, tickets and links.
    The intermediate format for any Open Migration pipeline.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self.report: MigrationReport | None = None

    # ── Node / Edge management ──────────────────────────────────────────────

    def add_node(self, node: Node) -> Node:
        if node.id in self.nodes:
            existing = self.nodes[node.id]
            for key in ("title", "body", "created_at", "updated_at", "source", "source_id", "url"):
                if getattr(existing, key) in (None, "") and getattr(node, key) not in (None, ""):
                    setattr(existing, key, getattr(node, key))
            existing.metadata.update({k: v for k, v in node.metadata.items() if k not in existing.metadata})
            existing.attachments.extend(
                a for a in node.attachments if a.id not in {x.id for x in existing.attachments}
            )
            return existing
        self.nodes[node.id] = node
        return node

    def add_edge(self, type: str, from_id: str, to_id: str, **metadata: Any) -> Edge:
        edge_id = stable_id(type, from_id, to_id, json.dumps(metadata, sort_keys=True, default=str))
        edge = Edge(id=edge_id, type=type, from_id=from_id, to_id=to_id, metadata=metadata)
        self.edges.setdefault(edge_id, edge)
        return self.edges[edge_id]

    def children(self, parent_id: str, edge_type: str | None = None) -> list[Node]:
        edges = [
            e for e in self.edges.values()
            if e.from_id == parent_id and (edge_type is None or e.type == edge_type)
        ]
        edges.sort(key=lambda e: e.metadata.get("order", 0))
        return [self.nodes[e.to_id] for e in edges if e.to_id in self.nodes]

    def incoming(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        return [
            e for e in self.edges.values()
            if e.to_id == node_id and (edge_type is None or e.type == edge_type)
        ]

    def by_type(self, *types: str) -> Iterable[Node]:
        wanted = set(types)
        return (n for n in self.nodes.values() if n.type in wanted)

    # ── Stats ───────────────────────────────────────────────────────────────

    def compute_stats(self) -> GraphStats:
        conversations = list(self.by_type("conversation"))
        stats = GraphStats(total_conversations=len(conversations))
        sources: dict[str, int] = {}
        dates: list[str] = []
        conv_msg_counts: list[tuple[int, str]] = []

        for conv in conversations:
            if conv.source:
                sources[conv.source] = sources.get(conv.source, 0) + 1
            if conv.created_at:
                dates.append(conv.created_at)

            messages = self.children(conv.id, "contains")
            conv_msg_counts.append((len(messages), conv.title or conv.id))

            for msg in messages:
                stats.total_messages += 1
                body = msg.body or ""
                stats.total_words += len(body.split())
                stats.total_chars += len(body)

        stats.sources = sources
        if dates:
            dates_sorted = sorted(dates)
            stats.date_range = (dates_sorted[0], dates_sorted[-1])
        if conv_msg_counts:
            stats.avg_messages_per_conv = stats.total_messages / len(conv_msg_counts)
            stats.longest_conversation = max(conv_msg_counts)[1]

        return stats

    # ── Serialization ───────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "open-migration-graph/v1",
            "generated_at": now_iso(),
            "stats": self.compute_stats().to_dict(),
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges.values()],
            "report": asdict(self.report) if self.report else None,
        }

    def write_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
