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
    if source == "web":
        if not url:
            console.print("[red]--url is required for web extraction[/red]")
            raise typer.Exit(1)

        from tml_engine.extractors.web import WebExtractor

        async def _extract() -> None:
            extractor = WebExtractor()
            config: dict = {"base_url": url}
            if template != "default":
                config["template_path"] = template
            console.print(f"[dim]Extracting from {url}...[/dim]")
            result = await extractor.extract(config)
            console.print(
                f"[green]Extracted {len(result.content_blocks)} content blocks "
                f"from {result.metadata.get('pages_crawled', 0)} pages[/green]"
            )

        asyncio.run(_extract())
    else:
        console.print(f"[yellow]Extract from '{source}' — plugin not yet available[/yellow]")


@app.command()
def interview(
    identity: str = typer.Option(..., help="Email of the person to interview"),
    fill_gaps: bool = typer.Option(False, help="Fill gaps from prior extractions"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Run an adaptive interview (requires ANTHROPIC_API_KEY)."""
    from tml_engine.extractors.interview import InterviewEngine

    engine = InterviewEngine()
    state = engine.new_session(identity)

    console.print("\n[bold]TML Coherence Engine — Adaptive Interview[/bold]")
    console.print(f"[dim]Session: {state.session_id}[/dim]\n")

    opening = engine.get_opening_message(state)
    console.print(f"[green]Interviewer:[/green] {opening}")

    async def _run_interview() -> None:
        nonlocal state

        while not engine.is_complete(state):
            console.print("")
            try:
                user_input = input("You: ")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Interview paused.[/dim]")
                return

            if user_input.strip().lower() in ("quit", "exit", "q"):
                console.print("[dim]Interview ended by user.[/dim]")
                return

            try:
                response, state = await engine.send_message(state, user_input)
                console.print(f"\n[green]Interviewer:[/green] {response}")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[dim]Make sure ANTHROPIC_API_KEY is set.[/dim]")
                return

        console.print("\n[bold green]Interview complete![/bold green]")
        result = engine.to_extraction_result(state)
        console.print(
            f"[dim]Extracted {len(result.content_blocks)} content blocks "
            f"from {result.metadata.get('total_messages', 0)} messages[/dim]"
        )

    asyncio.run(_run_interview())


@app.command()
def confirm(
    identity: str = typer.Option("", help="Email of the person to confirm (empty for mock data)"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
    mock: bool = typer.Option(False, help="Use mock data for testing"),
) -> None:
    """Launch the confirmation surface (Textual TUI)."""
    from tml_engine.confirmation.app import run_confirmation

    if mock or not identity:
        console.print("[dim]Launching with mock data...[/dim]")
        run_confirmation(declaration=None)
    else:
        console.print(f"[dim]Launching confirmation for {identity}...[/dim]")
        run_confirmation(declaration=None)  # TODO: load Declaration from storage


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
