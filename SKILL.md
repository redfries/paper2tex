---
name: paper2tex
description: Converts academic Word (.docx) papers into conference- and journal-formatted LaTeX (.tex) with seamless float flow, deterministic math/tables, and verified citations. Use when the user asks to convert Word documents to LaTeX, format papers for IEEE/ACM/Springer/Elsevier/NeurIPS conferences or journals, or prepare submission-ready PDFs.
---

# paper2tex — Academic Paper Word-to-LaTeX Converter

Converts academic `.docx` papers into publication-ready, compiling LaTeX documents tailored to any conference or journal theme (IEEE, ACM, Springer LNCS, Elsevier, NeurIPS, ICML, CVPR, MDPI, Nature).

## Quick Start

Run the end-to-end extraction and assembly pipeline:

```bash
# 1. Verify system toolchain
python -m scripts.preflight

# 2. Extract content, math (OMML), tables, figures, and bibliography
python -m scripts.extract input.docx work_dir/

# 3. Apply target conference theme (or analyze custom template zip)
python -m scripts.template_spec "ieee-conference" work_dir/

# 4. Assemble main.tex with seamless float flow & single-column layout
python -m scripts.assemble work_dir/

# 5. Compile and run visual QA verification
python -m scripts.compile work_dir/main.tex
python -m scripts.visual_qa work_dir/main.pdf work_dir/
```

## Workflow Stages

```
STAGE 0: PREFLIGHT       → Check pandoc, tectonic/latexmk, lxml, OMML2MML.XSL
STAGE 1: PREPROCESS      → Strip tracked changes, fix Symbol font trap, map field codes
STAGE 2: EXTRACT         → Parallel extractors for OMML math, tables, figures, bib
STAGE 3: THEME SPEC      → Match recipe (IEEE/ACM/LNCS) or research via Firecrawl
STAGE 4: AST ASSEMBLE    → Deterministic assembly with single-column first float rules
STAGE 5: COMPILE LOOP    → Engine selection (XeLaTeX/pdfLaTeX) + automated log auto-fix
STAGE 6: VERIFICATION    → Manifest diff + special character audit + Visual QA
STAGE 7: DELIVER         → submission/ folder (.tex, .bib, figures/, .pdf, report.md)
```

## Core Architectural Guarantees

1. **100% Verbatim Prose Preservation**: Maps Markdown AST directly to LaTeX. Zero dropped paragraphs, zero paraphrasing, zero text alteration.
2. **Seamless Float Flow**: Eliminates disruptive `\FloatBarrier` injections before sections. Floats place naturally (`[!t]`, `[b]`) with zero blank page voids.
3. **Single-Column First Layout**: Figures and tables default to single column (`\columnwidth`). Multi-panel subfigures pack tightly side-by-side without column disruption.
4. **Deterministic OMML Math**: Word equations convert directly to LaTeX via MathML XSLT — never through LLM text re-emission.
5. **Theme Versatility**: Dynamically configures author blocks, keywords, column modes, and bibstyles for any conference or journal venue.

## Documentation & References

- **Layout & Float Rules**: See [LAYOUT_GUIDELINES.md](LAYOUT_GUIDELINES.md) for figure sizing, subfigure geometry, and table formatting.
- **Themes & Firecrawl Research**: See [THEMES_AND_TEMPLATES.md](THEMES_AND_TEMPLATES.md) for venue recipes and online template research.
- **Technical Reference**: See [REFERENCE.md](REFERENCE.md) for extraction internals, symbol font mapping, and compiler auto-fix taxonomy.
- **Usage Examples**: See [EXAMPLES.md](EXAMPLES.md) for end-to-end sample workflows.
- **Curated Recipes**: See [recipes/](recipes/) for IEEE, ACM, Springer, Elsevier, NeurIPS, and Nature specifications.
