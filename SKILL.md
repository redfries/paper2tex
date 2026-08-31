---
name: paper2tex
description: >
  Convert academic .docx papers to conference-formatted LaTeX (.tex) files.
  Deterministic extraction pipeline + constrained LLM assembly + compile-fix loop + verification gate.
  Supports IEEE, ACM, LNCS, NeurIPS, ICML, and any template the student provides.
---

# paper2tex — Convert Academic Papers from Word to LaTeX

## When to Activate

Trigger this skill when the user asks to:
- "convert my paper to latex"
- "format this docx for IEEE / ACM / conference"
- "make this docx a .tex for \<conference\>"
- "docx to overleaf"
- "convert my Word paper to \<conference\> format"
- "prepare my paper for submission"
- "format my paper for \<journal/conference\>"

## What This Skill Does

Takes a student's `.docx` academic paper + a conference template and produces:
- A compiling `.tex` file formatted to the conference template
- A verified `references.bib`
- All figures at best available quality
- A compiled `.pdf`
- A QA report (`report.md`) the student can use as a checklist

## Prerequisites

Run `scripts/preflight.py` first to check all tools are installed:
```
python scripts/preflight.py
```

Required: `pandoc`, `lxml`, `python-docx`, and either `tectonic` or `latexmk`.
Recommended: `pdftotext` (for character verification), `OMML2MML.XSL` (for optimal math conversion).

## Pipeline Overview

```
STAGE 0: PREFLIGHT → check tools (pandoc, tectonic/latexmk, lxml)
STAGE 1: PRE-PROCESS → fix Symbol font trap, extract field codes, cross-ref map
STAGE 2: EXTRACT → parallel pipelines for text, math, tables, figures, bibliography
STAGE 3: ASSEMBLE → Deterministic AST Assembler (scripts/assemble.py)
STAGE 4: COMPILE-FIX → tectonic/latexmk loop with error classifier
STAGE 5: VERIFY → QA Gate + Bidirectional Text Fidelity & Hallucination Checker
STAGE 6: DELIVER → submission/ folder with verified main.tex, .bib, figures, .pdf
```

## Step-by-Step Workflow

### Step 1: Gather Inputs

Ask the user for:
1. **The `.docx` file** — the paper to convert
2. **The conference template** — one of:
   - A template zip file (e.g., `IEEEtran.zip`)
   - A conference name (e.g., "IEEE journal/conference", "ACM SIGCONF", "NeurIPS 2026")
   - A sample `.tex` file from the conference
3. **External figures directory** (optional) — if figures are in a separate folder

### Step 2: Pre-process the Document

Run the preprocessor on the `.docx`:
```python
from scripts.preprocess import preprocess_docx
result = preprocess_docx(docx_path, work_dir)
```

This fixes:
- **Symbol font trap** (ASCII chars masquerading as Greek letters)
- **Tracked changes** (accepts all)
- **Comments** (stripped)
- **Cross-references** (field codes → semantic label map)
- **Citation manager detection** (Zotero/Mendeley/EndNote)

### Step 3: Extract Content (Parallel Pipelines)

Run all extractors. Each produces a registry JSON file:

```python
from scripts.extract_math import extract_math
from scripts.extract_tables import extract_tables
from scripts.extract_figures import extract_figures
from scripts.extract_bib import extract_bibliography

# Math: OMML → MathML → LaTeX (deterministic, never use LLM for math)
math_reg = extract_math(docx_path, work_dir)

# Tables: direct XML parsing, 2-column wide table* auto-fit, cmidrule generation
table_reg = extract_tables(docx_path, work_dir)

# Figures: DrawingML extents, aspect ratio/orientation, subfigure grouping, external reconciliation
fig_reg = extract_figures(docx_path, work_dir, figures_dir=user_figures_dir)

# Bibliography: XML relationship target URL extraction, IEEE [Online]. Available: clean formatting, Crossref
bib_reg = extract_bibliography(docx_path, work_dir,
    citation_type=result.citation_type,
    verify_crossref=True)
```

Also run Pandoc for bulk text:
```
pandoc paper.docx -f docx -t markdown -o work/content.md
pandoc paper.docx -f docx -t latex -o work/content.tex
```

### Step 4: Deterministic AST Assembly (`scripts/assemble.py`)

Run the deterministic AST Assembler to build `main.tex`:
```powershell
python scripts/assemble.py work_dir/
```

