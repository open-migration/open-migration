"""
Obsidian Vault Exporter.
Creates a proper Obsidian vault with YAML frontmatter, wikilinks, and an index note.
"""
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime, timezone

from open_migration.connectors.base import Exporter
from open_migration.graph import KnowledgeGraph, Node


def _safe_filename(title: str, max_len: int = 80) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "", title)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] or "Untitled"


def _role_label(role: str) -> str:
    return {
        "user": "You", "human": "You",
        "assistant": "AI", "claude": "AI", "model": "AI",
        "system": "System",
    }.get(str(role).lower(), str(role).title())


def _role_callout(role: str) -> str:
    return {
        "user": "info", "human": "info",
        "assistant": "note", "claude": "note", "model": "note",
        "system": "warning",
    }.get(str(role).lower(), "note")


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso[:10] if iso else ""


def _yaml_str(s: str | None) -> str:
    if s is None:
        return '""'
    s = str(s).replace('"', '\\"').replace("\n", " ")
    return f'"{s}"'


class ObsidianExporter(Exporter):
    name = "obsidian"

    def write(self, graph: KnowledgeGraph, output_path: Path) -> None:
        vault = output_path
        vault.mkdir(parents=True, exist_ok=True)

        convs_dir = vault / "Conversations"
        convs_dir.mkdir(exist_ok=True)

        conversations = sorted(
            graph.by_type("conversation"),
            key=lambda n: n.created_at or "",
            reverse=True,
        )

        written: list[tuple[Node, Path]] = []
        seen_filenames: dict[str, int] = {}

        for conv in conversations:
            filename = _safe_filename(conv.title or "Untitled")
            if filename in seen_filenames:
                seen_filenames[filename] += 1
                filename = f"{filename} ({seen_filenames[filename]})"
            else:
                seen_filenames[filename] = 0

            note_path = convs_dir / f"{filename}.md"
            messages = graph.children(conv.id, "contains")

            lines: list[str] = []

            # YAML frontmatter
            lines += [
                "---",
                f"title: {_yaml_str(conv.title)}",
                f"source: {conv.source or 'unknown'}",
                f"source_id: {_yaml_str(conv.source_id)}",
            ]
            if conv.created_at:
                lines.append(f"date: {_fmt_date(conv.created_at)}")
            if conv.updated_at:
                lines.append(f"updated: {_fmt_date(conv.updated_at)}")
            lines += [
                f"messages: {len(messages)}",
                f"words: {sum(len((m.body or '').split()) for m in messages)}",
                "tags:",
                f"  - ai-conversation",
                f"  - {conv.source or 'unknown'}",
                "---",
                "",
            ]

            # Title
            lines.append(f"# {conv.title or 'Untitled'}")
            lines.append("")

            # Meta block
            if conv.url:
                lines.append(f"> **Source:** [{conv.url}]({conv.url})")
            if conv.created_at:
                lines.append(f"> **Date:** {_fmt_date(conv.created_at)}")
            lines += ["", "---", ""]

            # Messages as Obsidian callouts
            for msg in messages:
                role = msg.metadata.get("role", "unknown")
                label = _role_label(role)
                callout = _role_callout(role)
                time_str = f" — {_fmt_date(msg.created_at)}" if msg.created_at else ""
                body = (msg.body or "").strip()

                lines.append(f"> [!{callout}]+ {label}{time_str}")
                for body_line in body.split("\n"):
                    lines.append(f"> {body_line}")

                # Attachments
                if msg.attachments:
                    lines.append("> ")
                    lines.append("> **Attachments:**")
                    for att in msg.attachments:
                        lines.append(f"> - `{att.name}`")

                lines.append("")

            note_path.write_text("\n".join(lines), encoding="utf-8")
            written.append((conv, note_path))

        # ── Index note ──────────────────────────────────────────────────────
        stats = graph.compute_stats()
        index_lines: list[str] = [
            "---",
            'title: "Open Migration Archive Index"',
            f"generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            f"total_conversations: {stats.total_conversations}",
            f"total_messages: {stats.total_messages}",
            f"total_words: {stats.total_words}",
            "---",
            "",
            "# 🗂️ AI Conversation Archive",
            "",
            f"> Generated by **[Open Migration](https://github.com/open-migration/open-migration)**",
            "",
            "## 📊 Stats",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Conversations | {stats.total_conversations:,} |",
            f"| Messages | {stats.total_messages:,} |",
            f"| Words | {stats.total_words:,} |",
            f"| Sources | {', '.join(stats.sources.keys()) or '—'} |",
        ]

        if stats.date_range[0]:
            index_lines.append(f"| Date Range | {_fmt_date(stats.date_range[0])} → {_fmt_date(stats.date_range[1])} |")
        if stats.longest_conversation:
            index_lines.append(f"| Longest Conversation | {stats.longest_conversation} |")

        index_lines += ["", "## 🔗 All Conversations", ""]

        # Group by source
        by_source: dict[str, list[tuple[Node, Path]]] = {}
        for conv, path in written:
            src = conv.source or "unknown"
            by_source.setdefault(src, []).append((conv, path))

        for src, items in by_source.items():
            icons = {"chatgpt": "🤖", "claude": "⚡", "gemini": "✨"}
            icon = icons.get(src, "💬")
            index_lines.append(f"### {icon} {src.title()} ({len(items)})")
            index_lines.append("")
            for conv, path in items:
                rel = path.relative_to(vault)
                wikilink = str(rel.with_suffix("")).replace("\\", "/")
                date_str = f" `{_fmt_date(conv.created_at)}`" if conv.created_at else ""
                msgs = graph.children(conv.id, "contains")
                index_lines.append(f"- [[{wikilink}]]{date_str} · {len(msgs)} messages")
            index_lines.append("")

        (vault / "Index.md").write_text("\n".join(index_lines), encoding="utf-8")

        # ── .obsidian config ────────────────────────────────────────────────
        obs_dir = vault / ".obsidian"
        obs_dir.mkdir(exist_ok=True)
        (obs_dir / "app.json").write_text(
            '{"promptDelete":false,"trashOption":"local"}\n', encoding="utf-8"
        )
        (obs_dir / "appearance.json").write_text(
            '{"theme":"obsidian"}\n', encoding="utf-8"
        )
