"""jackryan CLI entrypoint.

Everything a human action touches lives here. Actions on the DB happen
via subcommands; review of results happens via Airtable (future) or by
inspecting the SQLite file directly.

Available today (early scaffold):
  jackryan config validate     -- load & cross-validate all YAML config
  jackryan config show-thesis  -- print the parsed thesis
  jackryan db init             -- create SQLite schema
  jackryan llm ping            -- smoke-test the OpenRouter connection
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from jackryan import __version__
from jackryan.config import load_all
from jackryan.config.loader import ConfigError

# Load .env at import time so any subcommand sees the vars.
load_dotenv()

app = typer.Typer(
    help="jackryan -- AI-augmented sourcing & screening workflow.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect and validate configuration.")
db_app = typer.Typer(help="Database operations.")
llm_app = typer.Typer(help="LLM diagnostics.")
app.add_typer(config_app, name="config")
app.add_typer(db_app, name="db")
app.add_typer(llm_app, name="llm")

console = Console()


@app.command()
def version() -> None:
    """Print the installed jackryan version."""
    rprint(f"jackryan [bold]{__version__}[/bold]")


# ------------------------------------------------------------------- config --

@config_app.command("validate")
def config_validate() -> None:
    """Load and cross-validate all YAML config files."""
    try:
        cfg = load_all()
    except ConfigError as e:
        console.print(f"[bold red]Configuration invalid:[/bold red]\n{e}")
        raise typer.Exit(code=1)

    table = Table(title="Config summary", show_header=True, header_style="bold")
    table.add_column("File")
    table.add_column("Summary")
    table.add_row("thesis.yaml", f"{cfg.thesis.name} (v{cfg.thesis.version})")
    table.add_row("kpis.yaml", f"{len(cfg.kpis)} KPIs ({len(cfg.required_kpi_keys())} required)")
    table.add_row(
        "weights.yaml",
        f"{len(cfg.weights.dimensions)} dimensions, "
        f"weights sum = {sum(d.weight for d in cfg.weights.dimensions):.2f}",
    )
    table.add_row("models.yaml", f"{len(cfg.models.steps)} steps routed")
    console.print(table)
    console.print("[bold green]OK[/bold green] -- all config files valid.")


@config_app.command("show-thesis")
def config_show_thesis() -> None:
    """Print the parsed thesis in JSON form."""
    cfg = load_all()
    console.print_json(json.dumps(cfg.thesis.model_dump(), indent=2, default=str))


@config_app.command("show-kpis")
def config_show_kpis() -> None:
    """List all configured KPIs."""
    cfg = load_all()
    table = Table(title="KPIs", show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Type")
    table.add_column("Required")
    table.add_column("Description")
    for k in cfg.kpis:
        table.add_row(k.key, k.type, "✓" if k.required else "", k.description)
    console.print(table)


@config_app.command("show-weights")
def config_show_weights() -> None:
    """List all scoring dimensions."""
    cfg = load_all()
    table = Table(title="Scoring dimensions", show_header=True, header_style="bold")
    table.add_column("Dimension")
    table.add_column("Weight")
    table.add_column("Scorer")
    table.add_column("Inputs")
    for d in cfg.weights.dimensions:
        table.add_row(d.key, f"{d.weight:.2f}", d.scorer, ", ".join(d.inputs) or "-")
    console.print(table)


# ----------------------------------------------------------------------- db --

@db_app.command("init")
def db_init() -> None:
    """Create the SQLite schema. Idempotent."""
    from jackryan.db import init_db  # local import: avoid pulling SQLAlchemy on --help

    path: Path = init_db()
    console.print(f"[bold green]OK[/bold green] -- database ready at {path}")


# ---------------------------------------------------------------------- llm --

@llm_app.command("ping")
def llm_ping(
    step: str = typer.Option("extract_from_website", help="Step key from models.yaml"),
) -> None:
    """Send a trivial prompt through the configured model to verify OpenRouter access."""
    from jackryan.db import init_db
    from jackryan.llm import get_client

    init_db()  # ensure llm_calls table exists so logging works
    cfg = load_all()
    client = get_client(cfg)
    resp = client.complete(
        step=step,
        system="You are a terse assistant. Reply with a single word.",
        user="Say 'pong'.",
    )
    console.print(f"[bold]model:[/bold] {resp.model}")
    console.print(f"[bold]reply:[/bold] {resp.text.strip()}")
    console.print(
        f"[bold]tokens:[/bold] in={resp.tokens_in} out={resp.tokens_out}  "
        f"[bold]cost:[/bold] ${(resp.cost_usd or 0):.5f}  "
        f"[bold]latency:[/bold] {resp.latency_ms}ms"
    )


if __name__ == "__main__":
    app()
