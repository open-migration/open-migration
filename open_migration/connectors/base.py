from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from open_migration.graph import KnowledgeGraph


class Connector(ABC):
    """Read a platform export and return a KnowledgeGraph."""
    name: str

    @abstractmethod
    def extract(self, input_path: Path) -> KnowledgeGraph: ...

    def supports(self, path: Path) -> bool:
        """Optional: return True if this connector can handle the given path."""
        return False


class Exporter(ABC):
    """Write a KnowledgeGraph into a target format."""
    name: str

    @abstractmethod
    def write(self, graph: KnowledgeGraph, output_path: Path) -> None: ...
