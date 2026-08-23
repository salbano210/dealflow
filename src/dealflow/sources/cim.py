"""CIM (Confidential Information Memorandum) PDF parser.

Deterministic. No LLM. Extracts text from a PDF into a SourceDocument.

Known limitations (documented, not silently swallowed):
- Image-only / scanned PDFs produce little or no text. We detect this and
  raise a clear error suggesting OCR, rather than returning empty text that
  would later confuse extraction.
- Encrypted PDFs without a password raise a clear error.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from dealflow.sources.base import SourceDocument

# Below this many extracted characters we assume the PDF is image-only.
_MIN_TEXT_CHARS = 200


class CimParseError(RuntimeError):
    """Raised when a CIM PDF cannot be parsed into usable text."""


def parse_cim(path: str | Path, *, allow_external_llm: bool = True) -> SourceDocument:
    """Parse a CIM PDF at `path` into a SourceDocument.

    Raises CimParseError with an actionable message on failure.
    """
    p = Path(path)
    if not p.exists():
        raise CimParseError(f"File not found: {p}")
    if p.suffix.lower() != ".pdf":
        raise CimParseError(f"Expected a .pdf file, got: {p.name}")

    try:
        reader = PdfReader(str(p))
    except PdfReadError as e:
        raise CimParseError(f"Could not read PDF ({p.name}): {e}") from e

    if reader.is_encrypted:
        # pypdf can sometimes decrypt with an empty password; try once.
        try:
            reader.decrypt("")
        except Exception as e:
            raise CimParseError(
                f"PDF is encrypted and could not be opened without a password: {p.name}"
            ) from e

    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            # A single bad page shouldn't kill the whole document.
            continue

    text = "\n\n".join(part.strip() for part in parts if part.strip())

    if len(text) < _MIN_TEXT_CHARS:
        raise CimParseError(
            f"Extracted only {len(text)} characters from {p.name}. "
            f"This is likely a scanned / image-only PDF. OCR is not yet "
            f"supported; run the file through an OCR tool first."
        )

    return SourceDocument(
        kind="cim",
        text=text,
        url_or_path=str(p),
        allow_external_llm=allow_external_llm,
    )
