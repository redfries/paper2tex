"""
Unit and regression tests for verify_text_fidelity.
"""

import json
from pathlib import Path
import pytest

from scripts.verify_text_fidelity import (
    verify_text_fidelity,
    normalize_text_for_comparison,
    extract_paragraphs_from_md,
    extract_paragraphs_from_tex,
)


def test_normalization():
    raw = r"Overnight capital cost was \$3,000/kWe with 15\% reduction for CO$_2$ and 50\textdegree{}C."
    norm = normalize_text_for_comparison(raw)
    assert "3000" in norm
    assert "co2" in norm
    assert "50" in norm


def test_fidelity_exact_match(tmp_path: Path):
    md_file = tmp_path / "content.md"
    tex_file = tmp_path / "main.tex"
    fig_reg_file = tmp_path / "figures_registry.json"

    md_content = (
        "# Sample Paper\n\n"
        "Global efforts to mitigate climate change are accelerating the transition away from coal-fired power.\n\n"
        "This paper evaluates the techno-economic feasibility of converting coal power plants into nuclear facilities.\n"
    )
    tex_content = (
        "\\documentclass{IEEEtran}\n"
        "\\begin{document}\n"
        "\\section{Introduction}\n"
        "Global efforts to mitigate climate change are accelerating the transition away from coal-fired power.\n\n"
        "This paper evaluates the techno-economic feasibility of converting coal power plants into nuclear facilities.\n"
        "\\end{document}\n"
    )
    fig_reg = {"figures": []}

    md_file.write_text(md_content, encoding="utf-8")
    tex_file.write_text(tex_content, encoding="utf-8")
    fig_reg_file.write_text(json.dumps(fig_reg), encoding="utf-8")

    result = verify_text_fidelity(md_file, tex_file, fig_reg_file)
    assert result.passed
    assert result.fidelity_score == 100.0
    assert len(result.dropped_paras) == 0
    assert len(result.hallucinated_paras) == 0
    assert len(result.rewritten_paras) == 0


def test_fidelity_dropped_paragraph(tmp_path: Path):
    md_file = tmp_path / "content.md"
    tex_file = tmp_path / "main.tex"

    md_content = (
        "# Sample Paper\n\n"
        "First paragraph about global energy transitions and decarbonization policies.\n\n"
        "Second paragraph with critical cost model calculations that should not be dropped.\n"
    )
    tex_content = (
        "\\documentclass{IEEEtran}\n"
        "\\begin{document}\n"
        "First paragraph about global energy transitions and decarbonization policies.\n"
        "\\end{document}\n"
    )

    md_file.write_text(md_content, encoding="utf-8")
    tex_file.write_text(tex_content, encoding="utf-8")

    result = verify_text_fidelity(md_file, tex_file)
    assert not result.passed
    assert len(result.dropped_paras) == 1
    assert "Second paragraph" in result.dropped_paras[0].source_preview


def test_fidelity_hallucinated_paragraph(tmp_path: Path):
    md_file = tmp_path / "content.md"
    tex_file = tmp_path / "main.tex"

    md_content = (
        "# Sample Paper\n\n"
        "First paragraph about global energy transitions and decarbonization policies.\n"
    )
    tex_content = (
        "\\documentclass{IEEEtran}\n"
        "\\begin{document}\n"
        "First paragraph about global energy transitions and decarbonization policies.\n\n"
        "Furthermore, we also propose an unprecedented artificial neural network architecture to optimize power grids.\n"
        "\\end{document}\n"
    )

    md_file.write_text(md_content, encoding="utf-8")
    tex_file.write_text(tex_content, encoding="utf-8")

    result = verify_text_fidelity(md_file, tex_file)
    assert not result.passed
    assert len(result.hallucinated_paras) == 1
    assert "artificial neural network" in result.hallucinated_paras[0].target_preview


def test_fidelity_caption_mismatch(tmp_path: Path):
    md_file = tmp_path / "content.md"
    tex_file = tmp_path / "main.tex"
    fig_reg_file = tmp_path / "figures_registry.json"

    md_content = "Global efforts to mitigate climate change are accelerating the transition away from coal-fired power.\n"
    tex_content = (
        "\\documentclass{IEEEtran}\n"
        "\\begin{document}\n"
        "Global efforts to mitigate climate change are accelerating the transition away from coal-fired power.\n"
        "\\begin{figure}\n"
        "\\caption{Shortened caption}\n"
        "\\end{figure}\n"
        "\\end{document}\n"
    )
    fig_reg = {
        "figures": [
            {
                "fig_id": "fig1",
                "caption": "Comparison of Levelized Cost of Electricity across power generation cases including greenfield and repowered options.",
            }
        ]
    }

    md_file.write_text(md_content, encoding="utf-8")
    tex_file.write_text(tex_content, encoding="utf-8")
    fig_reg_file.write_text(json.dumps(fig_reg), encoding="utf-8")

    result = verify_text_fidelity(md_file, tex_file, fig_reg_file)
    assert not result.passed
    failed_caps = [c for c in result.caption_checks if not c.passed]
    assert len(failed_caps) == 1
