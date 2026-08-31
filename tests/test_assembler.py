"""
Unit and regression tests for assemble.py (Deterministic AST Assembler).
"""

import json
from pathlib import Path
import pytest

from scripts.assemble import (
    sanitize_prose,
    split_into_blocks,
    build_figure_blocks,
    parse_and_assemble,
    AssemblyContext,
)


def test_sanitize_prose_currency_and_chemicals():
    raw = "The overnight capital cost was $3,000/kWe with 15% reduction for CO2 and SOx at 50 °C."
    sanitized = sanitize_prose(raw, {}, {})
    assert r"\$3,000/kWe" in sanitized
    assert r"15\%" in sanitized
    assert r"CO$_2$" in sanitized
    assert r"SO$_x$" in sanitized
    assert r"50\textdegree{}C" in sanitized


def test_sanitize_prose_citations():
    cite_map = {"1": "statista2022", "2": "iea2023", "3": "goodkind2019"}
    raw = "Several studies have analyzed emissions [1, 2] and health impacts [1-3]."
    sanitized = sanitize_prose(raw, cite_map, {})
    assert r"\cite{statista2022, iea2023}" in sanitized
    assert r"\cite{statista2022, iea2023, goodkind2019}" in sanitized


def test_subfigure_group_generation():
    fig_reg = {
        "figures": [
            {
                "fig_id": "fig1",
                "caption": "Fig. 1: (a) Case 1; (b) Case 2; (c) Case 3",
                "label": "fig:cases",
                "output_path": "figures/fig1.png",
                "is_subfigure": True,
                "subfigure_group": "subfig_group_1",
                "figure_number": 1,
            },
            {
                "fig_id": "fig2",
                "caption": "Fig. 1: (a) Case 1; (b) Case 2; (c) Case 3",
                "label": "fig:cases",
                "output_path": "figures/fig2.png",
                "is_subfigure": True,
                "subfigure_group": "subfig_group_1",
                "figure_number": 1,
            },
            {
                "fig_id": "fig3",
                "caption": "Fig. 1: (a) Case 1; (b) Case 2; (c) Case 3",
                "label": "fig:cases",
                "output_path": "figures/fig3.png",
                "is_subfigure": True,
                "subfigure_group": "subfig_group_1",
                "figure_number": 1,
            },
            {
                "fig_id": "fig4",
                "caption": "Fig. 3: Comparison of LCOE",
                "label": "fig:lcoe",
                "output_path": "figures/fig4.png",
                "is_subfigure": False,
                "subfigure_group": None,
                "aspect_ratio": 1.58,
                "figure_number": 3,
            },
        ]
    }

    blocks, img_to_key = build_figure_blocks(fig_reg)
    assert "subfig_group_1" in blocks
    assert "fig4" in blocks
    assert r"\begin{figure}" in blocks["subfig_group_1"] or r"\begin{figure*}" in blocks["subfig_group_1"]
    assert r"\hfill" in blocks["subfig_group_1"]

    # Standalone figure 4 (Fig 3 in document)
    assert "fig4.png" in blocks["fig4"]
    assert r"\begin{figure}" in blocks["fig4"]


def test_assembler_seamless_flow_and_verbatim(tmp_path: Path):
    content_md = (
        "**Techno-economic Assessment of Energy Systems**\n\n"
        "**Abstract**\n\n"
        "This paper evaluates the techno-economic performance of energy systems.\n\n"
        "**1.0 Introduction**\n\n"
        "Global decarbonization requires accelerating the transition to clean power.\n\n"
        "**2.0 Results**\n\n"
        "Results show significant capital cost savings.\n"
    )

    ctx = AssemblyContext(
        work_dir=tmp_path,
        content_md=content_md,
        manifest={"counts": {"sections": 2, "figures": 0, "tables": 0}},
        fig_reg={"figures": []},
        table_reg={"tables": []},
        bib_reg={"entries": []},
    )

    tex = parse_and_assemble(ctx)
    assert r"\documentclass[journal]{IEEEtran}" in tex
    assert r"\section{Introduction}" in tex or r"\section{1.0 Introduction}" in tex
    assert r"\section{Results}" in tex or r"\section{2.0 Results}" in tex
    assert "Global decarbonization requires accelerating the transition to clean power." in tex
