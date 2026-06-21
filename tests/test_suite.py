"""
Tests for open-migration.
Run: pytest tests/ -v
"""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from open_migration.graph import KnowledgeGraph, Node, Edge, stable_id
from open_migration.connectors.chatgpt import ChatGPTConnector
from open_migration.connectors.claude import ClaudeConnector
from open_migration.connectors.gemini import GeminiConnector
from open_migration.connectors.auto import AutoConnector
from open_migration.exporters.html_site import HtmlSiteExporter
from open_migration.exporters.obsidian import ObsidianExporter
from open_migration.exporters.markdown import MarkdownExporter


# ── Fixtures ─────────────────────────────────────────────────────────────────

CHATGPT_SAMPLE = [
    {
        "id": "conv-001",
        "title": "Python debugging help",
        "create_time": 1700000000.0,
        "update_time": 1700001000.0,
        "current_node": "msg-003",
        "mapping": {
            "msg-001": {
                "id": "msg-001",
                "parent": None,
                "children": ["msg-002"],
                "message": None,
            },
            "msg-002": {
                "id": "msg-002",
                "parent": "msg-001",
                "children": ["msg-003"],
                "message": {
                    "id": "msg-002",
                    "author": {"role": "user"},
                    "create_time": 1700000001.0,
                    "content": {"content_type": "text", "parts": ["Why does my list comprehension not work?"]},
                    "status": "finished_successfully",
                    "metadata": {},
                },
            },
            "msg-003": {
                "id": "msg-003",
                "parent": "msg-002",
                "children": [],
                "message": {
                    "id": "msg-003",
                    "author": {"role": "assistant"},
                    "create_time": 1700000002.0,
                    "content": {"content_type": "text", "parts": ["List comprehensions need a valid iterable. Here's an example:\n```python\nresult = [x*2 for x in range(10)]\n```"]},
                    "status": "finished_successfully",
                    "metadata": {},
                },
            },
        },
    }
]

CLAUDE_SAMPLE = [
    {
        "uuid": "claude-conv-001",
        "name": "Architecture planning",
        "created_at": "2024-03-15T10:00:00.000000+00:00",
        "updated_at": "2024-03-15T10:05:00.000000+00:00",
        "account": {"uuid": "user-001"},
        "chat_messages": [
            {
                "uuid": "claude-msg-001",
                "text": "Help me design a microservices architecture for an e-commerce app.",
                "sender": "human",
                "created_at": "2024-03-15T10:00:00.000000+00:00",
                "attachments": [],
            },
            {
                "uuid": "claude-msg-002",
                "text": "Great question! Here's a recommended architecture:\n\n## Core Services\n\n1. **User Service** — handles auth\n2. **Product Service** — catalog management\n3. **Order Service** — order processing\n\nEach service should have its own database.",
                "sender": "assistant",
                "created_at": "2024-03-15T10:01:00.000000+00:00",
                "attachments": [],
            },
        ],
    }
]

GEMINI_SAMPLE = [
    {
        "title": "Explain quantum computing",
        "time": "2024-06-01T09:00:00Z",
        "messages": [
            {"author": "user", "text": "What is quantum computing in simple terms?"},
            {"author": "model", "text": "Quantum computing uses quantum bits (qubits) that can exist in multiple states simultaneously, unlike classical bits which are either 0 or 1."},
        ],
    }
]


@pytest.fixture
def chatgpt_json_file(tmp_path: Path) -> Path:
    f = tmp_path / "conversations.json"
    f.write_text(json.dumps(CHATGPT_SAMPLE), encoding="utf-8")
    return f


@pytest.fixture
def chatgpt_zip_file(tmp_path: Path) -> Path:
    json_path = tmp_path / "conversations.json"
    json_path.write_text(json.dumps(CHATGPT_SAMPLE), encoding="utf-8")
    zip_path = tmp_path / "chatgpt_export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(json_path, "conversations.json")
    return zip_path


@pytest.fixture
def claude_json_file(tmp_path: Path) -> Path:
    f = tmp_path / "claude_conversations.json"
    f.write_text(json.dumps(CLAUDE_SAMPLE), encoding="utf-8")
    return f


