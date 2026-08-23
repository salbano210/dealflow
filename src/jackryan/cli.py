"""jackryan CLI entrypoint.

Everything a human action touches lives here. Actions on the DB happen
via subcommands; review of results happens via Airtable (future) or by
inspecting the SQLite file directly.

Available today:
  jackryan config validate     -- load & cross-validate all YAML config
  jackryan config show-thesis  -- print the parsed thesis
  jackryan db init             -- create SQLite schema
  jackryan llm ping            -- smoke-test the OpenRouter connection
  jackryan add                 -- add a company (lightweight entry point)
  jackryan ingest-cim          -- add/enrich a company from a CIM PDF
  jackryan enrich              -- fetch website + extract KPIs
  jackryan show                -- print a company's merged KPI picture
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


# ------------------------------------------------------------- companies ----

@app.command("add")
def add_company_cmd(
    name: str = typer.Option(..., "--name", help="Company name"),
    website: str | None = typer.Option(None, "--website", help="Company website"),
    source: str | None = typer.Option(None, "--source", help="How it entered the pipeline"),
) -> None:
    """Add a company (lightweight entry point). Does not run enrichment."""
    from jackryan.db import init_db
    from jackryan.db.session import get_session
    from jackryan.steps.company import create_company

    init_db()
    with get_session() as s:
        company = create_company(s, name=name, website=website, source=source)
        cid = company.id
    console.print(f"[bold green]OK[/bold green] -- added company id={cid}: {name}")


@app.command("ingest-cim")
def ingest_cim_cmd(
    path: str = typer.Argument(..., help="Path to the CIM PDF"),
    company_id: int | None = typer.Option(None, "--company-id", help="Attach to existing company"),
    company_name: str | None = typer.Option(None, "--company-name", help="Existing or new company name"),
    no_external_llm: bool = typer.Option(
        False, "--no-external-llm", help="Flag this source as not sendable to an external LLM"
    ),
    extract: bool = typer.Option(True, help="Run extraction after ingesting"),
) -> None:
    """CIM-first entry point: parse a CIM, store it, and extract KPIs.

    You are not gated on the company already existing -- pass --company-name
    and it will be created if needed.
    """
    from jackryan.db import init_db
    from jackryan.db.session import get_session
    from jackryan.sources.cim import CimParseError
    from jackryan.steps.company import CompanyNotFound, resolve_company
    from jackryan.steps.enrich import enrich_from_cim
    from jackryan.steps.extract import extract_from_source

    init_db()
    cfg = load_all()
    try:
        with get_session() as s:
            company = resolve_company(
                s, company_id=company_id, company_name=company_name,
                create_if_missing_name=True, source="cim_upload",
            )
            cid, cname = company.id, company.name
            src = enrich_from_cim(s, cid, path, allow_external_llm=not no_external_llm)
            src_id = src.id
            written = 0
            if extract and not no_external_llm:
                written = extract_from_source(s, cfg, src, cid)
    except (CimParseError, CompanyNotFound, ValueError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(
        f"[bold green]OK[/bold green] -- CIM stored for company id={cid} ({cname}), "
        f"source id={src_id}, {written} KPI rows extracted."
    )
    if extract and not no_external_llm:
        console.print(f"Run [bold]jackryan show {cid}[/bold] to view the KPI picture.")


@app.command("enrich")
def enrich_cmd(
    company_id: int = typer.Argument(..., help="Company id"),
    extract: bool = typer.Option(True, help="Run extraction after fetching sources"),
) -> None:
    """Fetch the company website and (optionally) extract KPIs from all sources."""
    from jackryan.db import init_db
    from jackryan.db.session import get_session
    from jackryan.sources.website import WebsiteFetchError
    from jackryan.steps.company import CompanyNotFound, get_company
    from jackryan.steps.enrich import enrich_from_website
    from jackryan.steps.extract import extract_company

    init_db()
    cfg = load_all()
    try:
        with get_session() as s:
            company = get_company(s, company_id)
            row_id = None
            try:
                row = enrich_from_website(s, company)
                row_id = row.id if row is not None else None
            except WebsiteFetchError as e:
                console.print(f"[yellow]Website fetch skipped:[/yellow] {e}")
            results: dict[str, int] = {}
            if extract:
                results = extract_company(s, cfg, company_id)
    except CompanyNotFound as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    if row_id is not None:
        console.print(f"[green]Fetched website[/green] -> source id={row_id}")
    if extract:
        total = sum(results.values())
        console.print(f"[bold green]OK[/bold green] -- extracted {total} KPI rows across sources.")
        console.print(f"Run [bold]jackryan show {company_id}[/bold] to view.")


@app.command("show")
def show_cmd(company_id: int = typer.Argument(..., help="Company id")) -> None:
    """Print a company's merged KPI picture with provenance."""
    from jackryan.db import init_db
    from jackryan.db.session import get_session
    from jackryan.steps.attributes import current_attributes
    from jackryan.steps.company import CompanyNotFound, get_company

    init_db()
    try:
        with get_session() as s:
            company = get_company(s, company_id)
            header = f"{company.name} (id={company.id}) — status={company.status}"
            website = company.website or "-"
            attrs = current_attributes(s, company_id)
    except CompanyNotFound as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[bold]{header}[/bold]  website: {website}")
    if not attrs:
        console.print("[yellow]No extracted attributes yet.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("KPI")
    table.add_column("Value")
    table.add_column("State")
    table.add_column("Conf")
    table.add_column("Evidence")
    for key in sorted(attrs):
        a = attrs[key]
        state = a.state + (" ⚠️" if a.conflict else "")
        conf = f"{a.confidence:.2f}" if a.confidence is not None else "-"
        table.add_row(
            key, str(a.value if a.value is not None else "-"),
            state, conf, (a.evidence or "")[:60],
        )
    console.print(table)


if __name__ == "__main__":
    app()
