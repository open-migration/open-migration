from open_migration.exporters.html_site import HtmlSiteExporter
from open_migration.exporters.obsidian import ObsidianExporter
from open_migration.exporters.markdown import MarkdownExporter

EXPORTERS = {
    "html": HtmlSiteExporter,
    "obsidian": ObsidianExporter,
    "markdown": MarkdownExporter,
}

__all__ = ["HtmlSiteExporter", "ObsidianExporter", "MarkdownExporter", "EXPORTERS"]