#### Core Architectural Guarantees:
1. **100% Verbatim Prose Preservation**: Maps markdown AST blocks directly into LaTeX. Zero dropped paragraphs, zero paraphrasing, zero hallucinated additions.
2. **Exact Figure & Section Anchoring**: Automatically inserts `\usepackage{placeins}` and `\FloatBarrier` before every `\section{}` and `\subsection{}` to prevent figures from drifting into subsequent sections.
3. **Subfigure & Standalone Figure Layout**: Multi-panel subfigures (e.g. Figure 1 panels a, b, c) are rendered in a 2-column `\begin{figure*}` block with `\hfill` and `width=0.31\textwidth`, while standalone landscape charts are properly centered and scaled.
4. **2-Column Wide Table Auto-Fit**: 4+ column tables automatically render in `\begin{table*}` with full-width `tabular*` and `\cmidrule(lr){...}` grouped subheaders.
5. **Interactive Clickable Hyperlinks**: In-text citations (`[1]`, `[2]`, `[3]`) and bibliography entries are hyperlinked with `\usepackage{hyperref}`.
6. **No content changes** — EVER. The student's text is preserved 100% verbatim.

#### TEMPLATE STRUCTURE

Read the template spec to determine:
- Document class and options
- Required packages (from template)
- Author block format
- Bibliography style
- Column mode (one-column vs two-column)
- Engine requirements (xelatex vs pdflatex)

Build `main.tex` with this structure:
```latex
\documentclass[...]{template_class}
% --- Template-required packages ---
\usepackage{...}
% --- Content-detected packages ---
\usepackage{amsmath,amssymb}    % if equations present
\usepackage{graphicx}            % if figures present
\usepackage{booktabs,multirow}   % if tables present
\usepackage{cleveref}            % for cross-references
\usepackage{siunitx}             % if units present
% ...

\begin{document}

\title{...}                      % verbatim from source
\author{...}                     % mapped to template format

\maketitle

\begin{abstract}
...                              % verbatim from source
\end{abstract}

\section{Introduction}           % section title verbatim
...                              % body text verbatim
...                              % math from registry
...                              % \cref{} from cross-ref map

\section{...}
...

\bibliographystyle{...}          % from template spec
\bibliography{references}

\end{document}
```

### Step 5: Compile and Fix

```python
from scripts.compile import compile_latex
result = compile_latex(work_dir / "main.tex", max_iterations=10)
```

If compilation fails with errors the auto-fixer can't handle, read the error, fix the specific line (markup only, never content), and recompile.

### Step 6: Verify

```python
from scripts.verify import verify_output
result = verify_output(
    tex_path=work_dir / "main.tex",
    pdf_path=work_dir / "main.pdf",
    bib_path=work_dir / "references.bib",
    manifest_path=work_dir / "manifest.json",
)
```

If verification fails, fix the issue and re-verify. Common failures:
- Missing `\label{}` → add it at the right anchor
- Hardcoded "Figure N" → replace with `\cref{fig:...}`
- Special chars missing in PDF → check xelatex/fontspec setup
- Citation key mismatch → align keys between .tex and .bib

### Step 7: Deliver

Organize the output:
```
submission/
├── main.tex           ← the formatted paper
├── references.bib     ← verified bibliography
├── figures/            ← best quality figures
├── main.pdf            ← compiled output
└── report.md           ← QA checklist for the student
```

Present `report.md` to the student with a summary of what was converted, what was verified, and any remaining TODOs.

## Package Detection Rules

Auto-detect and add packages based on content:

| Detected content | Package | Why |
|---|---|---|
| Display equations | `amsmath`, `amssymb` | align, equation, cases |
| Multi-row tables | `multirow` | \multirow command |
| Professional tables | `booktabs` | toprule, midrule, bottomrule |
| Subfigures | `subcaption` | subfigure environment |
| Cross-references | `cleveref` | \cref, \Cref |
| Units (°C, µm) | `siunitx` | proper unit formatting |
| Algorithms | `algorithm`, `algorithmicx` | algorithm environment |
| Code listings | `listings` | lstlisting environment |
| Unicode + xelatex | `fontspec` | font handling |
| Graphics | `graphicx` | includegraphics |

## Explicit Non-Goals

- **NOT a rewriting/polishing tool.** If the student asks to "improve" the writing, decline.
- **NOT a translation tool.** Content must stay in its original language.
- **NOT Overleaf.** Output is files, not an editor. (Optional: produce overleaf.zip for upload.)
- **No account, no cloud, no telemetry.** Everything is local.

## Error Recovery

If you encounter issues during any step:
1. Check `report.md` for specific failures
2. For math issues: re-run `extract_math.py` and check the OMML pipeline output
3. For table issues: re-run `extract_tables.py` and verify merged cell handling
4. For figure issues: check that all `\includegraphics` paths resolve
5. For citation issues: verify `.bib` keys match `\cite{}` keys in the .tex
6. For the `?` bug: ensure xelatex is used (not pdflatex), and check `fontspec` / `textcomp` packages
