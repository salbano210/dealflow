"""Website main-content fetcher.

Deterministic. No LLM. Fetches a URL and extracts the primary readable
content with trafilatura (strips nav, ads, boilerplate).
"""

from __future__ import annotations

import httpx
import trafilatura

from dealflow.sources.base import SourceDocument

_DEFAULT_TIMEOUT = 20.0
_USER_AGENT = "dealflow/0.1 (+https://github.com/salbano210/dealflow)"


class WebsiteFetchError(RuntimeError):
    """Raised when a URL cannot be fetched or yields no usable content."""


def _normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def fetch_website(url: str, *, timeout: float = _DEFAULT_TIMEOUT) -> SourceDocument:
    """Fetch `url` and return its main content as a SourceDocument.

    Raises WebsiteFetchError on network failure or empty extraction.
    """
    full_url = _normalize_url(url)
    try:
        resp = httpx.get(
            full_url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise WebsiteFetchError(f"Failed to fetch {full_url}: {e}") from e

    extracted = trafilatura.extract(
        resp.text,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    if not extracted or not extracted.strip():
        raise WebsiteFetchError(
            f"No readable content extracted from {full_url}. "
            f"The page may be JavaScript-rendered or empty."
        )

    return SourceDocument(
        kind="website",
        text=extracted.strip(),
        url_or_path=full_url,
        allow_external_llm=True,
    )
