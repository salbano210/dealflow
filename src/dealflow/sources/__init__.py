"""Evidence sources.

Each source fetches unstructured text and returns a `SourceDocument`.
No LLM calls happen here -- sources only gather and store raw text into
`raw_sources`. The extraction step (steps/extract.py) turns that text
into structured KPIs.

Trust tiers (higher wins in merge conflicts):
    cim        = 3   (analyst-provided, authoritative)
    user_note  = 3
    website    = 2
    news       = 1
"""

from dealflow.sources.base import SourceDocument, TRUST_TIERS

__all__ = ["SourceDocument", "TRUST_TIERS"]
