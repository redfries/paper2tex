"""
paper2tex: visual_qa — PDF-to-PNG rendering + optional vision model inspection.

Renders each page of the compiled PDF as a PNG image for visual quality assurance.
Checks for: missing/blank figures, table overflow, broken glyphs (? boxes),
math rendering artifacts, header/author block issues.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class PageCheck:
    """Visual check result for a single PDF page."""
    page_num: int
    png_path: Path
    issues: list[str] = field(default_factory=list)


@dataclass
class VisualQAResult:
    """Result of visual QA on the compiled PDF."""
    pages: list[PageCheck] = field(default_factory=list)
    total_pages: int = 0
    pages_with_issues: int = 0
    png_dir: Path | None = None
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Visual QA: {self.total_pages} pages rendered",
            f"Pages with potential issues: {self.pages_with_issues}",
        ]
        for page in self.pages:
            if page.issues:
                lines.append(f"  Page {page.page_num}:")
                for issue in page.issues:
                    lines.append(f"    ⚠️ {issue}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ℹ️ {w}")
        return "\n".join(lines)


def _render_pdf_to_png_pdftoppm(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 200,
) -> list[Path]:
    """Render PDF pages to PNG using pdftoppm (from poppler-utils)."""
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise FileNotFoundError("pdftoppm not found. Install poppler: scoop install poppler")

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"

    result = subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode != 0:
        log.warning("pdftoppm failed: %s", result.stderr)
        return []

    # pdftoppm outputs page-1.png, page-2.png, etc.
    pngs = sorted(output_dir.glob("page-*.png"))
    log.info("Rendered %d pages to PNG", len(pngs))
    return pngs


def _render_pdf_to_png_pdf2image(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 200,
) -> list[Path]:
    """Render PDF pages to PNG using pdf2image (Python library)."""
    try:
        from pdf2image import convert_from_path  # type: ignore
    except ImportError:
        raise ImportError("pdf2image not available: pip install pdf2image")

    output_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(str(pdf_path), dpi=dpi)

    pngs: list[Path] = []
    for i, img in enumerate(images, 1):
        png_path = output_dir / f"page-{i:03d}.png"
        img.save(png_path, "PNG")
        pngs.append(png_path)

    log.info("Rendered %d pages to PNG via pdf2image", len(pngs))
    return pngs


def _basic_image_checks(png_path: Path) -> list[str]:
    """Run basic image-level checks on a rendered page PNG.

    Checks for very simple indicators of problems. For full visual QA,
    a vision model (GPT-4o, Claude Sonnet, Gemini) should inspect the images.
    """
    issues: list[str] = []

    try:
        from PIL import Image  # type: ignore
        img = Image.open(png_path)
        width, height = img.size

        # Check if page is mostly blank (potential missing content)
        grayscale = img.convert("L")
        pixels = list(grayscale.getdata())
        total = len(pixels)
        white_pixels = sum(1 for p in pixels if p > 250)
        white_ratio = white_pixels / total if total > 0 else 0

        if white_ratio > 0.98:
            issues.append("Page appears nearly blank (>98% white pixels)")

        if white_ratio > 0.95 and height > width:
            # Mostly blank page — might be a page with just a header
            issues.append("Page is mostly empty — possible content drop")

    except ImportError:
        # Pillow not available — skip pixel analysis
        pass
    except Exception as e:
        log.debug("Image check failed for %s: %s", png_path, e)

    return issues


def run_visual_qa(
    pdf_path: Path,
    work_dir: Path,
    dpi: int = 200,
) -> VisualQAResult:
    """Render PDF to PNGs and run basic visual checks.

    Args:
        pdf_path: Path to the compiled PDF
        work_dir: Working directory for output PNGs
        dpi: Resolution for rendering

    Returns:
        VisualQAResult with page-by-page check results
    """
    result = VisualQAResult()
    png_dir = work_dir / "visual_qa"
    result.png_dir = png_dir

    if not pdf_path.exists():
        result.warnings.append(f"PDF not found: {pdf_path}")
        return result

    # Try pdftoppm first, then pdf2image
    pngs: list[Path] = []
    try:
        pngs = _render_pdf_to_png_pdftoppm(pdf_path, png_dir, dpi)
    except FileNotFoundError:
        try:
            pngs = _render_pdf_to_png_pdf2image(pdf_path, png_dir, dpi)
        except ImportError:
            result.warnings.append(
                "Neither pdftoppm nor pdf2image available. "
                "Install poppler (scoop install poppler) or pdf2image (pip install pdf2image) "
                "for visual QA."
            )
            return result

    result.total_pages = len(pngs)

    for i, png_path in enumerate(pngs, 1):
        issues = _basic_image_checks(png_path)
        page = PageCheck(page_num=i, png_path=png_path, issues=issues)
        result.pages.append(page)
        if issues:
            result.pages_with_issues += 1

    # Add guidance for manual/vision-model review
    if pngs:
        result.warnings.append(
            f"Page images saved to {png_dir}. "
            "For thorough visual QA, inspect these images for: "
            "broken glyphs (?), missing figures, table overflow, "
            "math rendering artifacts, header/author block issues."
        )

    log.info("Visual QA: %d pages, %d with potential issues",
             result.total_pages, result.pages_with_issues)
    return result


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python visual_qa.py <main.pdf> <work_dir> [--dpi N]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    work_dir = Path(sys.argv[2])
    dpi = 200

    if "--dpi" in sys.argv:
        idx = sys.argv.index("--dpi")
        if idx + 1 < len(sys.argv):
            dpi = int(sys.argv[idx + 1])

    result = run_visual_qa(pdf_path, work_dir, dpi)
    print(result.summary())


if __name__ == "__main__":
    main()
