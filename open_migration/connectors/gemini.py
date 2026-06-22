"""
Gemini connector.
Handles Google Takeout exports: Takeout/Gemini Apps Activity/

How to export:
  https://takeout.google.com → select "Gemini Apps Activity" → download ZIP
  Extract and point --input at the Gemini Apps Activity/ directory or MyActivity.json
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import zipfile

from open_migration.connectors.base import Connector
from open_migration.graph import KnowledgeGraph, Node, stable_id


def _load_takeout(path: Path) -> list[dict]:
    """
    Locate and load Gemini activity data from a Takeout directory or ZIP.
    Gemini Takeout has changed formats over time; we handle the common variants.
    """
    # If given a ZIP, extract to temp approach isn't needed — just walk the ZipFile
    if path.suffix == ".zip":
        # Safe: reads JSON directly to memory, never extracts to disk
        with zipfile.ZipFile(path) as zf:
            # Look for Gemini-related JSON files
            candidates = [
                n for n in zf.namelist()
                if "Gemini" in n and n.endswith(".json")
            ]
            if not candidates:
                raise FileNotFoundError("No Gemini JSON found in ZIP. Did you export Gemini Apps Activity?")
            records: list[dict] = []
            for name in candidates:
                with zf.open(name) as f:
                    try:
                        data = json.load(f)
                        records.extend(_normalize(data))
                    except Exception:
                        pass
            return records

    # Directory: search recursively
    if path.is_dir():
        json_files = list(path.rglob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No JSON files found under {path}")
        records = []
        for jf in json_files:
            try:
                with jf.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                records.extend(_normalize(data))
            except Exception:
                pass
        return records

    # Single JSON file
    with path.open("r", encoding="utf-8") as f:
        return _normalize(json.load(f))


def _normalize(data: Any) -> list[dict]:
    """
    Gemini Takeout has two common shapes:
      1. A list of activity records, each with 'title', 'time', 'subtitles' etc.
      2. A dict with a 'conversations' or 'sessions' key.
    We normalize both into a flat list of conversation-like dicts.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("conversations", "sessions", "items", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Might be a single conversation
        return [data]
    return []


def _extract_text_from_activity(record: dict) -> tuple[str, str]:
    """
    Extract (user_text, ai_text) from a Gemini Takeout activity record.
    The format varies: sometimes 'details', sometimes 'subtitles', sometimes nested.
    """
    user_text = ""
    ai_text = ""

    # Format 1: Google Takeout activity JSON (title = user prompt, subtitles = response)
    title = record.get("title", "")
    if title and title != "Used Gemini Apps":
        user_text = title

    subtitles = record.get("subtitles") or []
    if isinstance(subtitles, list):
        for s in subtitles:
            if isinstance(s, dict):
                ai_text += s.get("name", "") + "\n"
            elif isinstance(s, str):
                ai_text += s + "\n"

    # Format 2: Structured messages
    messages = record.get("messages") or record.get("turns") or []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = (msg.get("author") or msg.get("role") or "").lower()
        text = msg.get("text") or msg.get("content") or ""
        if isinstance(text, list):
            text = " ".join(str(t) for t in text)
        if role in ("user", "human"):
            user_text = str(text)
        elif role in ("model", "assistant", "gemini"):
            ai_text = str(text)

    # Format 3: details field
    details = record.get("details") or []
    for d in details:
        if isinstance(d, dict):
            name = d.get("name", "")
            if name:
                ai_text += name + "\n"

    return user_text.strip(), ai_text.strip()


class GeminiConnector(Connector):
    name = "gemini"

    def supports(self, path: Path) -> bool:
        name = path.name.lower()
        return "gemini" in name or "takeout" in name

    def extract(self, input_path: Path) -> KnowledgeGraph:
        records = _load_takeout(input_path)
        graph = KnowledgeGraph()

        for idx, record in enumerate(records):
            if not isinstance(record, dict):
                continue

            # Try to parse as a full conversation first
            messages = record.get("messages") or record.get("turns") or []
            has_messages = bool(messages)

            src_id = str(
                record.get("id") or record.get("conversation_id")
                or stable_id("gemini", idx, record.get("title"))
            )
            conv_id = stable_id("gemini", "conversation", src_id)

            title = (
                record.get("title")
                or record.get("name")
                or f"Gemini conversation {idx + 1}"
            )
            if title in ("Used Gemini Apps", "Gemini Apps Activity"):
                title = f"Gemini conversation {idx + 1}"

            created = (
                record.get("time")
                or record.get("created_at")
                or record.get("createdAt")
            )

            graph.add_node(Node(
                id=conv_id,
                type="conversation",
                title=title,
                created_at=str(created) if created else None,
                source="gemini",
                source_id=src_id,
                metadata={"record_index": idx},
            ))

            order = 0
            prev_id: str | None = None

            if has_messages:
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue
                    role = (msg.get("author") or msg.get("role") or "unknown").lower()
                    text = msg.get("text") or msg.get("content") or ""
                    if isinstance(text, list):
                        text = "\n".join(str(t) for t in text)
                    text = str(text).strip()
                    if not text:
                        continue
                    msg_id = stable_id("gemini", "message", src_id, str(order))
                    graph.add_node(Node(
                        id=msg_id,
                        type="message",
                        title=f"{role} message",
                        body=text,
                        source="gemini",
                        source_id=msg_id,
                        metadata={"role": role},
                    ))
                    graph.add_edge("contains", conv_id, msg_id, order=order)
                    if prev_id:
                        graph.add_edge("next", prev_id, msg_id, order=order)
                    prev_id = msg_id
                    order += 1
            else:
                # Activity record format: synthesize user + assistant messages
                user_text, ai_text = _extract_text_from_activity(record)

                if user_text:
                    uid = stable_id("gemini", "message", src_id, "user")
                    graph.add_node(Node(
                        id=uid, type="message", title="user message",
                        body=user_text, source="gemini", source_id=uid,
                        metadata={"role": "user"},
                    ))
                    graph.add_edge("contains", conv_id, uid, order=0)
                    prev_id = uid
                    order = 1

                if ai_text:
                    aid = stable_id("gemini", "message", src_id, "model")
                    graph.add_node(Node(
                        id=aid, type="message", title="model message",
                        body=ai_text, source="gemini", source_id=aid,
                        metadata={"role": "model"},
                    ))
                    graph.add_edge("contains", conv_id, aid, order=order)
                    if prev_id:
                        graph.add_edge("next", prev_id, aid, order=order)

        return graph
