"""TrustPipe CLI — Click-based command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from trustpipe._version import __version__

console = Console()


def _get_tp(ctx: click.Context) -> "TrustPipe":
    """Lazy-load TrustPipe instance from CLI context."""
    from trustpipe import TrustPipe
    from trustpipe.core.config import TrustPipeConfig

    project = ctx.obj.get("project", "default")
    db_path = ctx.obj.get("db_path")
    config_path = ctx.obj.get("config_path")

    config = None
    if config_path:
        config = TrustPipeConfig._from_yaml(Path(config_path))

    return TrustPipe(project=project, db_path=db_path, config=config)


@click.group()
@click.version_option(version=__version__, prog_name="trustpipe")
@click.option("--project", "-p", default="default", help="Project namespace")
@click.option("--config", "-c", "config_path", type=click.Path(), help="Path to config YAML")
@click.option("--db", "db_path", type=click.Path(), help="Path to SQLite database")
@click.pass_context
def cli(ctx: click.Context, project: str, config_path: Optional[str], db_path: Optional[str]) -> None:
    """TrustPipe — AI Data Supply Chain Trust & Provenance."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = project
    ctx.obj["config_path"] = config_path
    ctx.obj["db_path"] = db_path


@cli.command()
@click.option("--project", "-p", default="default", help="Project name")
@click.pass_context
def init(ctx: click.Context, project: str) -> None:
    """Initialize a TrustPipe project."""
    from trustpipe import TrustPipe
    from trustpipe.core.config import DEFAULT_CONFIG_DIR

    ctx.obj["project"] = project
    tp = _get_tp(ctx)
    db_path = tp.config.resolve_db_path(project)

    console.print(f"[green]✓[/green] Initialized project [bold]{project}[/bold]")
    console.print(f"  Database: {db_path}")
    console.print(f"  Config dir: {DEFAULT_CONFIG_DIR}")
    console.print()
    console.print("Next steps:")
    console.print("  1. Track data: tp.track(df, name='my_data')")
    console.print("  2. Check trust: trustpipe score my_data")
    console.print("  3. View lineage: trustpipe trace my_data")


@cli.command()
@click.argument("dataset")
@click.option("--depth", "-d", type=int, default=0, help="Max ancestor depth (0=full)")
@click.option(
    "--format", "fmt", type=click.Choice(["tree", "table", "json"]), default="tree"
)
@click.pass_context
def trace(ctx: click.Context, dataset: str, depth: int, fmt: str) -> None:
    """Show provenance chain for a dataset."""
    tp = _get_tp(ctx)
    chain = tp.trace(dataset)

    if not chain:
        console.print(f"[yellow]No provenance records found for '{dataset}'[/yellow]")
        return

    if fmt == "json":
        click.echo(json.dumps([r.to_dict() for r in chain], indent=2, default=str))
        return

    if fmt == "table":
        table = Table(title=f"Provenance: {dataset}")
        table.add_column("#", style="dim")
        table.add_column("ID", style="cyan")
        table.add_column("Source")
        table.add_column("Rows", justify="right")
        table.add_column("Parents")
        table.add_column("Merkle Root", style="dim")
        table.add_column("Created")

        for i, r in enumerate(chain):
            table.add_row(
                str(i + 1),
                r.id,
                r.source or "-",
                str(r.row_count) if r.row_count else "-",
                ", ".join(r.parent_ids) if r.parent_ids else "-",
                r.merkle_root[:12] + "..." if r.merkle_root else "-",
                r.created_at.strftime("%Y-%m-%d %H:%M"),
            )
        console.print(table)
        return

    # Tree format (default)
    lineage = tp.lineage(dataset)
    if lineage:
        console.print(lineage.to_tree_string())
    else:
        # Fallback to simple list
        tree = Tree(f"[bold]{dataset}[/bold]")
        for r in chain:
            source = f" ← {r.source}" if r.source else ""
            rows = f" ({r.row_count} rows)" if r.row_count else ""
            tree.add(f"[cyan]{r.id}[/cyan]{source}{rows}")
        console.print(tree)


@cli.command()
@click.option("--record", "-r", "record_id", help="Verify specific record ID")
@click.pass_context
def verify(ctx: click.Context, record_id: Optional[str]) -> None:
    """Verify Merkle chain integrity."""
    tp = _get_tp(ctx)
    result = tp.verify(record_id)

    if record_id:
        if result["verified"]:
            console.print(f"[green]✓[/green] Record {record_id}: integrity verified")
        else:
            console.print(f"[red]✗[/red] Record {record_id}: VERIFICATION FAILED")
        return

    integrity = result["integrity"]
    color = "green" if integrity == "OK" else "red"
    console.print(f"Chain integrity: [{color}]{integrity}[/{color}]")
    console.print(f"  Total records: {result['total']}")
    console.print(f"  Verified: {result['verified']}")
    console.print(f"  Failed: {result['failed']}")
    if result["chain_root"]:
        console.print(f"  Root hash: {result['chain_root'][:24]}...")
    if result["failed_ids"]:
        console.print("[red]Failed record IDs:[/red]")
        for fid in result["failed_ids"]:
            console.print(f"  - {fid}")


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show project summary."""
    tp = _get_tp(ctx)
    info = tp.status()

    console.print(f"[bold]Project:[/bold] {info['project']}")
    console.print(f"[bold]Records:[/bold] {info['record_count']}")
    console.print(f"[bold]Chain length:[/bold] {info['chain_length']}")
    if info["chain_root"]:
        console.print(f"[bold]Chain root:[/bold] {info['chain_root'][:24]}...")
    console.print()

    if info["latest_records"]:
        table = Table(title="Latest Records")
        table.add_column("Name")
        table.add_column("Source")
        table.add_column("Created")
        for r in info["latest_records"]:
            table.add_row(r["name"], r.get("source") or "-", r["created_at"][:19])
        console.print(table)
    else:
        console.print("[dim]No records yet. Start with: tp.track(data, name='...')")
