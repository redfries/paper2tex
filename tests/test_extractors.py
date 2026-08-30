"""
Unit tests for paper2tex extraction and verification components.
"""

from pathlib import Path
import pytest

from scripts.utils.char_map import (
    detect_special_chars,
    get_required_packages,
    MATH_CHAR_MAP,
    TEXT_CHAR_MAP,
    GREEK_TEXT_MAP,
)
from scripts.template_spec import analyze_template, TIER1_RECIPES
from scripts.compile import _classify_errors, ErrorCategory
from scripts.extract_bib import _parse_reference_text, BibRegistry, BibEntry


def test_special_char_detection():
    sample_text = (
        "Operating temperature was 25°C to 500°C. "
        "Particle size was 10 µm with thermal coefficient α ≈ 2.5 × 10⁻³ W/(m·K). "
        "Margin of error is ±3%."
    )
    chars = detect_special_chars(sample_text)
    assert "°" in chars and chars["°"] == 2
    assert "µ" in chars and chars["µ"] == 1
    assert "α" in chars and chars["α"] == 1
    assert "≈" in chars and chars["≈"] == 1
    assert "±" in chars and chars["±"] == 1
    assert "×" in chars and chars["×"] == 1

    packages = get_required_packages(chars)
    assert "textcomp" in packages


def test_tier1_template_matching(tmp_path):
    spec_ieee = analyze_template("IEEE conference", tmp_path)
    assert spec_ieee.document_class == "IEEEtran"
    assert "conference" in spec_ieee.class_options
    assert spec_ieee.engine == "xelatex"

    spec_acm = analyze_template("ACM SIGCONF", tmp_path)
    assert spec_acm.document_class == "acmart"
    assert "sigconf" in spec_acm.class_options

    spec_lncs = analyze_template("Springer LNCS", tmp_path)
    assert spec_lncs.document_class == "llncs"


def test_bib_reference_parsing():
    ref_text = '[1] A. Smith and B. Jones, "Deep Learning for Document Processing," in Proc. ICML, 2024.'
    entry = _parse_reference_text(ref_text, 0)
    assert entry.year == "2024"
    assert "Deep Learning" in entry.title
    assert entry.key != ""


def test_error_classification():
    log_sample = """
! Undefined control sequence.
l.42 \\align

! LaTeX Error: File `somepkg.sty' not found.

LaTeX Warning: Citation `smith2024' on page 1 undefined on input line 50.
LaTeX Warning: Reference `fig:arch' on page 2 undefined on input line 60.
Overfull \\hbox (12.5pt too wide) in paragraph at lines 70--75
"""
    errors = _classify_errors(log_sample)
    categories = [e.category for e in errors]

    assert ErrorCategory.UNDEFINED_COMMAND in categories
    assert ErrorCategory.MISSING_PACKAGE in categories
    assert ErrorCategory.CITATION_UNDEFINED in categories
    assert ErrorCategory.REFERENCE_UNDEFINED in categories
    assert ErrorCategory.OVERFULL_HBOX in categories
