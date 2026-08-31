# paper2tex — Theme & Template Architecture

Academic publishing involves diverse submission venues (IEEE, ACM, Springer, Elsevier, Nature, NeurIPS, ICML, CVPR, MDPI), each with distinct document classes, author metadata schemas, font families, citation systems, and column structures.

This guide outlines how the `paper2tex` pipeline adapts to any conference or journal theme at every stage, and how to use Firecrawl to retrieve live template specifications.

---

## 1. Pipeline Adaptation by Stage

```
[Docx Input + Target Theme]
       │
STAGE 0: PREFLIGHT ────────► Validate compiler engines (XeLaTeX/pdfLaTeX/LuaLaTeX)
STAGE 1: PREPROCESS ───────► Parse headings and structure to match theme conventions
STAGE 2: EXTRACT ──────────► Extract math, tables, figures, bibliography with metadata
STAGE 3: THEME SPEC ───────► Match tier-1 recipe OR research via Firecrawl
STAGE 4: AST ASSEMBLE ─────► Generate theme-tailored main.tex (authors, columns, floats)
STAGE 5: COMPILE LOOP ─────► Engine selection + automated package conflict resolution
STAGE 6: VERIFICATION ─────► Validate theme compliance (citations, fonts, page budget)
STAGE 7: DELIVER ──────────► Produce submission/ directory with all required files
```

### Stage 0: Preflight Engine Check
- **Unicode-first themes** (IEEE, Springer Nature, MDPI) run optimally on `xelatex` or `lualatex`.
- **Legacy macro templates** (certain ICML/CVPR distributions) run on `pdflatex`.
- Preflight automatically confirms availability of `pandoc`, `tectonic`, `pdftotext`, and Python dependencies.

### Stage 1: Document Structure & Heading Normalization
- Different themes use different numbering schemes:
  - **IEEE**: Roman uppercase section numbers (`I. INTRODUCTION`, `A. Subsection`)
  - **ACM**: Arabic numbers (`1 Introduction`, `1.1 Subsection`)
  - **Nature / Science**: Unnumbered bold headers (`\section*{Results}`)
- The AST assembler preserves the verbatim heading title while letting the template document class govern numbering.

### Stage 2: Feature & Constraint Extraction
- **Bibliography Format**: Detects whether the theme uses numeric bracketed citations (`[1]`, `[2]`), superscript numbers (`^1`), or author-year (`(Smith et al., 2024)`).
- **Subfigure packages**: Checks if the target theme permits `subcaption`, `subfig`, or requires native side-by-side subfigure blocks.

### Stage 3: Theme Discovery & Firecrawl Research
When a user specifies a conference name or URL:
1. **Tier-1 Local Match**: Checks `recipes/` (IEEE, ACM, Springer LNCS, Elsevier, NeurIPS, ICML, CVPR, Nature).
2. **Template Zip Extraction**: If a template `.zip` or sample `.tex` is provided, `scripts/template_spec.py` mechanically extracts the preamble, author block format, and `.bst` style.
3. **Firecrawl Online Research**: When given an unfamiliar conference name or journal URL, use Firecrawl tools to research the official author submission guidelines:
   - Search: `firecrawl_search("IEEE Transactions on Robotics author LaTeX template submission guidelines")`
   - Scrape: `firecrawl_scrape(url)` to inspect official `.cls`, `.bst`, column mode, and page limit rules.

### Stage 4: Theme-Aware AST Assembly
- **Author & Affiliation Blocks**:
  - **IEEE**: `\IEEEauthorblockN{...}\IEEEauthorblockA{...}`
  - **ACM**: `\author{...}\affiliation{\institution{...}}\email{...}` (abstract and keywords placed BEFORE `\maketitle`)
  - **Springer LNCS**: `\author{...}\institute{...}`
  - **Elsevier cas-dc**: `\author[1]{...}\affiliation[1]{...}`
- **Float Placement & Sizing**:
  - Automatically switches between two-column compact mode and one-column book mode based on `template-spec.json`.

### Stage 5: Compiler Loop & Package Defense
- Avoids theme package collisions:
  - `acmart` already loads `amsmath` and `hyperref` (reloading triggers option clash).
  - `IEEEtran` conflicts with standard `caption` package formatting.
  - `llncs` requires custom handling for `hyperref`.

### Stage 6 & 7: Verification & Packaging
- Ensures all bibliography keys resolve against the theme's `.bst`.
- Verifies that all figures referenced in `\includegraphics` resolve in the theme's graphicspath.
- Bundles `.cls`, `.bst`, `main.tex`, `references.bib`, and `figures/` into a complete zip ready for submission or Overleaf.

---

## 2. Supported Theme Recipes

Detailed recipes are available in the `recipes/` directory:
- [IEEE Recipe](file:///c:/Users/lords/OneDrive/Documents/skills/paper2tex/recipes/ieee.md): Conference, Transactions, Letters
- [ACM Recipe](file:///c:/Users/lords/OneDrive/Documents/skills/paper2tex/recipes/acm.md): SIGCONF, TOG, TWEB, ACM Small
- [Springer Recipe](file:///c:/Users/lords/OneDrive/Documents/skills/paper2tex/recipes/springer.md): LNCS, Springer Nature (`sn-jnl`)
- [Elsevier Recipe](file:///c:/Users/lords/OneDrive/Documents/skills/paper2tex/recipes/elsevier.md): cas-dc, cas-sc, elsarticle
- [ML Conferences Recipe](file:///c:/Users/lords/OneDrive/Documents/skills/paper2tex/recipes/ml_conferences.md): NeurIPS, ICML, ICLR, CVPR
- [Nature & Science Recipe](file:///c:/Users/lords/OneDrive/Documents/skills/paper2tex/recipes/nature_science.md): Nature, Science, MDPI, PLOS
