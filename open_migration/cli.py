"""
omigrate — Open Migration CLI
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from open_migration.connectors import CONNECTORS
from open_migration.exporters import EXPORTERS


def _console():
    return Console() if HAS_RICH else None

def _print(msg, style=""):
    if HAS_RICH:
        Console().print(msg, style=style)
    else:
        import re
        print(re.sub(r"\[.*?\]", "", msg))

def _err(msg):
    _print(f"[bold red]Error:[/bold red] {msg}" if HAS_RICH else f"Error: {msg}")

def _ok(msg):
    _print(f"[bold green]✓[/bold green] {msg}" if HAS_RICH else f"✓ {msg}")

def _info(msg):
    _print(f"[dim]{msg}[/dim]" if HAS_RICH else msg)


BANNER = (
    "\n"
    "[bold #7c6af7]  ___                   __  __ _                 _   _\n"
    r" / _ \ _ __   ___ _ __ |  \/  (_) __ _ _ __ __ _| |_(_) ___  _ __" + "\n"
    r"| | | | '_ \ / _ \ '_ \| |\/| | |/ _` | '__/ _` | __| |/ _ \| '_ \\" + "\n"
    r"| |_| | |_) |  __/ | | | |  | | | (_| | | | (_| | |_| | (_) | | | |" + "\n"
    r" \___/| .__/ \___|_| |_|_|  |_|_|\__, |_|  \__,_|\__|_|\___/|_| |_|" + "\n"
    "      |_|                        |___/[/bold #7c6af7]\n"
    "[dim]Own your AI conversations. Move anywhere.[/dim]\n"
)

BANNER_PLAIN = "Open Migration — Own your AI conversations. Move anywhere."


def _print_banner(con):
    if HAS_RICH and con:
        con.print(BANNER)
    else:
        print(BANNER_PLAIN)
        print()


def _print_stats(stats, con):
    if HAS_RICH and con:
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column(style="dim")
        table.add_column(style="bold")
        table.add_row("Conversations", f"{stats.total_conversations:,}")
        table.add_row("Messages", f"{stats.total_messages:,}")
        table.add_row("Words", f"{stats.total_words:,}")
        table.add_row("Sources", ", ".join(stats.sources.keys()) or "—")
        if stats.date_range[0]:
            dr = f"{stats.date_range[0][:10]}  →  {stats.date_range[1][:10]}"
            table.add_row("Date range", dr)
        if stats.longest_conversation:
            title = stats.longest_conversation
            if len(title) > 50:
                title = title[:50] + "…"
            table.add_row("Longest", title)
        con.print(Panel(table, title="[bold]📊 Your AI history[/bold]", border_style="#7c6af7"))
    else:
        print(f"\nConversations : {stats.total_conversations:,}")
        print(f"Messages      : {stats.total_messages:,}")
        print(f"Words         : {stats.total_words:,}")
        print(f"Sources       : {', '.join(stats.sources.keys()) or '—'}")
        print()


def _open_output(output_dir, target):
    import subprocess
    try:
        if target == "html":
            html_file = output_dir / "archive.html"
            if not html_file.exists():
                html_file = next(output_dir.glob("*.html"), None)
            if html_file:
                _info(f"Opening {html_file.name} in browser…")
                if sys.platform == "win32":
                    subprocess.Popen(["start", str(html_file)], shell=True)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(html_file)])
                else:
                    subprocess.Popen(["xdg-open", str(html_file)])
        else:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(output_dir)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(output_dir)])
    except Exception:
        pass


def _extract(input_path, source, con):
    """Extract conversations from a file, with progress display."""
    connector_cls = CONNECTORS[source]
    connector = connector_cls()

    if HAS_RICH and con:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=con,
        ) as progress:
            task = progress.add_task("[cyan]Reading export…", total=None)
            try:
                graph = connector.extract(input_path)
            except Exception as exc:
                progress.stop()
                raise exc
            progress.update(task, description="[green]Export read ✓")
    else:
        print("Reading export…")
        graph = connector.extract(input_path)

    return graph


def _export(graph, target, output_dir, con):
    """Write graph to target format with progress display."""
    exporter_cls = EXPORTERS[target]
    exporter = exporter_cls()

    if HAS_RICH and con:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=con,
        ) as progress:
            task = progress.add_task(f"[cyan]Writing {target} output…", total=None)
            try:
                exporter.write(graph, output_dir)
            except Exception as exc:
                progress.stop()
                raise exc
            progress.update(task, description=f"[green]{target} output written ✓")
    else:
        print(f"Writing {target} output…")
        exporter.write(graph, output_dir)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_convert(args) -> int:
    con = _console()
    _print_banner(con)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        _err(f"Input path not found: {input_path}")
        return 1

    output_dir = Path(args.output or "./open-migration-output").expanduser().resolve()

    _info(f"Source:  {input_path.name}")
    _info(f"Format:  {args.source}")
    _info(f"Target:  {args.target}")
    _info(f"Output:  {output_dir}")
    print()

    t0 = time.perf_counter()
    try:
        graph = _extract(input_path, args.source, con)
    except Exception as exc:
        _err(str(exc))
        _info("Tip: Try --source chatgpt, --source claude, or --source gemini")
        return 1

    if not graph.nodes:
        _err("No conversations found. Is this the right file?")
        return 1

    stats = graph.compute_stats()
    _print_stats(stats, con)

    if args.stats:
        return 0

    try:
        _export(graph, args.target, output_dir, con)
    except Exception as exc:
        _err(f"Export failed: {exc}")
        return 1

    elapsed = time.perf_counter() - t0
    print()
    if HAS_RICH and con:
        con.print(
            f"[bold green]✓ Done![/bold green]  "
            f"{stats.total_conversations:,} conversations exported in [bold]{elapsed:.1f}s[/bold]"
        )
        con.print(f"  Output → [bold cyan]{output_dir}[/bold cyan]")
    else:
        print(f"✓ Done! {stats.total_conversations} conversations in {elapsed:.1f}s → {output_dir}")

    if args.open:
        _open_output(output_dir, args.target)

    print()
    return 0


def cmd_merge(args) -> int:
    from open_migration.connectors.auto import AutoConnector
    from open_migration.graph import KnowledgeGraph

    con = _console()
    _print_banner(con)

    inputs = [Path(p).expanduser().resolve() for p in args.inputs]
    missing = [str(p) for p in inputs if not p.exists()]
    if missing:
        _err(f"Input(s) not found: {', '.join(missing)}")
        return 1

    if len(inputs) < 2:
        _err("merge requires at least two --inputs")
        return 1

    output_dir = Path(args.output or "./open-migration-merged").expanduser().resolve()
    _info(f"Merging {len(inputs)} exports → {args.target}")
    print()

    t0 = time.perf_counter()
    merged = KnowledgeGraph()
    total_sources = []

    for path in inputs:
        _info(f"  Loading {path.name}…")
        try:
            graph = AutoConnector().extract(path)
        except Exception as exc:
            _err(f"Failed to parse {path.name}: {exc}")
            return 1

        # Merge nodes and edges
        for node in graph.nodes.values():
            merged.add_node(node)
        for edge in graph.edges.values():
            merged.add_edge(edge.type, edge.from_id, edge.to_id, **edge.metadata)

        src = list(graph.compute_stats().sources.keys())
        total_sources.extend(src)

    if not merged.nodes:
        _err("No conversations found across all inputs.")
        return 1

    stats = merged.compute_stats()
    _print_stats(stats, con)

    try:
        _export(merged, args.target, output_dir, con)
    except Exception as exc:
        _err(f"Export failed: {exc}")
        return 1

    elapsed = time.perf_counter() - t0
    print()
    if HAS_RICH and con:
        con.print(
            f"[bold green]✓ Merged![/bold green]  "
            f"{stats.total_conversations:,} conversations from {len(inputs)} sources in "
            f"[bold]{elapsed:.1f}s[/bold]"
        )
        con.print(f"  Output → [bold cyan]{output_dir}[/bold cyan]")
    else:
        print(f"✓ Merged! {stats.total_conversations} conversations → {output_dir}")

    if args.open:
        _open_output(output_dir, args.target)

    print()
    return 0


def cmd_serve(args) -> int:
    try:
        from open_migration.web.app import run_server
    except ImportError as exc:
        _err(str(exc))
        _info('Install with: pip install "open-migration[web]"')
        return 1

    try:
        run_server(port=args.port, no_open=args.no_open)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="omigrate",
        description="Export and migrate AI conversations from Claude, ChatGPT, and Gemini.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    sub = parser.add_subparsers(dest="command")

    # convert
    p_conv = sub.add_parser("convert", help="Convert an AI export to a target format")
    p_conv.add_argument("-i", "--input", required=True)
    p_conv.add_argument("-s", "--source", default="auto", choices=list(CONNECTORS.keys()))
    p_conv.add_argument("-t", "--target", default="html", choices=list(EXPORTERS.keys()))
    p_conv.add_argument("-o", "--output", default=None)
    p_conv.add_argument("--open", action="store_true")
    p_conv.add_argument("--stats", action="store_true")

    # merge
    p_merge = sub.add_parser("merge", help="Merge multiple AI exports into one archive")
    p_merge.add_argument("-i", "--inputs", nargs="+", required=True)
    p_merge.add_argument("-t", "--target", default="html", choices=list(EXPORTERS.keys()))
    p_merge.add_argument("-o", "--output", default=None)
    p_merge.add_argument("--open", action="store_true")

    # serve
    p_serve = sub.add_parser("serve", help='Launch local web UI (needs pip install "open-migration[web]")')
    p_serve.add_argument("--port", type=int, default=7337)
    p_serve.add_argument("--no-open", action="store_true")

    # Pre-check: legacy mode (omigrate --input X --target Y without subcommand)
    argv_actual = list(argv) if argv is not None else sys.argv[1:]
    SUBCMDS = {"convert", "merge", "serve"}
    first_pos = next((a for a in argv_actual if not a.startswith("-")), None)
    is_legacy = (
        first_pos not in SUBCMDS
        and any(a in ("-i", "--input") for a in argv_actual)
    )
    if is_legacy:
        leg = argparse.ArgumentParser(add_help=False)
        leg.add_argument("-i", "--input", default=None)
        leg.add_argument("-s", "--source", default="auto")
        leg.add_argument("-t", "--target", default="html")
        leg.add_argument("-o", "--output", default=None)
        leg.add_argument("--open", action="store_true")
        leg.add_argument("--stats", action="store_true")
        largs, _ = leg.parse_known_args(argv_actual)
        if largs.input:
            return cmd_convert(largs)

    args = parser.parse_args(argv)

    if args.version:
        from open_migration import __version__
        print(f"open-migration {__version__}")
        return 0

    if args.command == "convert":
        return cmd_convert(args)
    elif args.command == "merge":
        return cmd_merge(args)
    elif args.command == "serve":
        return cmd_serve(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
