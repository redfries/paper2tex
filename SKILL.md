---
name: paper2tex
description: Converts academic Word (.docx) papers into conference- and journal-formatted LaTeX (.tex) with seamless float flow, deterministic math/tables, verified citations, and OpenXML rotation/transform normalization. Trigger whenever the user asks to "use paper2tex", "run paper2tex", "convert my paper to LaTeX", "format docx for IEEE/ACM/Springer", or prepare submission-ready PDFs.
---

# paper2tex — Academic Paper Word-to-LaTeX Converter

Converts academic `.docx` papers into publication-ready, compiling LaTeX documents tailored to any conference or journal theme (IEEE, ACM, Springer LNCS, Elsevier, NeurIPS, ICML, CVPR, MDPI, Nature).

## Mandatory Step 0: Figure Source Clarification

Before executing the extraction pipeline, the agent **MUST ALWAYS** ask the user:

> *"Do you have a dedicated `figures/` folder with high-resolution or vector images (e.g., `./figures`), or should I extract the embedded images directly from the Word document? (Reply with your folder path or simply 'extract')"*

- **If the user replies `'extract'`**: Run `python -m scripts.extract input.docx work_dir/`. The pipeline will automatically extract, normalize, and auto-rotate all embedded drawings from `.docx`.
- **If the user provides a folder path** (e.g., `./figures` or `C:/assets/figs`): Run `python -m scripts.extract input.docx work_dir/ --figures-dir <path>`. The pipeline will match your high-res vector (`.pdf`, `.svg`) and raster (`.png`, `.jpg` >= 300 DPI) files to document figures.

---

## Quick Start

Run the end-to-end extraction and assembly pipeline:

```bash
# 1. Verify system toolchain
python -m scripts.preflight

# 2. Extract content, math (OMML), tables, figures, and bibliography
python -m scripts.extract input.docx work_dir/ [--figures-dir <path>]

# 3. Apply target conference theme (or analyze custom template zip)
python -m scripts.template_spec "ieee-conference" work_dir/

# 4. Assemble main.tex with template-aware subfigures & seamless float flow
python -m scripts.assemble work_dir/

# 5. Compile and run visual QA verification
python -m scripts.compile work_dir/main.tex
python -m scripts.visual_qa work_dir/main.pdf work_dir/
```

## Workflow Stages

```
STAGE 0: FIGURE INQUIRY  → Ask user for figures/ folder or "extract" confirmation
STAGE 1: PREFLIGHT       → Check pandoc, tectonic/latexmk, lxml, Pillow, pymupdf
STAGE 2: PREPROCESS      → Strip tracked changes, fix Symbol font trap, map field codes
STAGE 3: EXTRACT         → Parallel extractors for OMML math, tables, figures, bib
STAGE 4: THEME SPEC      → Match recipe (IEEE/ACM/LNCS) or research via Firecrawl
STAGE 5: AST ASSEMBLE    → Deterministic assembly with template-aware subfigures & subfloats
STAGE 6: COMPILE LOOP    → Engine selection (XeLaTeX/pdfLaTeX) + automated log auto-fix
STAGE 7: VERIFICATION    → Manifest diff + special character audit + Visual QA
STAGE 8: DELIVER         → submission/ folder (.tex, .bib, figures/, .pdf, report.md)
```

## Core Architectural Guarantees

1. **100% Verbatim Prose Preservation**: Maps Markdown AST directly to LaTeX. Zero dropped paragraphs, zero paraphrasing, zero text alteration.
2. **OpenXML Rotation & Flip Normalization**: Accurately parses `<a:xfrm rot="...">` to prevent sideways/rotated images.
3. **Template-Aware Subfigures**: Uses `\usepackage[caption=false,font=footnotesize]{subfig}` with `\subfloat` for `IEEEtran` and `subcaption` for `acmart`/`llncs`.
4. **Subcaption Decomposition**: Splits composite captions with `(a)`, `(b)`, `(c)` into individual panel captions.
5. **Seamless Float Flow**: Eliminates disruptive `\FloatBarrier` injections before sections. Floats place naturally (`[!t]`, `[b]`) with zero blank page voids.
6. **Deterministic OMML Math**: Word equations convert directly to LaTeX via MathML XSLT — never through LLM text re-emission.

## Documentation & References

- **Layout & Float Rules**: See [LAYOUT_GUIDELINES.md](LAYOUT_GUIDELINES.md) for figure sizing, subfigure geometry, and table formatting.
- **Themes & Firecrawl Research**: See [THEMES_AND_TEMPLATES.md](THEMES_AND_TEMPLATES.md) for venue recipes and online template research.
- **Technical Reference**: See [REFERENCE.md](REFERENCE.md) for extraction internals, symbol font mapping, and compiler auto-fix taxonomy.
- **Agent Instructions**: See [AGENTS.md](AGENTS.md) for step-by-step agent instructions.
- **Setup Guide**: See [SETUP.md](SETUP.md) for platform-specific setup (Antigravity, Claude Code, Cursor, OpenCode).
