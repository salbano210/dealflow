"""CIM (Confidential Information Memorandum) PDF parser.

Deterministic. No LLM. Extracts text from a PDF into a SourceDocument.

Handles both text-based PDFs (via pypdf) and scanned/image-only PDFs
(via PyMuPDF OCR fallback). Raises a clear error if neither works.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from dealflow.sources.base import SourceDocument

# Below this many extracted characters we try OCR fallback.
_MIN_TEXT_CHARS = 200


class CimParseError(RuntimeError):
    """Raised when a CIM PDF cannot be parsed into usable text."""


def _extract_with_pypdf(path: Path) -> str:
    """Extract text using pypdf. Returns empty string on failure."""
    try:
        reader = PdfReader(str(path))
    except PdfReadError:
        return ""

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            return ""

    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue

    return "\n\n".join(part.strip() for part in parts if part.strip())


def _extract_with_ocr(path: Path) -> str:
    """Extract text using ocrmypdf + PyMuPDF. Returns empty string on failure."""
    import tempfile

    try:
        import ocrmypdf
        import pymupdf
    except ImportError:
        return ""

    # Create a temp file for the OCR'd output
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Run ocrmypdf on the input PDF
        ocrmypdf.ocr(
            input_file=str(path),
            output_file=tmp_path,
            skip_text=True,  # Only OCR pages without text
            progress_bar=False,
            quiet=True,
        )

        # Extract text from the OCR'd PDF using PyMuPDF
        doc = pymupdf.open(tmp_path)
        parts: list[str] = []
        for page in doc:
            try:
                parts.append(page.get_text())
            except Exception:
                continue
        doc.close()
        return "\n\n".join(part.strip() for part in parts if part.strip())
    except Exception:
        return ""
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


def parse_cim(path: str | Path, *, allow_external_llm: bool = True) -> SourceDocument:
    """Parse a CIM PDF at `path` into a SourceDocument.

    Raises CimParseError with an actionable message on failure.
    """
    p = Path(path)
    if not p.exists():
        raise CimParseError(f"File not found: {p}")
    if p.suffix.lower() != ".pdf":
        raise CimParseError(f"Expected a .pdf file, got: {p.name}")

    # Try pypdf first (faster, no OCR needed for text-based PDFs)
    text = _extract_with_pypdf(p)

    # If we got little/no text, try OCR via PyMuPDF
    if len(text) < _MIN_TEXT_CHARS:
        ocr_text = _extract_with_ocr(p)
        if len(ocr_text) > len(text):
            text = ocr_text

    if len(text) < _MIN_TEXT_CHARS:
        raise CimParseError(
            f"Extracted only {len(text)} characters from {p.name}. "
            f"This PDF may be encrypted, corrupted, or entirely image-based "
            f"with no OCR-able text. Try running it through a dedicated OCR "
            f"tool (e.g., ocrmypdf) first."
        )

    return SourceDocument(
        kind="cim",
        text=text,
        url_or_path=str(p),
        allow_external_llm=allow_external_llm,
    )