@pytest.fixture
def gemini_json_file(tmp_path: Path) -> Path:
    f = tmp_path / "gemini_activity.json"
    f.write_text(json.dumps(GEMINI_SAMPLE), encoding="utf-8")
    return f


@pytest.fixture
def mixed_graph() -> KnowledgeGraph:
    """A KnowledgeGraph with conversations from multiple sources."""
    from open_migration.connectors.chatgpt import ChatGPTConnector
    from open_migration.connectors.claude import ClaudeConnector

    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        gpt_f = p / "conversations.json"
        gpt_f.write_text(json.dumps(CHATGPT_SAMPLE), encoding="utf-8")
        claude_f = p / "claude.json"
        claude_f.write_text(json.dumps(CLAUDE_SAMPLE), encoding="utf-8")

        g1 = ChatGPTConnector().extract(gpt_f)
        g2 = ClaudeConnector().extract(claude_f)

        for node in g2.nodes.values():
            g1.add_node(node)
        for edge in g2.edges.values():
            g1.add_edge(edge.type, edge.from_id, edge.to_id, **edge.metadata)

        return g1


# ── Graph tests ───────────────────────────────────────────────────────────────

class TestGraph:
    def test_stable_id_deterministic(self):
        assert stable_id("a", "b", "c") == stable_id("a", "b", "c")

    def test_stable_id_unique(self):
        assert stable_id("a", "b") != stable_id("a", "c")

    def test_add_node(self):
        g = KnowledgeGraph()
        n = Node(id="n1", type="conversation", title="Test")
        g.add_node(n)
        assert "n1" in g.nodes

    def test_add_node_merge(self):
        """Adding the same node twice should merge, not duplicate."""
        g = KnowledgeGraph()
        g.add_node(Node(id="n1", type="conversation", title="Original"))
        g.add_node(Node(id="n1", type="conversation", title=None, source="chatgpt"))
        assert g.nodes["n1"].title == "Original"
        assert g.nodes["n1"].source == "chatgpt"

    def test_add_edge(self):
        g = KnowledgeGraph()
        g.add_node(Node(id="a", type="conversation"))
        g.add_node(Node(id="b", type="message"))
        g.add_edge("contains", "a", "b", order=0)
        children = g.children("a", "contains")
        assert len(children) == 1
        assert children[0].id == "b"

    def test_children_ordered(self):
        g = KnowledgeGraph()
        g.add_node(Node(id="parent", type="conversation"))
        for i in range(5):
            g.add_node(Node(id=f"msg-{i}", type="message"))
            g.add_edge("contains", "parent", f"msg-{i}", order=i)
        children = g.children("parent", "contains")
        assert [c.id for c in children] == [f"msg-{i}" for i in range(5)]

    def test_stats(self, mixed_graph: KnowledgeGraph):
        stats = mixed_graph.compute_stats()
        assert stats.total_conversations >= 2
        assert stats.total_messages >= 3
        assert stats.total_words > 0
        assert "chatgpt" in stats.sources
        assert "claude" in stats.sources


# ── Connector tests ───────────────────────────────────────────────────────────

class TestChatGPTConnector:
    def test_parse_json(self, chatgpt_json_file: Path):
        graph = ChatGPTConnector().extract(chatgpt_json_file)
        convs = list(graph.by_type("conversation"))
        assert len(convs) == 1
        assert convs[0].title == "Python debugging help"
        assert convs[0].source == "chatgpt"

    def test_messages_extracted(self, chatgpt_json_file: Path):
        graph = ChatGPTConnector().extract(chatgpt_json_file)
        conv = list(graph.by_type("conversation"))[0]
        messages = graph.children(conv.id, "contains")
        assert len(messages) == 2
        assert messages[0].metadata["role"] == "user"
        assert messages[1].metadata["role"] == "assistant"
        assert "list comprehension" in messages[0].body.lower()

    def test_parse_zip(self, chatgpt_zip_file: Path):
        graph = ChatGPTConnector().extract(chatgpt_zip_file)
        assert len(list(graph.by_type("conversation"))) == 1

    def test_code_block_preserved(self, chatgpt_json_file: Path):
        graph = ChatGPTConnector().extract(chatgpt_json_file)
        conv = list(graph.by_type("conversation"))[0]
        messages = graph.children(conv.id, "contains")
        assert "```python" in messages[1].body

    def test_timestamps(self, chatgpt_json_file: Path):
        graph = ChatGPTConnector().extract(chatgpt_json_file)
        conv = list(graph.by_type("conversation"))[0]
        assert conv.created_at is not None
        assert "2023" in conv.created_at


