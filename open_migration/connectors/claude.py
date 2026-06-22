"""
Claude connector.
Handles JSON exports from https://claude.ai → Settings → Export Data.
Tolerates both the flat-text and content-block message formats.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import zipfile

from open_migration.connectors.base import Connector
from open_migration.graph import Attachment, KnowledgeGraph, Node, stable_id


def _load(path: Path) -> Any:
    if path.is_dir():
        for candidate in ("conversations.json", "chats.json"):
            if (path / candidate).exists():
                path = path / candidate
                break
    if path.suffix == ".zip":
        # Safe: reads JSON directly to memory, never extracts to disk
        with zipfile.ZipFile(path) as zf:
            name = next(
                (n for n in zf.namelist() if n.endswith(".json")),
                None,
            )
            if not name:
                raise ValueError("ZIP has no JSON file")
            with zf.open(name) as f:
                return json.load(f)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _pick(obj: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        v = obj.get(k)
        if v not in (None, ""):
            return v
    return None


def _body(msg: dict[str, Any]) -> str:
    """
    Extract text from a Claude message.
    Handles: plain text field, list of content blocks, dict with text key.
    """
    # Try simple text field first
    text = msg.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    # Content blocks (newer format)
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    name = block.get("name", "tool")
                    inp = json.dumps(block.get("input", {}), ensure_ascii=False)
                    parts.append(f"[Tool call: {name}]\n```json\n{inp}\n```")
                elif btype == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, list):
                        inner = "\n".join(
                            b.get("text", "") for b in inner if isinstance(b, dict)
                        )
                    parts.append(f"[Tool result]\n{inner}")
                elif btype == "image":
                    parts.append("[Image attachment]")
        return "\n\n".join(p for p in parts if p).strip()

    # Fallback
    for key in ("body", "message", "value"):
        v = msg.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return ""


class ClaudeConnector(Connector):
    name = "claude"

    def supports(self, path: Path) -> bool:
        name = path.name.lower()
        return "claude" in name or "anthropic" in name

    def extract(self, input_path: Path) -> KnowledgeGraph:
        data = _load(input_path)
        if isinstance(data, dict):
            conversations = data.get("conversations") or data.get("chats") or [data]
        elif isinstance(data, list):
            conversations = data
        else:
            raise ValueError("Claude export must be a JSON array or object containing conversations")

        graph = KnowledgeGraph()

        for idx, conv in enumerate(conversations):
            if not isinstance(conv, dict):
                continue

            src_id = str(
                _pick(conv, "uuid", "id", "conversation_id")
                or stable_id("claude", idx, _pick(conv, "name", "title"))
            )
            conv_id = stable_id("claude", "conversation", src_id)
            title = _pick(conv, "name", "title") or f"Claude conversation {idx + 1}"

            graph.add_node(Node(
                id=conv_id,
                type="conversation",
                title=title,
                created_at=_pick(conv, "created_at", "createdAt"),
                updated_at=_pick(conv, "updated_at", "updatedAt"),
                source="claude",
                source_id=src_id,
                metadata={"conversation_index": idx},
            ))

            messages = _pick(conv, "chat_messages", "messages", "turns") or []
            prev_id: str | None = None

            for order, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    continue

                msg_src_id = str(
                    _pick(msg, "uuid", "id")
                    or stable_id("claude-msg", src_id, order)
                )
                role = _pick(msg, "sender", "role", "author") or "unknown"
                body = _body(msg)

                attachments: list[Attachment] = []
                for a in msg.get("attachments") or []:
                    if isinstance(a, dict):
                        att_id = stable_id(
                            "claude", "att", msg_src_id,
                            a.get("file_name") or a.get("name") or a.get("id"),
                        )
                        attachments.append(Attachment(
                            id=att_id,
                            name=a.get("file_name") or a.get("name") or att_id,
                            source_uri=a.get("url"),
                            mime_type=a.get("mime_type") or a.get("file_type"),
                            size=a.get("size"),
                            metadata=a,
                        ))

                # Preserve all remaining fields in metadata
                skip = {"text", "content", "body", "message", "attachments",
                        "uuid", "id", "sender", "role", "author"}
                extra_meta = {k: v for k, v in msg.items() if k not in skip}

                msg_id = stable_id("claude", "message", msg_src_id)
                graph.add_node(Node(
                    id=msg_id,
                    type="message",
                    title=f"{role} message",
                    body=body,
                    created_at=_pick(msg, "created_at", "createdAt"),
                    updated_at=_pick(msg, "updated_at", "updatedAt"),
                    source="claude",
                    source_id=msg_src_id,
                    metadata={"role": role, **extra_meta},
                    attachments=attachments,
                ))
                graph.add_edge("contains", conv_id, msg_id, order=order)
                if prev_id:
                    graph.add_edge("next", prev_id, msg_id, order=order)
                prev_id = msg_id

        return graph
