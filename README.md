# dealflow

**AI-augmented sourcing & screening for growth-equity analysts.**

`dealflow` automates the repetitive information-processing layer between company
sourcing and human investment judgment. Upload a CIM, get structured KPIs with
evidence and provenance — no manual data entry.

---

## What it does

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────→│   Extract   │────→│   Merge &   │────→│   Sync to   │
│    CIM      │     │    KPIs     │     │   Score     │     │  Airtable   │
│   (PDF)     │     │  (LLM)      │     │  (Python)   │     │  (Review)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  58-page scanned     13 structured      Trust-tier merge      Human review
  PDF → OCR           fields with        + conflict flags      + approve/reject
                      evidence
```

**Key features:**
- **CIM ingestion** — handles scanned PDFs via OCR (RapidOCR)
- **Structured extraction** — LLM pulls KPIs into typed, validated fields
- **Provenance** — every value links to source text + evidence quote
- **Configurable** — thesis, KPIs, weights, models all YAML-editable
- **Cost-tracked** — every LLM call logged with tokens + USD cost
- **Airtable sync** — push to your review dashboard, pull human edits back

---

## Quick start

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/salbano210/dealflow.git
cd dealflow
uv sync
cp .env.example .env   # add your OpenRouter key
uv run dealflow db init
```

### Ingest a CIM

```bash
uv run dealflow ingest-cim examples/cims/cus_cim.pdf --company-name "Consolidated Utility Services"
```

**Output:**
```
Trying pypdf extraction on cus_cim.pdf...
pypdf extracted 0 chars, falling back to OCR (this may take 1-3 minutes)...
  OCR page 1/58... got 1245 chars
  OCR page 2/58... got 892 chars
  ...
OK -- CIM stored for company id=1, source id=1, 10 KPI rows extracted.
```

### View extracted KPIs

```bash
uv run dealflow show 1
```

**Output:**
```
Consolidated Utility Services (id=1) — status=new
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ KPI               ┃ Value          ┃ State ┃ Conf ┃ Evidence           ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ business_model    │ pure_services  │ infer │ 0.80 │ "locating services │
│                   │                │       │      │  account for 98%"  │
│ estimated_revenue │ $57.4M         │ known │ 1.00 │ "Revenue $57,442   │
│                   │                │       │      │  (in thousands)"   │
│ growth_rate_yoy   │ 4.1%           │ known │ 1.00 │ "Growth Rate 4.1%" │
│ founder_led       │ True           │ known │ 1.00 │ "Rob Karam is a    │
│                   │                │       │      │  co-founder"       │
│ geography         │ US             │ known │ 1.00 │ "Omaha, Nebraska"  │
│ employee_count    │ 734            │ known │ 1.00 │ "734 employees"    │
│ customer_conc.    │ Top 10 = 53.5% │ known │ 1.00 │ "Top 10 customers  │
│                   │                │       │      │  accounted for..." │
└───────────────────┴────────────────┴───────┴────┴──────────────────────┘
```

### Sync to Airtable

```bash
uv run dealflow sync-airtable
```

Push companies to your Airtable base for human review. Pull edits back with `--pull`.

---

## Configuration

Everything is YAML. No code changes needed.

| File | What it controls |
|---|---|
| `config/thesis.yaml` | Investment thesis: hard filters, soft criteria, cost guardrails |
| `config/kpis.yaml` | Fields to extract (revenue, growth, founder status, etc.) |
| `config/weights.yaml` | Scoring dimensions + weights (LLM or deterministic) |
| `config/models.yaml` | Which LLM to use per step (OpenRouter) |
| `config/airtable.yaml` | Field mappings, status mappings, editable fields |

**Add a new KPI:** edit `config/kpis.yaml` → done. No migration, no code.

**Swap models:** edit `config/models.yaml` → done. Works with any OpenRouter model.

---

## Example data

Real extractions from two CIMs in `examples/`:

| Company | Revenue | Growth | Business Model | Data Completeness |
|---|---|---|---|---|
| Consolidated Utility Services | $57.4M | 4.1% | pure_services | 80% |
| American Casino | $429.7M | 4.9% | other | 40% |

Both extracted from scanned PDFs with full evidence provenance.

---

## Architecture

```
config/     YAML configs (thesis, KPIs, weights, models, Airtable)
db/         SQLite + SQLAlchemy (source of truth, audit log)
sources/    CIM parser (pypdf + RapidOCR), website scraper
llm/        OpenRouter client (structured outputs, cost logging)
steps/      Pipeline: enrich → extract → merge → score → sync
sync/       Airtable push/pull
cli/        Typer entrypoint
examples/   Sample CIMs + extracted JSON fixtures
```

**Design principles:**
1. **Configuration over code** — change behavior via YAML, not Python
2. **Deterministic glue, probabilistic leaves** — LLMs only for extraction/judgment
3. **Every call logged** — prompt, response, tokens, cost, latency
4. **Human-in-the-loop** — AI drafts, human approves
5. **Provenance for every claim** — trace any value to its source text

---

## Cost

Typical CIM extraction: **$0.01–0.03** (Gemini 2.5 Flash Lite)

All calls logged to `llm_calls` table with cost, tokens, latency.

---

## License

MIT — see [`LICENSE`](./LICENSE).