class TestClaudeConnector:
    def test_parse_json(self, claude_json_file: Path):
        graph = ClaudeConnector().extract(claude_json_file)
        convs = list(graph.by_type("conversation"))
        assert len(convs) == 1
        assert convs[0].title == "Architecture planning"
        assert convs[0].source == "claude"

    def test_messages(self, claude_json_file: Path):
        graph = ClaudeConnector().extract(claude_json_file)
        conv = list(graph.by_type("conversation"))[0]
        messages = graph.children(conv.id, "contains")
        assert len(messages) == 2
        assert messages[0].metadata["role"] == "human"
        assert "microservices" in messages[0].body.lower()

    def test_content_blocks(self, tmp_path: Path):
        """Test the newer content-block message format."""
        data = [{
            "uuid": "test-conv",
            "name": "Content blocks test",
            "created_at": "2024-01-01T00:00:00+00:00",
            "chat_messages": [{
                "uuid": "msg-1",
                "sender": "human",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "tool_use", "name": "calculator", "input": {"expr": "2+2"}},
                ],
            }],
        }]
        f = tmp_path / "claude_blocks.json"
        f.write_text(json.dumps(data))
        graph = ClaudeConnector().extract(f)
        messages = graph.children(list(graph.by_type("conversation"))[0].id, "contains")
        assert "Hello" in messages[0].body
        assert "calculator" in messages[0].body


class TestGeminiConnector:
    def test_parse_messages_format(self, gemini_json_file: Path):
        graph = GeminiConnector().extract(gemini_json_file)
        convs = list(graph.by_type("conversation"))
        assert len(convs) == 1
        messages = graph.children(convs[0].id, "contains")
        assert len(messages) == 2

    def test_activity_format(self, tmp_path: Path):
        """Test Takeout activity record format (title + subtitles)."""
        data = [{
            "title": "How does photosynthesis work?",
            "time": "2024-05-01T08:00:00Z",
            "subtitles": [{"name": "Photosynthesis is the process by which plants make food."}],
        }]
        f = tmp_path / "gemini_activity.json"
        f.write_text(json.dumps(data))
        graph = GeminiConnector().extract(f)
        convs = list(graph.by_type("conversation"))
        assert len(convs) == 1
        messages = graph.children(convs[0].id, "contains")
        assert any("photosynthesis" in (m.body or "").lower() for m in messages)


class TestAutoConnector:
    def test_detects_chatgpt(self, chatgpt_json_file: Path):
        graph = AutoConnector().extract(chatgpt_json_file)
        conv = list(graph.by_type("conversation"))[0]
        assert conv.source == "chatgpt"

    def test_detects_claude(self, claude_json_file: Path):
        graph = AutoConnector().extract(claude_json_file)
        conv = list(graph.by_type("conversation"))[0]
        assert conv.source == "claude"


# ── Exporter tests ────────────────────────────────────────────────────────────

