"""Shared types for evidence sources."""

from __future__ import annotations

from dataclasses import dataclass

# Trust tiers used when merging conflicting KPI values. Higher wins.
TRUST_TIERS: dict[str, int] = {
    "cim": 3,
    "user_note": 3,
    "website": 2,
    "news": 1,
}


@dataclass
class SourceDocument:
    """The output of any source fetcher: raw text plus metadata.

    This is a plain data object -- persisting it to `raw_sources` is the
    caller's job (see steps/enrich.py).
    """

    kind: str                       # 'cim' | 'website' | 'news' | 'user_note'
    text: str
    url_or_path: str | None = None
    allow_external_llm: bool = True

    @property
    def trust_tier(self) -> int:
        return TRUST_TIERS.get(self.kind, 1)

    def is_usable(self) -> bool:
        """A source is usable if it produced a non-trivial amount of text."""
        return bool(self.text and len(self.text.strip()) >= 40)
