"""
ChatGPT connector.
Handles conversations.json from https://chat.openai.com → Settings → Export data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import zipfile

from open_migration.connectors.base import Connector
from open_migration.graph import Attachment, KnowledgeGraph, Node, stable_id


# ── Helpers ─────────────────────────────────────────────────────────────────

def _load(path: Path) -> Any:
    """Load JSON from a file, directory, or ZIP."""
    if path.is_dir():
        path = path / "conversations.json"
    if path.suffix == ".zip":
        # Safe: reads JSON directly to memory, never extracts to disk
        with zipfile.ZipFile(path) as zf:
            name = next(
                (n for n in zf.namelist() if n.endswith("conversations.json")),
                None,
            )
            if not name:
                raise ValueError("ZIP has no conversations.json")
            with zf.open(name) as f:
                return json.load(f)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return (
            datetime.fromtimestamp(float(value), tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )
    except Exception:
        return str(value)


def _text(content: Any) -> str:
    """Recursively extract text from ChatGPT's content shapes."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_text(x) for x in content if x is not None).strip()
    if isinstance(content, dict):
        for key in ("parts", "text", "result", "value"):
            if key in content:
                return _text(content[key])
        # tool results, code interpreter output, etc.
        if content.get("content_type") in ("tether_browsing_display", "tether_quote"):
            return ""
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def _linearize(mapping: dict[str, Any], current_node: str | None) -> list[str]:
    """Walk from current_node back to root, then reverse → chronological order."""
    if current_node and current_node in mapping:
        ids: list[str] = []
        seen: set[str] = set()
        nid: str | None = current_node
        while nid and nid not in seen and nid in mapping:
            seen.add(nid)
            ids.append(nid)
            nid = mapping[nid].get("parent")
        return list(reversed(ids))
    # Fallback: DFS from roots
    roots = [k for k, v in mapping.items() if not v.get("parent")]
    out: list[str] = []

    def dfs(nid: str) -> None:
        out.append(nid)
        for child in mapping.get(nid, {}).get("children") or []:
            dfs(child)

    for r in roots:
        dfs(r)
    return out


# ── Connector ────────────────────────────────────────────────────────────────

class ChatGPTConnector(Connector):
    name = "chatgpt"

    def supports(self, path: Path) -> bool:
        name = path.name.lower()
        return "chatgpt" in name or "openai" in name or name == "conversations.json"

    def extract(self, input_path: Path) -> KnowledgeGraph:
        data = _load(input_path)
        conversations = (
            data.get("conversations")
            if isinstance(data, dict)
            else data
            if isinstance(data, list)
            else []
        )

        graph = KnowledgeGraph()
        for idx, conv in enumerate(conversations):
            if not isinstance(conv, dict):
                continue

            src_id = str(
                conv.get("id") or conv.get("conversation_id")
                or stable_id("chatgpt", idx, conv.get("title"))
            )
            conv_id = stable_id("chatgpt", "conversation", src_id)
            title = conv.get("title") or f"ChatGPT conversation {idx + 1}"

            graph.add_node(Node(
                id=conv_id,
                type="conversation",
                title=title,
                created_at=_iso(conv.get("create_time")),
                updated_at=_iso(conv.get("update_time")),
                source="chatgpt",
                source_id=src_id,
                url=f"https://chatgpt.com/c/{src_id}" if conv.get("id") else None,
                metadata={"conversation_index": idx},
            ))

            mapping = conv.get("mapping") or {}
            ordered = _linearize(mapping, conv.get("current_node"))
            prev_id: str | None = None
            order = 0

            for node_key in ordered:
                item = mapping.get(node_key) or {}
                msg = item.get("message")
                if not msg:
                    continue

                author = (msg.get("author") or {}).get("role") or "unknown"
                if author == "system":
                    continue  # skip system bootstrap messages

                body = _text(msg.get("content"))
                if not body.strip():
                    continue

                msg_src_id = str(msg.get("id") or node_key)
                msg_id = stable_id("chatgpt", "message", msg_src_id)

                raw_meta = dict(msg.get("metadata") or {})
                attachments: list[Attachment] = []
                for a in raw_meta.pop("attachments", None) or []:
                    if isinstance(a, dict):
                        att_id = stable_id("chatgpt", "att", msg_src_id, a.get("id") or a.get("name"))
                        attachments.append(Attachment(
                            id=att_id,
                            name=a.get("name") or att_id,
                            source_uri=a.get("url"),
                            mime_type=a.get("mime_type"),
                            size=a.get("size"),
                            metadata=a,
                        ))

                graph.add_node(Node(
                    id=msg_id,
                    type="message",
                    title=f"{author} message",
                    body=body,
                    created_at=_iso(msg.get("create_time")),
                    updated_at=_iso(msg.get("update_time")),
                    source="chatgpt",
                    source_id=msg_src_id,
                    metadata={"role": author, "status": msg.get("status"), **raw_meta},
                    attachments=attachments,
                ))
                graph.add_edge("contains", conv_id, msg_id, order=order)
                if prev_id:
                    graph.add_edge("next", prev_id, msg_id, order=order)
                prev_id = msg_id
                order += 1

        return graph