class TestHtmlSiteExporter:
    def test_creates_html_file(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        HtmlSiteExporter().write(mixed_graph, tmp_path)
        assert (tmp_path / "archive.html").exists()

    def test_html_contains_conversations(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        HtmlSiteExporter().write(mixed_graph, tmp_path)
        html = (tmp_path / "archive.html").read_text()
        assert "Python debugging help" in html
        assert "Architecture planning" in html

    def test_html_contains_stats(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        HtmlSiteExporter().write(mixed_graph, tmp_path)
        html = (tmp_path / "archive.html").read_text()
        assert "total_conversations" in html

    def test_also_writes_graph_json(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        HtmlSiteExporter().write(mixed_graph, tmp_path)
        assert (tmp_path / "open-migration.graph.json").exists()

    def test_self_contained_no_external_assets(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        """HTML should not reference external CDN resources."""
        HtmlSiteExporter().write(mixed_graph, tmp_path)
        html = (tmp_path / "archive.html").read_text()
        assert "cdn." not in html
        assert 'src="http' not in html


class TestObsidianExporter:
    def test_creates_vault_structure(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        ObsidianExporter().write(mixed_graph, tmp_path)
        assert (tmp_path / "Index.md").exists()
        assert (tmp_path / "Conversations").is_dir()
        assert (tmp_path / ".obsidian").is_dir()

    def test_creates_note_per_conversation(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        ObsidianExporter().write(mixed_graph, tmp_path)
        notes = list((tmp_path / "Conversations").glob("*.md"))
        stats = mixed_graph.compute_stats()
        assert len(notes) == stats.total_conversations

    def test_yaml_frontmatter(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        ObsidianExporter().write(mixed_graph, tmp_path)
        notes = list((tmp_path / "Conversations").glob("*.md"))
        content = notes[0].read_text()
        assert content.startswith("---")
        assert "source:" in content
        assert "tags:" in content

    def test_index_contains_links(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        ObsidianExporter().write(mixed_graph, tmp_path)
        index = (tmp_path / "Index.md").read_text()
        assert "[[" in index


class TestMarkdownExporter:
    def test_creates_readme(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        MarkdownExporter().write(mixed_graph, tmp_path)
        assert (tmp_path / "README.md").exists()

    def test_creates_md_per_conversation(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        MarkdownExporter().write(mixed_graph, tmp_path)
        md_files = list(tmp_path.glob("*.md"))
        stats = mixed_graph.compute_stats()
        assert len(md_files) == stats.total_conversations + 1  # +1 for README

    def test_readme_has_stats(self, mixed_graph: KnowledgeGraph, tmp_path: Path):
        MarkdownExporter().write(mixed_graph, tmp_path)
        readme = (tmp_path / "README.md").read_text()
        assert "Conversations" in readme
        assert "Words" in readme


# ── CLI tests ─────────────────────────────────────────────────────────────────

class TestCLI:
    def test_version(self, capsys):
        from open_migration.cli import main
        ret = main(["--version"])
        out = capsys.readouterr().out
        assert "open-migration" in out
        assert ret == 0

    def test_missing_input_exits_1(self):
        from open_migration.cli import main
        ret = main(["convert", "--input", "/nonexistent/path/file.json"])
        assert ret == 1

    def test_full_pipeline_html(self, chatgpt_json_file: Path, tmp_path: Path):
        from open_migration.cli import main
        ret = main([
            "convert",
            "--input", str(chatgpt_json_file),
            "--source", "chatgpt",
            "--target", "html",
            "--output", str(tmp_path / "out"),
        ])
        assert ret == 0
        assert (tmp_path / "out" / "archive.html").exists()

    def test_full_pipeline_obsidian(self, claude_json_file: Path, tmp_path: Path):
        from open_migration.cli import main
        ret = main([
            "convert",
            "--input", str(claude_json_file),
            "--source", "claude",
            "--target", "obsidian",
            "--output", str(tmp_path / "vault"),
        ])
        assert ret == 0
        assert (tmp_path / "vault" / "Index.md").exists()

    def test_stats_flag(self, chatgpt_json_file: Path, tmp_path: Path):
        from open_migration.cli import main
        ret = main([
            "convert",
            "--input", str(chatgpt_json_file),
            "--output", str(tmp_path),
            "--stats",
        ])
        assert ret == 0

    def test_merge_command(self, chatgpt_json_file: Path, claude_json_file: Path, tmp_path: Path):
        from open_migration.cli import main
        ret = main([
            "merge",
            "--inputs", str(chatgpt_json_file), str(claude_json_file),
            "--target", "markdown",
            "--output", str(tmp_path / "merged"),
        ])
        assert ret == 0
        assert (tmp_path / "merged" / "README.md").exists()

    def test_legacy_mode(self, chatgpt_json_file: Path, tmp_path: Path):
        from open_migration.cli import main
        ret = main([
            "--input", str(chatgpt_json_file),
            "--target", "html",
            "--output", str(tmp_path / "legacy"),
        ])
        assert ret == 0
        assert (tmp_path / "legacy" / "archive.html").exists()
