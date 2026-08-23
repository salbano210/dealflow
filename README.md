# jack_rAIn

**An AI-augmented sourcing & screening workflow for growth-equity investment analysts.**

`jack_rAIn` automates the repetitive information-processing layer between company
sourcing and human investment judgment. Companies enter the pipeline (manually,
via CIM upload, or via a data source), get enriched from available evidence,
evaluated against a **configurable** investment thesis, assigned a transparent
evidence-backed screening score, and routed to an analyst for human review.

This is deliberately **not** another chatbot. It is workflow automation with an
LLM at the leaves.

---

## Design principles

1. **Configuration over code.** The thesis, the KPIs extracted, the scoring
   weights, and the model used at each pipeline step are all YAML files. Change
   any of them without touching Python.
2. **Deterministic glue, probabilistic leaves.** The pipeline is plain Python.
   LLMs are only called for specific, narrow tasks (extract this field, judge
   this dimension, draft this email).
3. **Every LLM call is logged** with prompt, model, tokens, cost, and latency.
4. **Human-in-the-loop for consequential actions.** The system drafts outreach;
   it never sends it.
5. **Provenance for every claim.** Every extracted field points to the source
   text it came from.

---

## Status

Early scaffold. What works today:

- Config loading & validation (`jackryan config validate`)
- SQLite schema init (`jackryan db init`)
- OpenRouter client wired up with structured-output support
- LLM call logging table

Coming next: CIM ingestion, extraction, screening, Airtable sync.

---

## Setup

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/salbano210/jack_rAIn.git
cd jack_rAIn
uv sync                              # creates .venv and installs deps
cp .env.example .env                 # then edit .env and add your OpenRouter key
uv run jackryan config validate      # sanity-check the config files
uv run jackryan db init              # create the SQLite database
uv run jackryan --help
```

You need your own [OpenRouter API key](https://openrouter.ai/keys). The key is
read from `.env`, which is gitignored — no secrets ship with the repo.

---

## Configuration files

Everything a user might reasonably want to change lives in `config/`:

| File | What it controls |
|---|---|
| `config/thesis.yaml` | Investment thesis: hard filters + soft criteria + free-text guidance the LLM sees. |
| `config/kpis.yaml` | The fields the model extracts from CIMs and web sources. |
| `config/weights.yaml` | Scoring dimensions, weights, and rubrics. Supports both LLM-scored and deterministic (builtin) scorers. |
| `config/models.yaml` | Which LLM to use at each pipeline step. Any [OpenRouter-supported model](https://openrouter.ai/models). |

Adding a new KPI: edit `config/kpis.yaml`. No code, no migration.
Adding a new scoring dimension: edit `config/weights.yaml`. No code.
Swapping a model: edit `config/models.yaml`. No code.

---

## Architecture (high level)

```
config/  → thesis.yaml, kpis.yaml, weights.yaml, models.yaml
db/      → SQLite (source of truth) + provenance/audit tables
sources/ → website scrape, news, CIM parser        (planned)
llm/     → OpenRouter client + structured outputs + call logging
steps/   → enrich, extract, screen, research, outreach   (planned)
sync/    → Airtable projection (push + pull)      (planned)
cli/     → Typer entrypoint
```

See `DealFlow_AI_Project_Thesis.md` in the repo root for the full product thesis.

---

## License

MIT — see [`LICENSE`](./LICENSE).
