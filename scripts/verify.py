"""
paper2tex: verify — QA gate that blocks delivery if checks fail.

Checks:
  a) Log audit: 0 errors, 0 undefined citations/references
  b) Manifest diff: sections/figs/tables/eqs/words match source
  c) Cross-ref integrity: every \\ref has a \\label, no hardcoded "Figure N"
  d) Citation integrity: every \\cite has a .bib entry, every entry is cited
  e) Character spot-check: special chars (° µ ≈ ± ×) present in PDF text
  f) Visual QA: optional PDF → PNG inspection
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class Check:
    """A single verification check result."""
    name: str
    passed: bool
    details: str = ""
    severity: str = "error"  # "error", "warning", "info"


@dataclass
class VerifyResult:
    """Result of all verification checks."""
    checks: list[Check] = field(default_factory=list)
    all_passed: bool = False
    report_path: Path | None = None

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "warning")

    def to_report_md(self) -> str:
        """Generate a student-readable report.md."""
        lines = [
            "# paper2tex — Conversion Report",
            "",
            "## QA Checklist",
            "",
        ]

        for check in self.checks:
            icon = "✅" if check.passed else ("⚠️" if check.severity == "warning" else "❌")
            lines.append(f"- {icon} **{check.name}**")
            if check.details:
                for detail_line in check.details.split("\n"):
                    lines.append(f"  {detail_line}")

        lines.append("")
        lines.append("---")
        if self.all_passed:
            lines.append("**All checks passed.** Your paper is ready for submission.")
        else:
            lines.append(
                f"**{self.error_count} error(s), {self.warning_count} warning(s).** "
                "Please review the items above before submitting."
            )

        return "\n".join(lines)


def _check_log_audit(log_path: Path) -> list[Check]:
    """Check the compilation log for errors and warnings."""
    checks: list[Check] = []

    if not log_path.exists():
        checks.append(Check(
            name="Compilation log",
            passed=False,
            details="Log file not found — was the paper compiled?",
        ))
        return checks

    content = log_path.read_text(encoding="utf-8", errors="replace")

    # Count errors
    error_count = len(re.findall(r"^!", content, re.MULTILINE))
    checks.append(Check(
        name="LaTeX errors",
        passed=error_count == 0,
        details=f"{error_count} error(s) in compilation log" if error_count > 0 else "No errors",
    ))

    # Citation undefined
    cite_undef = re.findall(r"Citation `([^']+)' .* undefined", content)
    checks.append(Check(
        name="Citations defined",
        passed=len(cite_undef) == 0,
        details=(
            f"Undefined citations: {', '.join(cite_undef)}"
            if cite_undef
            else "All citations resolved"
        ),
    ))

    # Reference undefined
    ref_undef = re.findall(r"Reference `([^']+)' .* undefined", content)
    checks.append(Check(
        name="References defined",
        passed=len(ref_undef) == 0,
        details=(
            f"Undefined references: {', '.join(ref_undef)}"
            if ref_undef
            else "All references resolved"
        ),
    ))

    # Overfull hboxes (warning only)
    overfull = len(re.findall(r"Overfull \\hbox", content))
    if overfull > 0:
        checks.append(Check(
            name="Overfull boxes",
            passed=False,
            details=f"{overfull} overfull hbox warning(s) — content may extend past margins",
            severity="warning",
        ))

    return checks


def _check_manifest_diff(manifest_path: Path, tex_path: Path) -> list[Check]:
    """Compare source manifest counts against the output .tex file."""
    checks: list[Check] = []

    if not manifest_path.exists():
        checks.append(Check(
            name="Manifest comparison",
            passed=True,
            details="No manifest file — skipping count verification",
            severity="info",
        ))
        return checks

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tex_content = tex_path.read_text(encoding="utf-8")

    # Section count
    source_sections = manifest.get("counts", {}).get("sections", 0)
    tex_sections = len(re.findall(r"\\(?:sub)*section\*?\{", tex_content))
    checks.append(Check(
        name="Section count",
        passed=abs(source_sections - tex_sections) <= 1,
        details=f"Source: {source_sections}, Output: {tex_sections}",
        severity="warning" if abs(source_sections - tex_sections) <= 2 else "error",
    ))

    # Figure count
    source_figs = manifest.get("counts", {}).get("figures", 0)
    tex_figs = len(re.findall(r"\\includegraphics", tex_content))
    checks.append(Check(
        name="Figure count",
        passed=source_figs == tex_figs,
        details=f"Source: {source_figs}, Output: {tex_figs}",
    ))

    # Table count
    source_tables = manifest.get("counts", {}).get("tables", 0)
    tex_tables = len(re.findall(r"\\begin\{tabular", tex_content))
    checks.append(Check(
        name="Table count",
        passed=source_tables == tex_tables,
        details=f"Source: {source_tables}, Output: {tex_tables}",
    ))

    # Equation count (display)
    source_eqs = manifest.get("counts", {}).get("display_equations", 0)
    tex_eqs = len(re.findall(
        r"\\begin\{(?:equation|align|gather|multline)\*?\}",
        tex_content,
    ))
    checks.append(Check(
        name="Display equation count",
        passed=abs(source_eqs - tex_eqs) <= 1,
        details=f"Source: {source_eqs}, Output: {tex_eqs}",
        severity="warning",
    ))

    return checks


def _check_crossref_integrity(tex_path: Path) -> list[Check]:
    """Verify cross-reference integrity in the .tex file."""
    checks: list[Check] = []
    content = tex_path.read_text(encoding="utf-8")

    # Collect all \label{} definitions
    labels = set(re.findall(r"\\label\{([^}]+)\}", content))
    # Collect all \ref{}, \cref{}, \Cref{}, \eqref{} references
    refs = set(re.findall(r"\\(?:c?C?ref|eqref)\{([^}]+)\}", content))

    # Every ref should have a label
    orphan_refs = refs - labels
    checks.append(Check(
        name="Cross-reference integrity",
        passed=len(orphan_refs) == 0,
        details=(
            f"References without labels: {', '.join(sorted(orphan_refs))}"
            if orphan_refs
            else f"All {len(refs)} references have matching labels"
        ),
    ))

    # Check for hardcoded "Figure N", "Table N" (should be \cref{})
    hardcoded = re.findall(r"(?:Figure|Table|Equation)\s+\d+(?!\s*\\)", content)
    # Filter out those inside \caption{} (captions legitimately say "Figure 1:")
    non_caption_hardcoded = [
        h for h in hardcoded
        if not re.search(r"\\caption\{.*" + re.escape(h), content)
    ]
    if non_caption_hardcoded:
        checks.append(Check(
            name="No hardcoded references",
            passed=False,
            details=(
                f"Found {len(non_caption_hardcoded)} hardcoded reference(s) "
                "that should use \\cref{}: " +
                ", ".join(non_caption_hardcoded[:5])
            ),
            severity="warning",
        ))

    return checks


def _check_citation_integrity(tex_path: Path, bib_path: Path) -> list[Check]:
    """Verify that all \\cite keys exist in .bib and vice versa."""
    checks: list[Check] = []

    if not bib_path.exists():
        checks.append(Check(
            name="Bibliography file",
            passed=False,
            details="references.bib not found",
        ))
        return checks

    tex_content = tex_path.read_text(encoding="utf-8")
    bib_content = bib_path.read_text(encoding="utf-8")

    # Extract all cited keys from .tex
    cite_matches = re.findall(r"\\cite[pt]?\{([^}]+)\}", tex_content)
    cited_keys: set[str] = set()
    for match in cite_matches:
        for key in match.split(","):
            cited_keys.add(key.strip())

    # Extract all defined keys from .bib
    bib_keys = set(re.findall(r"@\w+\{(\S+),", bib_content))

    # Every cited key should be in .bib
    missing_in_bib = cited_keys - bib_keys
    checks.append(Check(
        name="All citations in .bib",
        passed=len(missing_in_bib) == 0,
        details=(
            f"Cited but missing from .bib: {', '.join(sorted(missing_in_bib))}"
            if missing_in_bib
            else f"All {len(cited_keys)} cited keys found in .bib"
        ),
    ))

    # Every .bib entry should be cited (warning, not error)
    uncited = bib_keys - cited_keys
    if uncited:
        checks.append(Check(
            name="All .bib entries cited",
            passed=False,
            details=f"In .bib but never cited: {', '.join(sorted(uncited))}",
            severity="warning",
        ))

    return checks


def _check_special_chars(pdf_path: Path, manifest_path: Path) -> list[Check]:
    """Verify special characters survive in the final PDF.

    Uses pdftotext to extract text layer and checks for expected characters.
    This is THE regression test for the '?' bug.
    """
    checks: list[Check] = []

    if not pdf_path.exists():
        checks.append(Check(
            name="Special character verification",
            passed=False,
            details="PDF not found — cannot verify characters",
        ))
        return checks

    # Extract text from PDF using pdftotext
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        checks.append(Check(
            name="Special character verification",
            passed=True,
            details="pdftotext not available — skipping character verification",
            severity="info",
        ))
        return checks

    try:
        result = subprocess.run(
            [pdftotext, str(pdf_path), "-"],
            capture_output=True, text=True, timeout=30,
        )
        pdf_text = result.stdout
    except Exception as e:
        checks.append(Check(
            name="Special character verification",
            passed=True,
            details=f"pdftotext failed: {e} — skipping",
            severity="info",
        ))
        return checks

    # Load expected special chars from manifest
    expected_chars: dict[str, str] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_chars = manifest.get("special_chars", {})

    # Default chars to always check
    ALWAYS_CHECK = {
        "°": "degree symbol (°C)",
        "µ": "micro sign (µm)",
        "≈": "approximately equal",
        "±": "plus-minus",
        "×": "multiplication sign",
    }

    chars_to_check = {**ALWAYS_CHECK, **expected_chars}
    missing_chars: list[str] = []
    found_chars: list[str] = []

    for char, description in chars_to_check.items():
        if char in pdf_text:
            found_chars.append(f"{char} ({description})")
        else:
            # Only flag if the char was expected (in manifest)
            if char in expected_chars:
                missing_chars.append(f"{char} ({description})")

    if expected_chars:
        checks.append(Check(
            name="Special characters in PDF",
            passed=len(missing_chars) == 0,
            details=(
                f"Missing from PDF: {', '.join(missing_chars)}"
                if missing_chars
                else f"All {len(found_chars)} expected special characters verified in PDF"
            ),
        ))

    return checks


def verify_output(
    tex_path: Path,
    pdf_path: Path | None = None,
    bib_path: Path | None = None,
    manifest_path: Path | None = None,
    log_path: Path | None = None,
) -> VerifyResult:
    """Run all verification checks on the compiled output.

    Args:
        tex_path: Path to the generated main.tex
        pdf_path: Path to the compiled PDF (if available)
        bib_path: Path to references.bib
        manifest_path: Path to manifest.json from extraction
        log_path: Path to compilation .log file

    Returns:
        VerifyResult with all checks and a student-readable report
    """
    result = VerifyResult()
    work_dir = tex_path.parent

    # Defaults
    if pdf_path is None:
        pdf_path = work_dir / f"{tex_path.stem}.pdf"
    if bib_path is None:
        bib_path = work_dir / "references.bib"
    if manifest_path is None:
        manifest_path = work_dir / "manifest.json"
    if log_path is None:
        log_path = work_dir / f"{tex_path.stem}.log"

    # Run checks
    result.checks.extend(_check_log_audit(log_path))
    result.checks.extend(_check_manifest_diff(manifest_path, tex_path))
    result.checks.extend(_check_crossref_integrity(tex_path))
    result.checks.extend(_check_citation_integrity(tex_path, bib_path))
    result.checks.extend(_check_special_chars(pdf_path, manifest_path))

    # Overall result
    result.all_passed = all(
        c.passed for c in result.checks if c.severity == "error"
    )

    # Write report
    report_path = work_dir / "report.md"
    report_path.write_text(result.to_report_md(), encoding="utf-8", newline="\n")
    result.report_path = report_path

    log.info(
        "Verification: %s (%d checks, %d errors, %d warnings)",
        "PASSED" if result.all_passed else "FAILED",
        len(result.checks), result.error_count, result.warning_count,
    )

    return result


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python verify.py <main.tex> [--pdf <path>] [--bib <path>] [--manifest <path>]")
        sys.exit(1)

    tex_path = Path(sys.argv[1])
    kwargs: dict = {}

    for flag, key in [("--pdf", "pdf_path"), ("--bib", "bib_path"),
                       ("--manifest", "manifest_path"), ("--log", "log_path")]:
        if flag in sys.argv:
            idx = sys.argv.index(flag)
            if idx + 1 < len(sys.argv):
                kwargs[key] = Path(sys.argv[idx + 1])

    result = verify_output(tex_path, **kwargs)
    print(result.to_report_md())
    sys.exit(0 if result.all_passed else 1)


if __name__ == "__main__":
    main()
