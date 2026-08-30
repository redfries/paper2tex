"""
paper2tex: template_spec — Analyze a conference template to extract compilation settings.

Reads a template zip (or directory) containing .cls, .bst, and sample .tex files.
Produces a template-spec.json with engine, preamble, author commands, bib style, etc.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

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

log = logging.getLogger(__name__)


@dataclass
class TemplateSpec:
    """Specification extracted from a conference template."""
    name: str = ""                        # e.g., "IEEE Conference"
    document_class: str = ""              # e.g., "IEEEtran"
    class_options: list[str] = field(default_factory=list)  # e.g., ["conference", "compsoc"]
    engine: str = "xelatex"              # xelatex, pdflatex, lualatex
    required_packages: list[str] = field(default_factory=list)
    forbidden_packages: list[str] = field(default_factory=list)
    bib_style: str = ""                  # e.g., "IEEEtran"
    bib_engine: str = "bibtex"           # bibtex, biber
    column_mode: str = "twocolumn"       # onecolumn, twocolumn
    author_format: str = ""              # Template for \author block
    title_format: str = ""               # Template for \title block
    abstract_env: str = "abstract"       # Environment name for abstract
    keywords_cmd: str = ""               # Command for keywords
    preamble_additions: list[str] = field(default_factory=list)  # Extra preamble lines
    cls_files: list[str] = field(default_factory=list)
    bst_files: list[str] = field(default_factory=list)
    sample_tex: str = ""                 # Content of sample .tex if found
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "document_class": self.document_class,
            "class_options": self.class_options,
            "engine": self.engine,
            "required_packages": self.required_packages,
            "bib_style": self.bib_style,
            "bib_engine": self.bib_engine,
            "column_mode": self.column_mode,
            "author_format": self.author_format,
            "keywords_cmd": self.keywords_cmd,
            "cls_files": self.cls_files,
            "bst_files": self.bst_files,
            "warnings": self.warnings,
        }


# --- Tier-1 Recipes (known templates) ---

TIER1_RECIPES: dict[str, dict] = {
    "ieee-conference": {
        "name": "IEEE Conference",
        "document_class": "IEEEtran",
        "class_options": ["conference"],
        "engine": "xelatex",
        "bib_style": "IEEEtran",
        "bib_engine": "bibtex",
        "column_mode": "twocolumn",
        "author_format": "\\author{\\IEEEauthorblockN{NAME}\\IEEEauthorblockA{AFFILIATION}}",
        "keywords_cmd": "\\begin{IEEEkeywords}...\\end{IEEEkeywords}",
    },
    "ieee-transaction": {
        "name": "IEEE Transaction/Journal",
        "document_class": "IEEEtran",
        "class_options": ["journal"],
        "engine": "xelatex",
        "bib_style": "IEEEtran",
        "bib_engine": "bibtex",
        "column_mode": "twocolumn",
        "author_format": "\\author{NAME~\\IEEEmembership{Member,~IEEE}}",
        "keywords_cmd": "\\begin{IEEEkeywords}...\\end{IEEEkeywords}",
    },
    "acm-sigconf": {
        "name": "ACM SIGCONF (Conference)",
        "document_class": "acmart",
        "class_options": ["sigconf"],
        "engine": "xelatex",
        "bib_style": "ACM-Reference-Format",
        "bib_engine": "bibtex",
        "column_mode": "twocolumn",
        "author_format": "\\author{NAME}\\affiliation{\\institution{INST}\\city{CITY}\\country{COUNTRY}}\\email{EMAIL}",
        "keywords_cmd": "\\keywords{...}",
    },
    "lncs": {
        "name": "Springer LNCS",
        "document_class": "llncs",
        "class_options": [],
        "engine": "xelatex",
        "bib_style": "splncs04",
        "bib_engine": "bibtex",
        "column_mode": "onecolumn",
        "author_format": "\\author{NAME1 \\and NAME2}\\institute{INST1 \\and INST2}",
        "keywords_cmd": "\\keywords{...}",
    },
    "neurips": {
        "name": "NeurIPS",
        "document_class": "neurips",
        "class_options": [],
        "engine": "xelatex",
        "bib_style": "plain",
        "bib_engine": "bibtex",
        "column_mode": "onecolumn",
        "author_format": "\\author{NAME \\\\ INST \\\\ EMAIL}",
        "keywords_cmd": "",
    },
    "icml": {
        "name": "ICML",
        "document_class": "icml",
        "class_options": [],
        "engine": "pdflatex",
        "bib_style": "icml",
        "bib_engine": "bibtex",
        "column_mode": "twocolumn",
        "author_format": "\\icmlauthor{NAME}{INST}",
        "keywords_cmd": "\\begin{keywords}...\\end{keywords}",
    },
    "cvpr": {
        "name": "CVPR",
        "document_class": "cvpr",
        "class_options": [],
        "engine": "pdflatex",
        "bib_style": "ieee_fullname",
        "bib_engine": "bibtex",
        "column_mode": "twocolumn",
        "author_format": "\\author{NAME\\\\INST}",
        "keywords_cmd": "",
    },
}


def _match_tier1(name: str) -> TemplateSpec | None:
    """Try to match a conference name to a tier-1 recipe."""
    name_lower = name.lower().strip()

    for key, recipe in TIER1_RECIPES.items():
        recipe_name_lower = recipe["name"].lower()
        # Check various patterns
        if (key in name_lower or
            recipe_name_lower in name_lower or
            recipe.get("document_class", "") in name_lower):
            spec = TemplateSpec(**{k: v for k, v in recipe.items()
                                   if k in TemplateSpec.__dataclass_fields__})
            log.info("Matched tier-1 recipe: %s", spec.name)
            return spec

    return None


def _parse_sample_tex(tex_content: str) -> TemplateSpec:
    """Parse a sample .tex file to extract template settings."""
    spec = TemplateSpec()

    # Document class
    cls_match = re.search(r"\\documentclass\[?([^\]]*)\]?\{(\w+)\}", tex_content)
    if cls_match:
        options = [o.strip() for o in cls_match.group(1).split(",") if o.strip()]
        spec.class_options = options
        spec.document_class = cls_match.group(2)

    # Packages
    for pkg_match in re.finditer(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", tex_content):
        for pkg in pkg_match.group(1).split(","):
            pkg = pkg.strip()
            if pkg:
                spec.required_packages.append(pkg)

    # Bibliography style
    bst_match = re.search(r"\\bibliographystyle\{(\w+)\}", tex_content)
    if bst_match:
        spec.bib_style = bst_match.group(1)

    # Detect biber vs bibtex
    if "\\addbibresource" in tex_content or "biblatex" in tex_content:
        spec.bib_engine = "biber"
    else:
        spec.bib_engine = "bibtex"

    # Column mode
    if "twocolumn" in tex_content or "\\twocolumn" in tex_content:
        spec.column_mode = "twocolumn"
    elif "onecolumn" in tex_content:
        spec.column_mode = "onecolumn"

    # Author format — extract the \author{...} block pattern
    author_match = re.search(r"\\author\{(.+?)\}", tex_content, re.DOTALL)
    if author_match:
        spec.author_format = f"\\author{{{author_match.group(1)}}}"

    # Keywords
    kw_match = re.search(r"\\(?:keywords|begin\{(?:IEEE)?keywords\})", tex_content)
    if kw_match:
        spec.keywords_cmd = kw_match.group()

    # Engine hint: if fontspec or unicode-math → xelatex/lualatex needed
    if "fontspec" in tex_content or "unicode-math" in tex_content:
        spec.engine = "xelatex"
    elif any(pkg in tex_content for pkg in ["inputenc", "fontenc"]):
        spec.engine = "pdflatex"
    else:
        spec.engine = "xelatex"  # Default to xelatex for Unicode safety

    return spec


def analyze_template(
    template_source: str | Path,
    work_dir: Path,
) -> TemplateSpec:
    """Analyze a conference template and extract compilation settings.

    Args:
        template_source: One of:
          - A conference name (e.g., "IEEE conference") → tries tier-1 recipes
          - A path to a .zip file → unpacks and analyzes
          - A path to a directory → analyzes contents
          - A path to a .tex file → analyzes directly

    Returns:
        TemplateSpec with all compilation settings
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    source = str(template_source)

    # Try tier-1 recipe first
    spec = _match_tier1(source)
    if spec is not None:
        # Write spec
        spec_path = work_dir / "template-spec.json"
        spec_path.write_text(
            json.dumps(spec.to_dict(), indent=2),
            encoding="utf-8", newline="\n",
        )
        return spec

    source_path = Path(source)
    template_dir = work_dir / "template"
    template_dir.mkdir(exist_ok=True)

    # Handle zip file
    if source_path.exists() and source_path.suffix == ".zip":
        with zipfile.ZipFile(source_path, "r") as zf:
            zf.extractall(template_dir)
        log.info("Unpacked template zip: %s", source_path.name)
    elif source_path.exists() and source_path.is_dir():
        template_dir = source_path
    elif source_path.exists() and source_path.suffix == ".tex":
        spec = _parse_sample_tex(source_path.read_text(encoding="utf-8", errors="replace"))
        spec.sample_tex = str(source_path)
        spec_path = work_dir / "template-spec.json"
        spec_path.write_text(json.dumps(spec.to_dict(), indent=2), encoding="utf-8", newline="\n")
        return spec
    else:
        # Not a file — might be a conference name that didn't match tier-1
        spec = TemplateSpec(name=source)
        spec.warnings.append(
            f"Could not match '{source}' to a known template. "
            "Please provide the template zip or a sample .tex file."
        )
        return spec

    # Find .cls, .bst, .tex files in the template directory
    cls_files = list(template_dir.rglob("*.cls"))
    bst_files = list(template_dir.rglob("*.bst"))
    tex_files = list(template_dir.rglob("*.tex"))

    spec = TemplateSpec()
    spec.cls_files = [f.name for f in cls_files]
    spec.bst_files = [f.name for f in bst_files]

    # Use the document class from .cls filename
    if cls_files:
        spec.document_class = cls_files[0].stem

    if bst_files:
        spec.bib_style = bst_files[0].stem

    # Parse sample .tex for settings
    sample_tex_files = [f for f in tex_files if "sample" in f.name.lower() or "example" in f.name.lower() or "template" in f.name.lower() or "main" in f.name.lower()]
    if not sample_tex_files:
        sample_tex_files = tex_files

    if sample_tex_files:
        best_sample = sample_tex_files[0]
        tex_content = best_sample.read_text(encoding="utf-8", errors="replace")
        parsed = _parse_sample_tex(tex_content)

        # Merge parsed settings with file-based settings
        spec.class_options = parsed.class_options or spec.class_options
        spec.document_class = spec.document_class or parsed.document_class
        spec.engine = parsed.engine
        spec.required_packages = parsed.required_packages
        spec.bib_style = spec.bib_style or parsed.bib_style
        spec.bib_engine = parsed.bib_engine
        spec.column_mode = parsed.column_mode
        spec.author_format = parsed.author_format
        spec.keywords_cmd = parsed.keywords_cmd
        spec.sample_tex = str(best_sample)

    # Write spec
    spec_path = work_dir / "template-spec.json"
    spec_path.write_text(
        json.dumps(spec.to_dict(), indent=2),
        encoding="utf-8", newline="\n",
    )
    log.info("Template spec written: %s (class: %s, engine: %s)",
             spec_path, spec.document_class, spec.engine)

    return spec


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python template_spec.py <template_source> <work_dir>")
        print("  template_source: conference name, .zip path, .tex path, or directory")
        sys.exit(1)

    source = sys.argv[1]
    work_dir = Path(sys.argv[2])

    spec = analyze_template(source, work_dir)
    print(json.dumps(spec.to_dict(), indent=2))


if __name__ == "__main__":
    main()
