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
    identity: str = typer.Option("user@local", help="Email of the person this extraction is for"),
    template: str = typer.Option("default", help="Scrape template name"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Extract content from a source, structure as TML primitives, and persist."""
    if source == "web":
        if not url:
            console.print("[red]--url is required for web extraction[/red]")
            raise typer.Exit(1)

        from tml_engine.identity.local import LocalIdentityProvider
        from tml_engine.pipeline import run_web_extraction
        from tml_engine.storage.sqlite import StorageEngine
        from tml_engine.structurer.llm import LLMStructurer

        _ensure_db_dir(db)

        async def _extract() -> None:
            storage = StorageEngine(db)
            await storage.initialize()
            try:
                provider = LocalIdentityProvider(storage)
                human = await provider.resolve(identity)
                structurer = LLMStructurer()

                console.print(f"[dim]Extracting from {url}...[/dim]")
                scope_id = await run_web_extraction(
                    url=url,
                    identity=human,
                    storage=storage,
                    structurer=structurer,
                    template=template,
                )
                console.print(f"[green]Extraction complete. Scope: {scope_id}[/green]")

                # Show summary
                primitives = await storage.list_primitives(scope_id=scope_id)
                type_counts: dict[str, int] = {}
                for p in primitives:
                    ptype = p["type"]
                    type_counts[ptype] = type_counts.get(ptype, 0) + 1
                for ptype, count in sorted(type_counts.items()):
                    console.print(f"  {ptype}: {count}")
            finally:
                await storage.close()

        asyncio.run(_extract())
    else:
        console.print(f"[yellow]Extract from '{source}' — plugin not yet available[/yellow]")


@app.command()
def interview(
    identity: str = typer.Option(..., help="Email of the person to interview"),
    fill_gaps: bool = typer.Option(False, help="Fill gaps from prior extractions"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Run an adaptive interview, structure results, and persist."""
    from tml_engine.extractors.interview import InterviewEngine
    from tml_engine.identity.local import LocalIdentityProvider
    from tml_engine.pipeline import run_interview_structuring
    from tml_engine.storage.sqlite import StorageEngine
    from tml_engine.structurer.llm import LLMStructurer

    _ensure_db_dir(db)

    engine = InterviewEngine()
    state = engine.new_session(identity)

    console.print("\n[bold]TML Coherence Engine — Adaptive Interview[/bold]")
    console.print(f"[dim]Session: {state.session_id}[/dim]\n")

    opening = engine.get_opening_message(state)
    console.print(f"[green]Interviewer:[/green] {opening}")

    async def _run_interview() -> None:
        nonlocal state

        storage = StorageEngine(db)
        await storage.initialize()
        try:
            # Save initial session state
            provider = LocalIdentityProvider(storage)
            human = await provider.resolve(identity)
            identity_row = await storage.get_identity_by_email(identity)
            identity_id = identity_row["id"] if identity_row else "unknown"

            await storage.create_interview_session(
                session_id=state.session_id,
                identity_id=identity_id,
                phase=state.phase.value,
            )

            while not engine.is_complete(state):
                console.print("")
                try:
                    user_input = input("You: ")
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Interview paused.[/dim]")
                    await storage.update_interview_session(
                        state.session_id,
                        phase=state.phase.value,
                        conversation_history=[
                            m.model_dump(mode="json") if hasattr(m, "model_dump") else m
                            for m in state.conversation_history
                        ],
                        status="paused",
                    )
                    return

                if user_input.strip().lower() in ("quit", "exit", "q"):
                    console.print("[dim]Interview ended by user.[/dim]")
                    return

                try:
                    response, state = await engine.send_message(state, user_input)
                    console.print(f"\n[green]Interviewer:[/green] {response}")

                    # Update session state after each exchange
                    await storage.update_interview_session(
                        state.session_id,
                        phase=state.phase.value,
                        conversation_history=[
                            m.model_dump(mode="json") if hasattr(m, "model_dump") else m
                            for m in state.conversation_history
                        ],
                    )
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

            # Structure and persist
            console.print("[dim]Structuring interview results...[/dim]")
            structurer = LLMStructurer()
            scope_id = await run_interview_structuring(
                result=result,
                identity=human,
                storage=storage,
                structurer=structurer,
            )
            console.print(f"[green]Structured and persisted. Scope: {scope_id}[/green]")

            await storage.update_interview_session(
                state.session_id,
                status="completed",
            )
        finally:
            await storage.close()

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
        from tml_engine.confirmation.app import run_confirmation_async
        from tml_engine.pipeline import build_declaration_from_storage, find_scope_for_identity
        from tml_engine.storage.sqlite import StorageEngine

        _ensure_db_dir(db)

        async def _confirm() -> None:
            storage = StorageEngine(db)
            await storage.initialize()
            try:
                scope_id = await find_scope_for_identity(storage, identity)
                if not scope_id:
                    console.print(
                        f"[red]No data found for {identity}. Run extract or interview first.[/red]"
                    )
                    raise typer.Exit(1)

                declaration = await build_declaration_from_storage(storage, scope_id)
                if not declaration:
                    console.print(f"[red]Could not build Declaration for scope {scope_id}[/red]")
                    raise typer.Exit(1)

                # Resolve identity ID for provenance tracking
                identity_row = await storage.get_identity_by_email(identity)
                identity_id = identity_row["id"] if identity_row else identity

                console.print(f"[dim]Launching confirmation for {identity}...[/dim]")
                await run_confirmation_async(
                    declaration=declaration,
                    storage=storage,
                    identity_id=identity_id,
                )
            finally:
                await storage.close()

        asyncio.run(_confirm())


@app.command()
def serve(
    port: int = typer.Option(8080, help="Port for textual-web"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Serve the confirmation surface via web browser."""
    console.print("[yellow]Web serving — not yet implemented (Stage 6)[/yellow]")


@app.command(name="export")
def export_cmd(
    identity: str = typer.Option(..., help="Email of the person to export"),
    fmt: str = typer.Option("json", "--format", help="Export format: json or yaml"),
    output: Path = typer.Option(..., help="Output file path"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Export a confirmed Declaration."""
    from tml_engine.pipeline import build_declaration_from_storage, find_scope_for_identity
    from tml_engine.storage.sqlite import StorageEngine

    async def _export() -> None:
        storage = StorageEngine(db)
        await storage.initialize()
        try:
            scope_id = await find_scope_for_identity(storage, identity)
            if not scope_id:
                console.print(f"[red]No data found for {identity}[/red]")
                raise typer.Exit(1)

            declaration = await build_declaration_from_storage(storage, scope_id)
            if not declaration:
                console.print(f"[red]Could not build Declaration for scope {scope_id}[/red]")
                raise typer.Exit(1)

            if fmt == "yaml":
                from tml_engine.export.yaml import export_declaration_yaml

                export_declaration_yaml(declaration, output)
            else:
                from tml_engine.export.json import export_declaration_json

                export_declaration_json(declaration, output)

            console.print(f"[green]Exported Declaration to {output}[/green]")
        finally:
            await storage.close()

    asyncio.run(_export())


@app.command()
def graph(
    scope: str = typer.Option(..., help="Scope ID for the organizational graph"),
    fmt: str = typer.Option("json", "--format", help="Export format: json"),
    output: Path | None = typer.Option(None, help="Output file path"),
    show_flows: bool = typer.Option(False, help="Print decision flows"),
    show_automation: bool = typer.Option(False, help="Print automation candidates"),
    db: Path = typer.Option(DEFAULT_DB, help="Path to SQLite database"),
) -> None:
    """Compute and display the organizational graph."""
    from tml_engine.graph.compute import compute_organizational_graph
    from tml_engine.pipeline import build_declaration_from_storage
    from tml_engine.storage.sqlite import StorageEngine

    async def _graph() -> None:
        import json

        from tml_engine.models.declaration import Declaration

        storage = StorageEngine(db)
        await storage.initialize()
        try:
            # Load all declarations for this scope
            decl_rows = await storage.list_declarations(scope_id=scope)

            declarations = []
            if decl_rows:
                for row in decl_rows:
                    data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
                    declarations.append(Declaration.model_validate(data))
            else:
                # Try building from primitives directly
                declaration = await build_declaration_from_storage(storage, scope)
                if declaration:
                    declarations.append(declaration)

            if not declarations:
                console.print(f"[red]No declarations found for scope {scope}[/red]")
                raise typer.Exit(1)

            org_graph = compute_organizational_graph(declarations)

            if output:
                output.write_text(org_graph.model_dump_json(indent=2))
                console.print(f"[green]Organizational graph exported to {output}[/green]")

            if show_flows:
                console.print("\n[bold]Decision Flows[/bold]")
                if not org_graph.decision_flows:
                    console.print("  [dim]No decision flows found[/dim]")
                for flow in org_graph.decision_flows:
                    console.print(f"  {flow.description}")

            if show_automation:
                console.print("\n[bold]Automation Candidates[/bold]")
                if not org_graph.automation_candidates:
                    console.print("  [dim]No automation candidates found[/dim]")
                for candidate in org_graph.automation_candidates:
                    color = (
                        "green"
                        if candidate.automation_readiness > 0.7
                        else ("yellow" if candidate.automation_readiness > 0.4 else "red")
                    )
                    console.print(
                        f"  [{color}]{candidate.automation_readiness:.0%}[/{color}] "
                        f"{candidate.capability_id} → {candidate.recommended_skill_type}"
                    )
                    if candidate.missing_elements:
                        for missing in candidate.missing_elements:
                            console.print(f"    [dim]missing: {missing}[/dim]")

            if not output and not show_flows and not show_automation:
                console.print(
                    f"[green]Graph computed: "
                    f"{len(org_graph.decision_flows)} flows, "
                    f"{len(org_graph.dependency_map)} dependencies, "
                    f"{len(org_graph.automation_candidates)} automation candidates[/green]"
                )
        finally:
            await storage.close()

    asyncio.run(_graph())


if __name__ == "__main__":
    app()
