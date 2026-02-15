"""CLI entry point for the TML Coherence Engine."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="tml-engine",
    help="TML Coherence Engine — extract, structure, confirm human expertise.",
    no_args_is_help=True,
)
console = Console()

DEFAULT_DB = Path.cwd() / ".tml" / "coherence.db"


def _ensure_db_dir(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


@app.command()
def init(
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Initialize a new TML Coherence Engine project."""
    from tml_engine.storage.sqlite import StorageEngine

    _ensure_db_dir(db)

    async def _init() -> None:
        engine = StorageEngine(db)
        await engine.initialize()
        await engine.close()

    asyncio.run(_init())
    console.print(f"[green]Initialized TML Coherence Engine at {db}[/green]")


@app.command()
def status(
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Show status of primitives and declarations."""
    from tml_engine.storage.sqlite import StorageEngine

    async def _status() -> None:
        engine = StorageEngine(db)
        await engine.initialize()
        try:
            primitives = await engine.list_primitives()
            declarations = await engine.list_declarations()

            if not primitives and not declarations:
                console.print("[dim]No primitives or declarations found.[/dim]")
                return

            # Count by type and status
            type_counts: dict[str, int] = {}
            status_counts: dict[str, int] = {}
            for p in primitives:
                ptype = p["type"]
                pstatus = p["confirmation_status"]
                type_counts[ptype] = type_counts.get(ptype, 0) + 1
                status_counts[pstatus] = status_counts.get(pstatus, 0) + 1

            console.print("\n[bold]Primitives[/bold]")
            for ptype, count in sorted(type_counts.items()):
                console.print(f"  {ptype}: {count}")

            console.print("\n[bold]Confirmation Status[/bold]")
            for pstatus, count in sorted(status_counts.items()):
                console.print(f"  {pstatus}: {count}")

            console.print(f"\n[bold]Declarations:[/bold] {len(declarations)}")
        finally:
            await engine.close()

    asyncio.run(_status())


@app.command()
def extract(
    source: str = typer.Argument(help="Source type: 'web' or 'atlassian'"),
    url: str | None = typer.Option(None, help="URL to scrape (for web extractor)"),
    template: str = typer.Option("default", help="Scrape template name"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Extract content from a source."""
    console.print(f"[yellow]Extract from '{source}' — not yet implemented (Stage 3)[/yellow]")


@app.command()
def interview(
    identity: str = typer.Option(..., help="Email of the person to interview"),
    fill_gaps: bool = typer.Option(False, help="Fill gaps from prior extractions"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Run an adaptive interview."""
    console.print("[yellow]Adaptive interview — not yet implemented (Stage 4)[/yellow]")


@app.command()
def confirm(
    identity: str = typer.Option(..., help="Email of the person to confirm"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Launch the confirmation surface (Textual TUI)."""
    console.print("[yellow]Confirmation TUI — not yet implemented (Stage 2)[/yellow]")


@app.command()
def serve(
    port: int = typer.Option(8080, help="Port for textual-web"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Serve the confirmation surface via web browser."""
    console.print("[yellow]Web serving — not yet implemented (Stage 5)[/yellow]")


@app.command()
def export(
    identity: str = typer.Option(..., help="Email of the person to export"),
    format: str = typer.Option("json", help="Export format: json or yaml"),
    output: Path = typer.Option(..., help="Output file path"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Export a confirmed Declaration."""
    console.print("[yellow]Export — not yet implemented (Stage 5)[/yellow]")


@app.command()
def graph(
    scope: str = typer.Option(..., help="Scope ID for the organizational graph"),
    format: str = typer.Option("json", help="Export format: json"),
    output: Path | None = typer.Option(None, help="Output file path"),
    show_flows: bool = typer.Option(False, help="Print decision flows"),
    show_automation: bool = typer.Option(False, help="Print automation candidates"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Export or display the organizational graph."""
    console.print("[yellow]Organizational graph — not yet implemented (Stage 5)[/yellow]")


if __name__ == "__main__":
    app()
