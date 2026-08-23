"""SQLite database layer.

The DB is the source of truth. Airtable is a projected view.
Schema uses an EAV pattern for extracted attributes so that adding a new
KPI in kpis.yaml requires zero DB migrations.
"""

from dealflow.db.session import get_engine, get_session, init_db
from dealflow.db import models  # re-exported for Alembic

__all__ = ["get_engine", "get_session", "init_db", "models"]
