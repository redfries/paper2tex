"""
paper2tex: extract_bib — Extract bibliography from .docx and generate BibTeX.

Three extraction paths:
  Path A: Active citations (Zotero/Mendeley/EndNote) → parse field codes → CSL JSON → BibTeX
  Path B: Plain text numeric citations [1] → AnyStyle parse → BibTeX
  Path C: Plain text author-year citations → match + parse → BibTeX
All paths: optionally verify against Crossref API for canonical DOIs.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from lxml import etree
except ImportError:
    etree = None  # type: ignore

log = logging.getLogger(__name__)

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}


@dataclass
class BibEntry:
    """A single bibliography entry."""
    key: str                    # BibTeX citation key, e.g., "smith2024deep"
    bib_type: str = "article"  # article, inproceedings, book, misc, etc.
    title: str = ""
    authors: str = ""           # BibTeX-formatted: "Smith, John and Doe, Jane"
    year: str = ""
    journal: str = ""
    booktitle: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    publisher: str = ""
    url: str = ""
    raw_text: str = ""          # Original reference text from docx
    source: str = "parsed"      # "citation_manager", "parsed", "crossref_verified"


@dataclass
class CiteMapping:
    """Maps an in-text citation pattern to a BibTeX key."""
    pattern: str          # The text pattern found, e.g., "[1]" or "(Smith, 2024)"
    keys: list[str]       # BibTeX keys this maps to
    doc_positions: list[int] = field(default_factory=list)  # Paragraph indices


@dataclass
class BibRegistry:
    """All bibliography data extracted from the document."""
    entries: list[BibEntry] = field(default_factory=list)
    cite_mappings: list[CiteMapping] = field(default_factory=list)
    citation_style: str = "numeric"  # "numeric", "author-year", "unknown"
    citation_source: str = "none"    # "zotero", "mendeley", "endnote", "plain_text"
    warnings: list[str] = field(default_factory=list)

    def to_bibtex(self) -> str:
        """Generate a complete .bib file string."""
        lines: list[str] = []
        for entry in self.entries:
            fields: list[str] = []
            for fname in ["title", "authors", "year", "journal", "booktitle",
                          "volume", "number", "pages", "doi", "publisher", "url"]:
                val = getattr(entry, fname, "")
                if val:
                    bib_field = "author" if fname == "authors" else fname
                    # Protect title case with braces
                    if fname == "title":
                        val = f"{{{val}}}"
                    fields.append(f"  {bib_field} = {{{val}}}")

            fields_str = ",\n".join(fields)
            lines.append(f"@{entry.bib_type}{{{entry.key},\n{fields_str}\n}}\n")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "citation_style": self.citation_style,
            "citation_source": self.citation_source,
            "entry_count": len(self.entries),
            "warnings": self.warnings,
            "entries": [
                {"key": e.key, "title": e.title, "year": e.year, "source": e.source}
                for e in self.entries
            ],
        }


# --- Path A: Citation Manager Extraction ---

def _extract_zotero_citations(doc_xml: etree._Element) -> list[dict[str, Any]]:
    """Extract Zotero CSL JSON from field codes."""
    citations: list[dict[str, Any]] = []

    for instr in doc_xml.iter(f"{{{NS['w']}}}instrText"):
        text = instr.text or ""
        if "ADDIN ZOTERO_ITEM CSL_CITATION" in text:
            # Extract JSON payload
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                try:
                    csl_data = json.loads(json_match.group())
                    citations.append(csl_data)
                except json.JSONDecodeError:
                    log.warning("Failed to parse Zotero CSL JSON")

    return citations


def _csl_to_bibtex(csl_items: list[dict]) -> list[BibEntry]:
    """Convert CSL JSON items to BibEntry objects."""
    entries: list[BibEntry] = []

    for item in csl_items:
        # Handle nested citationItems (Zotero wraps items)
        items_list = item.get("citationItems", [item])
        for ci in items_list:
            item_data = ci.get("itemData", ci)

            # Generate citation key
            authors = item_data.get("author", [])
            year = ""
            issued = item_data.get("issued", {})
            if "date-parts" in issued and issued["date-parts"]:
                year = str(issued["date-parts"][0][0])

            first_author = ""
            if authors:
                first_author = authors[0].get("family", "unknown").lower()

            title_words = item_data.get("title", "").split()
            short_word = title_words[0].lower() if title_words else "ref"
            key = f"{first_author}{year}{short_word}"
            key = re.sub(r"[^a-zA-Z0-9]", "", key)

            # Format authors for BibTeX
            author_strs = []
            for a in authors:
                family = a.get("family", "")
                given = a.get("given", "")
                if family:
                    author_strs.append(f"{family}, {given}" if given else family)
            authors_bib = " and ".join(author_strs)

            # Map CSL type to BibTeX type
            csl_type = item_data.get("type", "article-journal")
            bib_type_map = {
                "article-journal": "article",
                "paper-conference": "inproceedings",
                "book": "book",
                "chapter": "incollection",
                "thesis": "phdthesis",
                "report": "techreport",
            }
            bib_type = bib_type_map.get(csl_type, "misc")

            entries.append(BibEntry(
                key=key,
                bib_type=bib_type,
                title=item_data.get("title", ""),
                authors=authors_bib,
                year=year,
                journal=item_data.get("container-title", ""),
                volume=str(item_data.get("volume", "")),
                number=str(item_data.get("issue", "")),
                pages=item_data.get("page", ""),
                doi=item_data.get("DOI", ""),
                source="citation_manager",
            ))

    return entries


# --- Path B: Plain Text Reference Parsing ---

def _extract_references_section(doc_xml: etree._Element) -> list[str]:
    """Find the References/Bibliography section and extract each reference as text."""
    body = doc_xml.find(".//w:body", namespaces=NS)
    if body is None:
        return []

    paragraphs = body.findall("w:p", namespaces=NS)
    ref_start_idx: int | None = None

    # Find the References heading
    for i, para in enumerate(paragraphs):
        pPr = para.find("w:pPr", namespaces=NS)
        text = _get_paragraph_text(para).strip()
        cleaned = re.sub(r"^[\d\.\sIVXLCDMivxlcdm\:\-]+", "", text).strip().lower()

        if pPr is not None:
            pStyle = pPr.find("w:pStyle", namespaces=NS)
            if pStyle is not None:
                style = pStyle.get(f"{{{NS['w']}}}val", "")
                if "heading" in style.lower():
                    if cleaned in ("references", "bibliography", "works cited",
                                "reference", "literature", "cited references") or "reference" in cleaned:
                        ref_start_idx = i + 1
                        break

        # Also check plain text (some students don't use heading style)
        if cleaned in ("references", "bibliography", "works cited", "reference", "literature") or (
            ("reference" in cleaned or "bibliography" in cleaned) and len(text.split()) <= 4
        ):
            ref_start_idx = i + 1
            break

    if ref_start_idx is None:
        return []

    # Collect reference paragraphs until next heading or end
    references: list[str] = []
    for i in range(ref_start_idx, len(paragraphs)):
        para = paragraphs[i]

        # Stop at next heading
        pPr = para.find("w:pPr", namespaces=NS)
        if pPr is not None:
            pStyle = pPr.find("w:pStyle", namespaces=NS)
            if pStyle is not None:
                style = pStyle.get(f"{{{NS['w']}}}val", "")
                if "heading" in style.lower():
                    break

        text = _get_paragraph_text(para).strip()
        if text:
            references.append(text)

    log.info("Found %d reference entries in References section", len(references))
    return references


def _parse_reference_text(ref_text: str, index: int) -> BibEntry:
    """Parse a single reference text string into a BibEntry.

    Uses heuristics to extract author, year, title, journal.
    This is a basic parser; for production use AnyStyle or GROBID.
    """
    # Try to extract year
    year_match = re.search(r"(?:19|20)\d{2}", ref_text)
    year = year_match.group() if year_match else ""

    # Try to extract DOI
    doi_match = re.search(r"10\.\d{4,}/[^\s,]+", ref_text)
    doi = doi_match.group().rstrip(".") if doi_match else ""

    # Clean leading citation number like [1] or 1.
    cleaned_text = re.sub(r"^\[\d+\]\s*", "", ref_text).strip()
    cleaned_text = re.sub(r"^\d+\.\s*", "", cleaned_text).strip()

    title = ""
    authors = ""

    # Check for quoted title: "Title" or “Title”
    quote_match = re.search(r'["“](.+?)["”]', cleaned_text)
    if quote_match:
        title = quote_match.group(1).strip()
        # Authors are typically before the quote
        authors_part = cleaned_text[:quote_match.start()].strip().rstrip(",.")
        authors = authors_part
    else:
        # Heuristic: split by commas / periods around year
        if year_match:
            before_year = cleaned_text[:year_match.start()].strip().rstrip(",.(")
            after_year = cleaned_text[year_match.end():].strip().lstrip(",.):")

            parts = [p.strip() for p in before_year.split(".") if p.strip()]
            if len(parts) >= 2:
                authors = parts[0]
                title = ".".join(parts[1:]).strip()
            elif after_year:
                authors = before_year
                title_parts = after_year.split(".", 1)
                title = title_parts[0].strip().strip('"').strip("'")
            else:
                authors = before_year
                title = before_year
        else:
            title = cleaned_text[:100]
            authors = cleaned_text[:50]

    # Generate key
    first_word = re.sub(r"[^a-zA-Z0-9]", "", authors.split(",")[0].split()[-1] if authors else "ref").lower()
    title_word = re.sub(r"[^a-zA-Z0-9]", "", title.split()[0] if title else "unknown").lower()
    key = f"{first_word}{year}{title_word}"

    return BibEntry(
        key=key,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        raw_text=ref_text,
        source="parsed",
    )


def _detect_citation_style(doc_xml: etree._Element) -> str:
    """Detect whether citations are numeric [1] or author-year (Smith, 2024)."""
    body = doc_xml.find(".//w:body", namespaces=NS)
    if body is None:
        return "unknown"

    full_text = ""
    for para in body.findall("w:p", namespaces=NS):
        full_text += _get_paragraph_text(para) + " "

    numeric_count = len(re.findall(r"\[\d+(?:[-–,]\s*\d+)*\]", full_text))
    authoryear_count = len(re.findall(
        r"\([A-Z][a-z]+(?:\s+(?:et\s+al\.?|and\s+[A-Z][a-z]+))?,?\s*(?:19|20)\d{2}\)",
        full_text,
    ))

    if numeric_count > authoryear_count:
        return "numeric"
    elif authoryear_count > 0:
        return "author-year"
    return "unknown"


def _build_cite_mappings_numeric(
    doc_xml: etree._Element,
    entries: list[BibEntry],
) -> list[CiteMapping]:
    """Map [N] patterns to BibTeX keys for numeric citations."""
    mappings: list[CiteMapping] = []
    body = doc_xml.find(".//w:body", namespaces=NS)
    if body is None:
        return mappings

    for para_idx, para in enumerate(body.findall("w:p", namespaces=NS)):
        text = _get_paragraph_text(para)
        for m in re.finditer(r"\[(\d+(?:[-–,]\s*\d+)*)\]", text):
            pattern = m.group()
            # Parse the numbers
            nums_str = m.group(1)
            nums: list[int] = []
            for part in re.split(r"[,\s]+", nums_str):
                range_match = re.match(r"(\d+)[-–](\d+)", part)
                if range_match:
                    start, end = int(range_match.group(1)), int(range_match.group(2))
                    nums.extend(range(start, end + 1))
                elif part.isdigit():
                    nums.append(int(part))

            keys = []
            for n in nums:
                if 1 <= n <= len(entries):
                    keys.append(entries[n - 1].key)

            if keys:
                mappings.append(CiteMapping(
                    pattern=pattern,
                    keys=keys,
                    doc_positions=[para_idx],
                ))

    return mappings


def _get_paragraph_text(para) -> str:
    """Extract plain text from a paragraph element."""
    texts = []
    for t in para.iter(f"{{{NS['w']}}}t"):
        if t.text:
            texts.append(t.text)
    return "".join(texts)


# --- Crossref Verification ---

def _verify_with_crossref(entries: list[BibEntry], timeout: int = 10) -> list[BibEntry]:
    """Verify and enrich BibTeX entries using Crossref API.

    Only called if requests is available and entries have enough info.
    """
    try:
        import requests
    except ImportError:
        log.info("requests not available — skipping Crossref verification")
        return entries

    verified = []
    for entry in entries:
        if entry.source == "citation_manager":
            # Already high quality from citation manager
            verified.append(entry)
            continue

        query = entry.title or entry.raw_text[:200]
        if not query or len(query) < 10:
            verified.append(entry)
            continue

        try:
            resp = requests.get(
                "https://api.crossref.org/works",
                params={
                    "query.bibliographic": query,
                    "rows": 1,
                    "mailto": "paper2tex@example.com",
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("message", {}).get("items", [])
                if items:
                    item = items[0]
                    # Only accept if title is a reasonable match
                    cr_title = item.get("title", [""])[0].lower()
                    our_title = entry.title.lower()
                    if our_title and (
                        our_title[:30] in cr_title or cr_title[:30] in our_title
                    ):
                        entry.doi = entry.doi or item.get("DOI", "")
                        if not entry.journal:
                            entry.journal = (item.get("container-title") or [""])[0]
                        if not entry.volume:
                            entry.volume = item.get("volume", "")
                        if not entry.pages:
                            entry.pages = item.get("page", "")
                        entry.source = "crossref_verified"
                        log.debug("Crossref match: %s", entry.key)

        except Exception as e:
            log.debug("Crossref lookup failed for %s: %s", entry.key, e)

        verified.append(entry)

    verified_count = sum(1 for e in verified if e.source == "crossref_verified")
    log.info("Crossref verified %d / %d entries", verified_count, len(entries))
    return verified


# --- Main Entry Point ---

def extract_bibliography(
    docx_path: Path,
    work_dir: Path,
    citation_type: str = "none",
    verify_crossref: bool = True,
) -> BibRegistry:
    """Extract bibliography from a .docx and generate BibTeX.

    Args:
        docx_path: Path to the .docx file
        work_dir: Working directory for output files
        citation_type: Pre-detected citation manager type from preprocess step
        verify_crossref: Whether to verify entries against Crossref API

    Returns:
        BibRegistry with all entries and cite mappings
    """
    if etree is None:
        raise ImportError("lxml is required: pip install lxml")

    registry = BibRegistry()
    work_dir.mkdir(parents=True, exist_ok=True)

    # Parse document XML
    with zipfile.ZipFile(docx_path, "r") as zf:
        with zf.open("word/document.xml") as f:
            doc_tree = etree.parse(f)
    doc_xml = doc_tree.getroot()

    # Detect citation style
    registry.citation_style = _detect_citation_style(doc_xml)
    registry.citation_source = citation_type

    # Path A: Citation manager detected
    if citation_type == "zotero":
        csl_items = _extract_zotero_citations(doc_xml)
        if csl_items:
            registry.entries = _csl_to_bibtex(csl_items)
            registry.citation_source = "zotero"
            log.info("Extracted %d entries from Zotero field codes", len(registry.entries))

    # Path B/C: Plain text references
    if not registry.entries:
        ref_texts = _extract_references_section(doc_xml)
        if ref_texts:
            registry.entries = [
                _parse_reference_text(text, i)
                for i, text in enumerate(ref_texts)
            ]
            registry.citation_source = "plain_text"

            # Verify with Crossref
            if verify_crossref:
                registry.entries = _verify_with_crossref(registry.entries)

    # Build cite mappings
    if registry.citation_style == "numeric":
        registry.cite_mappings = _build_cite_mappings_numeric(doc_xml, registry.entries)

    # Warnings
    if not registry.entries:
        registry.warnings.append("No references found in document.")
    else:
        unparsed = [e for e in registry.entries if not e.title and not e.doi]
        if unparsed:
            registry.warnings.append(
                f"{len(unparsed)} references could not be parsed. "
                "Consider using a reference manager (Zotero recommended) for better extraction."
            )

    # Write .bib file
    bib_path = work_dir / "references.bib"
    bib_path.write_text(registry.to_bibtex(), encoding="utf-8", newline="\n")
    log.info("Wrote %d BibTeX entries to %s", len(registry.entries), bib_path)

    # Write registry JSON
    reg_path = work_dir / "bib_registry.json"
    reg_path.write_text(
        json.dumps(registry.to_dict(), indent=2),
        encoding="utf-8", newline="\n",
    )

    return registry


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python extract_bib.py <input.docx> <work_dir> [--no-crossref]")
        sys.exit(1)

    docx_path = Path(sys.argv[1])
    work_dir = Path(sys.argv[2])
    verify = "--no-crossref" not in sys.argv

    registry = extract_bibliography(docx_path, work_dir, verify_crossref=verify)
    print(json.dumps(registry.to_dict(), indent=2))


if __name__ == "__main__":
    main()
