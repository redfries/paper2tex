"""
paper2tex: docling_extract — Optional Docling-based extraction for complex documents.

IBM Docling provides superior table reconstruction (TableFormer) and OMML handling
for documents where Pandoc struggles. This module is optional — it requires
PyTorch and the docling package (pip install docling).

Use when:
  - Tables have complex merged cells that extract_tables.py flags as problematic
  - OMML math with unusual accents or nested structures
  - Multi-column layouts with interleaved text and figures
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class DoclingResult:
    """Result of Docling-based extraction."""
    available: bool = False
    markdown: str = ""
    tables: list[dict] = field(default_factory=list)
    equations: list[dict] = field(default_factory=list)
    figures: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def is_docling_available() -> bool:
    """Check if docling is installed and importable."""
    try:
        import docling  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


def extract_with_docling(docx_path: Path, work_dir: Path) -> DoclingResult:
    """Extract document content using IBM Docling.

    This is a fallback/upgrade path for documents where Pandoc struggles.
    Requires: pip install docling

    Args:
        docx_path: Path to the .docx file
        work_dir: Working directory for output

    Returns:
        DoclingResult with extracted content
    """
    result = DoclingResult()

    if not is_docling_available():
        result.warnings.append(
            "Docling is not installed. For improved table and math extraction, "
            "install it with: pip install docling "
            "(requires PyTorch — approximately 2-4 GB disk space)"
        )
        return result

    try:
        from docling.document_converter import DocumentConverter  # type: ignore

        converter = DocumentConverter()
        doc_result = converter.convert(str(docx_path))

        result.available = True

        # Export as Markdown
        result.markdown = doc_result.document.export_to_markdown()
        md_path = work_dir / "docling_content.md"
        md_path.write_text(result.markdown, encoding="utf-8", newline="\n")

        # Extract tables with structure
        for i, table in enumerate(doc_result.document.tables):
            table_data = {
                "index": i,
                "num_rows": table.num_rows if hasattr(table, "num_rows") else 0,
                "num_cols": table.num_cols if hasattr(table, "num_cols") else 0,
                "markdown": table.export_to_markdown() if hasattr(table, "export_to_markdown") else "",
            }
            result.tables.append(table_data)

        # Export structured JSON
        json_export = doc_result.document.export_to_dict()
        json_path = work_dir / "docling_export.json"
        json_path.write_text(
            json.dumps(json_export, indent=2, default=str),
            encoding="utf-8", newline="\n",
        )

        log.info(
            "Docling extraction complete: %d tables, %d chars of markdown",
            len(result.tables), len(result.markdown),
        )

    except Exception as e:
        result.warnings.append(f"Docling extraction failed: {e}")
        log.error("Docling extraction failed: %s", e, exc_info=True)

    return result


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not is_docling_available():
        print("❌ Docling is not installed.")
        print("   Install with: pip install docling")
        print("   Note: requires PyTorch (~2-4 GB)")
        sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: python docling_extract.py <input.docx> <work_dir>")
        sys.exit(1)

    docx_path = Path(sys.argv[1])
    work_dir = Path(sys.argv[2])
    work_dir.mkdir(parents=True, exist_ok=True)

    result = extract_with_docling(docx_path, work_dir)
    if result.available:
        print(f"✅ Docling extraction complete: {len(result.tables)} tables")
    else:
        print("❌ Docling extraction failed")
        for w in result.warnings:
            print(f"   {w}")


if __name__ == "__main__":
    main()
