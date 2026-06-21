"""
Auto connector — detect source format and delegate to the right connector.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from open_migration.connectors.base import Connector
from open_migration.connectors.chatgpt import ChatGPTConnector
from open_migration.connectors.claude import ClaudeConnector
from open_migration.connectors.gemini import GeminiConnector
from open_migration.graph import KnowledgeGraph


def _sniff(path: Path) -> str:
    """Return the most likely source name without fully parsing."""
    name = path.name.lower()

    # Filename hints
    if "chatgpt" in name or "openai" in name:
        return "chatgpt"
    if "claude" in name or "anthropic" in name:
        return "claude"
    if "gemini" in name or "takeout" in name:
        return "gemini"

    # Peek at content
    try:
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                names_lower = " ".join(zf.namelist()).lower()
                if "gemini" in names_lower:
                    return "gemini"
                if "chatgpt" in names_lower or "openai" in names_lower:
                    return "chatgpt"
                if "claude" in names_lower or "anthropic" in names_lower:
                    return "claude"
            return "chatgpt"  # safest guess for anonymous zip

        read_path = path
        if path.is_dir():
            for candidate in ("conversations.json", "chats.json"):
                if (path / candidate).exists():
                    read_path = path / candidate
                    break

        with read_path.open("r", encoding="utf-8") as f:
            raw = f.read(4096)

        # JSON structure sniffing
        data = json.loads(raw if raw.endswith("]") or raw.endswith("}") else raw + '"}]')
        sample: dict = {}
        if isinstance(data, list) and data:
            sample = data[0] if isinstance(data[0], dict) else {}
        elif isinstance(data, dict):
            for key in ("conversations", "chats"):
                if key in data and isinstance(data[key], list) and data[key]:
                    sample = data[key][0]
                    break
            if not sample:
                sample = data

        # ChatGPT has 'mapping' with node trees
        if "mapping" in sample:
            return "chatgpt"
        # Claude has uuid + chat_messages or sender field
        if "chat_messages" in sample or ("uuid" in sample and "sender" in str(raw)[:2000]):
            return "claude"
        # Gemini Takeout has 'subtitles' or 'products'
        if "subtitles" in sample or "products" in sample:
            return "gemini"
        # OpenAI role strings: 'role': 'assistant' appear in GPT too
        if '"role"' in raw and '"mapping"' in raw:
            return "chatgpt"

    except Exception:
        pass

    return "chatgpt"  # best guess


class AutoConnector(Connector):
    name = "auto"

    def extract(self, input_path: Path) -> KnowledgeGraph:
        source = _sniff(input_path)
        connector_map = {
            "chatgpt": ChatGPTConnector,
            "claude": ClaudeConnector,
            "gemini": GeminiConnector,
        }
        connector = connector_map[source]()
        try:
            graph = connector.extract(input_path)
            if graph.nodes:
                return graph
        except Exception:
            pass

        # Try remaining connectors
        for name, cls in connector_map.items():
            if name == source:
                continue
            try:
                graph = cls().extract(input_path)
                if graph.nodes:
                    return graph
            except Exception:
                continue

        raise ValueError(
            f"Could not parse {input_path.name}. "
            "Try --source chatgpt, --source claude, or --source gemini."
        )
