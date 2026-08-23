"""Push/pull sync between SQLite (source of truth) and Airtable (review UI)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import yaml

from dealflow.config import AppConfig
from dealflow.db.models import Company
from dealflow.db.session import get_session
from dealflow.steps.attributes import current_attributes

_AIRTABLE_API = "https://api.airtable.com/v0"


class AirtableSyncError(RuntimeError):
    pass


def _load_sync_config() -> dict:
    path = Path(__file__).resolve().parents[3] / "config" / "airtable.yaml"
    if not path.exists():
        raise AirtableSyncError(f"Missing config: {path}")
    with path.open() as f:
        return yaml.safe_load(f)


def _headers() -> dict[str, str]:
    key = os.environ.get("AIRTABLE_API_KEY")
    if not key:
        raise AirtableSyncError(
            "AIRTABLE_API_KEY not set. Add it to .env and re-run."
        )
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _base_url(cfg: dict) -> str:
    base_id = os.environ.get("AIRTABLE_BASE_ID") or cfg.get("base_id", "")
    if not base_id:
        raise AirtableSyncError(
            "AIRTABLE_BASE_ID not set. Add it to .env or config/airtable.yaml"
        )
    table = cfg.get("table_name", "Companies")
    return f"{_AIRTABLE_API}/{base_id}/{table}"


def _build_record_fields(
    cfg: dict, company: Company, attrs: dict, app_config: AppConfig
) -> dict[str, Any]:
    """Build the Airtable fields dict for one company."""
    fields_cfg = cfg.get("fields", {})
    record: dict[str, Any] = {}

    for airtable_field, source in fields_cfg.items():
        if source.startswith("company."):
            attr = source.split(".", 1)[1]
            record[airtable_field] = getattr(company, attr, None)
        elif source.startswith("kpi."):
            kpi_key = source.split(".", 1)[1]
            if kpi_key in attrs:
                record[airtable_field] = attrs[kpi_key].value
        elif source.startswith("computed."):
            name = source.split(".", 1)[1]
            if name == "data_completeness":
                required = app_config.required_kpi_keys()
                if required:
                    known = sum(
                        1 for k in required
                        if k in attrs and attrs[k].state == "known"
                    )
                    record[airtable_field] = round(known / len(required), 2)
                else:
                    record[airtable_field] = 1.0

    # Strip None values so Airtable doesn't overwrite with blanks
    return {k: v for k, v in record.items() if v is not None}


def push_all(app_config: AppConfig) -> dict[str, int]:
    """Push all companies to Airtable. Returns counts."""
    cfg = _load_sync_config()
    base_url = _base_url(cfg)
    headers = _headers()

    with get_session() as s:
        companies = s.query(Company).all()
        results = {"created": 0, "updated": 0, "errors": 0}

        for company in companies:
            attrs = current_attributes(s, company.id)
            fields = _build_record_fields(cfg, company, attrs, app_config)

            try:
                if company.airtable_record_id:
                    # Update existing
                    url = f"{base_url}/{company.airtable_record_id}"
                    resp = httpx.patch(url, json={"fields": fields}, headers=headers, timeout=30)
                    resp.raise_for_status()
                    results["updated"] += 1
                else:
                    # Create new
                    resp = httpx.post(base_url, json={"fields": fields}, headers=headers, timeout=30)
                    resp.raise_for_status()
                    record_id = resp.json()["id"]
                    company.airtable_record_id = record_id
                    results["created"] += 1
            except httpx.HTTPError as e:
                print(f"  [red]Error syncing {company.name}: {e}[/red]")
                results["errors"] += 1

    return results


def pull_all(app_config: AppConfig) -> dict[str, int]:
    """Pull human edits from Airtable back to DB. Returns counts."""
    cfg = _load_sync_config()
    base_url = _base_url(cfg)
    headers = _headers()
    human_fields = set(cfg.get("human_editable_fields", []))

    results = {"updated": 0, "skipped": 0, "errors": 0}

    try:
        resp = httpx.get(base_url, headers=headers, timeout=30)
        resp.raise_for_status()
        records = resp.json().get("records", [])
    except httpx.HTTPError as e:
        raise AirtableSyncError(f"Failed to fetch Airtable: {e}")

    with get_session() as s:
        for record in records:
            record_id = record["id"]
            fields = record.get("fields", {})

            # Find company by airtable_record_id
            company = s.query(Company).filter_by(airtable_record_id=record_id).first()
            if not company:
                results["skipped"] += 1
                continue

            changed = False
            for field_name, value in fields.items():
                if field_name not in human_fields:
                    continue

                # Map Airtable field back to company attribute
                fields_cfg = cfg.get("fields", {})
                source = fields_cfg.get(field_name)
                if not source or not source.startswith("company."):
                    continue

                attr = source.split(".", 1)[1]
                current = getattr(company, attr, None)
                if current != value:
                    setattr(company, attr, value)
                    changed = True

            if changed:
                results["updated"] += 1

    return results
