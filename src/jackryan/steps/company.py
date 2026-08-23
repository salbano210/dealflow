"""Small helpers for creating and resolving company records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jackryan.db.models import Company


class CompanyNotFound(RuntimeError):
    pass


def create_company(
    session: Session,
    *,
    name: str,
    website: str | None = None,
    source: str | None = None,
) -> Company:
    company = Company(name=name, website=website, source=source, status="new")
    session.add(company)
    session.flush()
    return company


def get_company(session: Session, company_id: int) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise CompanyNotFound(f"No company with id={company_id}")
    return company


def resolve_company(
    session: Session,
    *,
    company_id: int | None = None,
    company_name: str | None = None,
    create_if_missing_name: bool = False,
    source: str | None = None,
) -> Company:
    """Resolve a company by id or name.

    If only a name is given and no match exists, optionally create it
    (used by the CIM-first ingestion path so you aren't gated on the
    company already existing).
    """
    if company_id is not None:
        return get_company(session, company_id)
    if company_name is None:
        raise ValueError("Provide either company_id or company_name.")

    existing = session.execute(
        select(Company).where(Company.name == company_name)
    ).scalars().first()
    if existing:
        return existing
    if create_if_missing_name:
        return create_company(session, name=company_name, source=source)
    raise CompanyNotFound(f"No company named '{company_name}'.")
