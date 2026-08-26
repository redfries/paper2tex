"""
paper2tex: overleaf_export — Package submission files into an Overleaf-ready zip.

Creates a single .zip file containing everything needed to upload to Overleaf
as a new project: main.tex, references.bib, figures/, and any .cls/.bst files.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)


def create_overleaf_zip(
    submission_dir: Path,
    output_path: Path | None = None,
    template_dir: Path | None = None,
) -> Path:
    """Package all submission files into an Overleaf-ready zip.

    Args:
        submission_dir: Directory containing main.tex, references.bib, figures/, etc.
        output_path: Where to write the zip (default: submission_dir / overleaf.zip)
        template_dir: Optional directory with .cls/.bst files to include

    Returns:
        Path to the created zip file
    """
    if output_path is None:
        output_path = submission_dir / "overleaf.zip"

    # Collect all files to include
    files_to_zip: list[tuple[Path, str]] = []  # (absolute_path, archive_name)

    # main.tex
    main_tex = submission_dir / "main.tex"
    if main_tex.exists():
        files_to_zip.append((main_tex, "main.tex"))
    else:
        # Try to find any .tex file
        tex_files = list(submission_dir.glob("*.tex"))
        if tex_files:
            files_to_zip.append((tex_files[0], tex_files[0].name))

    # references.bib
    bib_file = submission_dir / "references.bib"
    if bib_file.exists():
        files_to_zip.append((bib_file, "references.bib"))

    # figures/
    figures_dir = submission_dir / "figures"
    if figures_dir.exists():
        for fig in figures_dir.iterdir():
            if fig.is_file():
                files_to_zip.append((fig, f"figures/{fig.name}"))

    # Template files (.cls, .bst, .sty)
    if template_dir and template_dir.exists():
        for ext in ("*.cls", "*.bst", "*.sty"):
            for f in template_dir.rglob(ext):
                files_to_zip.append((f, f.name))

    # Also check submission_dir for .cls, .bst, .sty
    for ext in ("*.cls", "*.bst", "*.sty"):
        for f in submission_dir.glob(ext):
            archive_name = f.name
            if not any(an == archive_name for _, an in files_to_zip):
                files_to_zip.append((f, archive_name))

    # Report
    if not files_to_zip:
        log.warning("No files found to package in %s", submission_dir)
        return output_path

    # Create zip
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for abs_path, archive_name in files_to_zip:
            zf.write(abs_path, archive_name)
            log.debug("Added: %s → %s", abs_path.name, archive_name)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    log.info(
        "Created Overleaf zip: %s (%.1f MB, %d files)",
        output_path, size_mb, len(files_to_zip),
    )

    return output_path


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python overleaf_export.py <submission_dir> [--template-dir <path>] [--output <path>]")
        sys.exit(1)

    submission_dir = Path(sys.argv[1])
    kwargs: dict = {}

    if "--template-dir" in sys.argv:
        idx = sys.argv.index("--template-dir")
        if idx + 1 < len(sys.argv):
            kwargs["template_dir"] = Path(sys.argv[idx + 1])

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            kwargs["output_path"] = Path(sys.argv[idx + 1])

    zip_path = create_overleaf_zip(submission_dir, **kwargs)
    print(f"✅ Overleaf zip created: {zip_path}")
    print(f"   Upload to: https://www.overleaf.com/project → New Project → Upload Project")


if __name__ == "__main__":
    main()
