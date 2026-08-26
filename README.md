# 📄 paper2tex

> **Convert your Word paper to conference-formatted LaTeX — without the pain.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

---

## The Problem

Every semester, thousands of students go through this nightmare:

1. Write paper in Word (because that's what they know)
2. Conference requires LaTeX (`.tex`) format
3. Upload `.docx` to ChatGPT, ask for `.tex`
4. Copy-paste into Overleaf
5. **Fight errors for 3 hours** — `?` symbols everywhere, math corrupted, tables broken, references missing
6. Submit at 11:59 PM with bugs still in it

The root cause: **ChatGPT re-types your document through its tokenizer**, corrupting math, special characters (°, µ, ≈), and symbols along the way. It can't compile LaTeX, so it can't catch its own mistakes.

## The Solution

`paper2tex` is an **agent skill** (for [Antigravity](https://antigravity.dev), Claude Code, OpenCode, Cursor, etc.) that does this properly:

- **Deterministic extraction** — math is converted via Microsoft's own OMML→MathML→LaTeX pipeline, never through an LLM
- **Direct XML parsing** — tables with merged cells, cross-references, and citations are handled by parsing the `.docx` XML directly
- **Auto-compile and fix** — runs LaTeX compiler, reads error logs, fixes issues automatically, recompiles (up to 10 iterations)
- **Verification gate** — checks section counts, figure counts, citation integrity, and special characters in the final PDF before delivery
- **Your text is sacred** — zero rewording, zero "improvements", verbatim extraction guaranteed

## Supported Conferences

Built-in tier-1 recipes for the most common templates:

| Conference | Template Class | Engine |
|-----------|---------------|--------|
| IEEE Conference | `IEEEtran` | xelatex |
| IEEE Transaction/Journal | `IEEEtran` | xelatex |
| ACM SIGCONF | `acmart` | xelatex |
| Springer LNCS | `llncs` | xelatex |
| NeurIPS | `neurips` | xelatex |
| ICML | `icml` | pdflatex |
| CVPR | `cvpr` | pdflatex |

**Any other template**: just provide the conference template `.zip` file and the skill will analyze it automatically.

---

## Quick Start

### 1. Install Prerequisites

```powershell
# Windows (PowerShell)
winget install JohnMacFarlane.Pandoc
winget install tectonic                # or: scoop install tectonic

# Python packages
pip install lxml python-docx requests
```

### 2. Clone This Repo

```bash
git clone https://github.com/redfries/paper2tex.git
cd paper2tex
pip install -e .
```

### 3. Check Everything Works

```bash
python scripts/preflight.py
```

### 4. Use It

#### With an AI Agent (Recommended)

Just tell your agent:

```
Convert my paper.docx to IEEE conference format
```

or

```
Format my thesis.docx for ACM SIGCONF, my figures are in the figs/ folder
```

The agent reads `SKILL.md`, follows the 7-stage pipeline, and delivers a ready-to-submit package.

#### Manual CLI

```bash
# Step 1: Extract everything from the docx
python scripts/extract.py paper.docx work/

# Step 2: Analyze the template
python scripts/template_spec.py "IEEE conference" work/

# Step 3: (Agent assembles main.tex using the registries)

# Step 4: Compile
python scripts/compile.py work/main.tex

# Step 5: Verify
python scripts/verify.py work/main.tex

# Step 6: Package for Overleaf
python scripts/overleaf_export.py work/submission/
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    paper2tex Pipeline                           │
│                                                                 │
│  student.docx ──► PREPROCESS ──► EXTRACT ──► ASSEMBLE          │
│                   (Symbol fix,   (Math,       (LLM maps         │
│                    cross-refs,    Tables,      content into      │
│                    citations)     Figures,     template)         │
│                                  Bib)                           │
│                                                                 │
│  ──► LINT ──► COMPILE-FIX ──► VERIFY ──► DELIVER               │
│      (chktex,  (tectonic,      (log audit,  (main.tex,         │
│       escape    14-pattern      manifest     references.bib,    │
│       chars)    error fix)      diff, char   figures/,          │
│                                 spot-check)  main.pdf,          │
│                                              report.md,         │
│                                              overleaf.zip)      │
└─────────────────────────────────────────────────────────────────┘
```

### The Key Insight: What the LLM Does vs. What It Doesn't

| Component | Handled by | Why |
|-----------|-----------|-----|
| Text extraction | **Pandoc** (deterministic) | Never corrupts prose |
| Math conversion | **OMML→MathML→LaTeX pipeline** (deterministic) | Never produces `?` symbols |
| Table reconstruction | **Direct XML parsing** (deterministic) | Pandoc breaks on merged cells |
| Figure extraction | **File operations** (deterministic) | Original quality, scans external folders |
| Bibliography | **AnyStyle + Crossref** (deterministic) | LLMs hallucinate DOIs |
| Cross-references | **XML field code parsing** (deterministic) | Bookmark→`\label{}`/`\ref{}` map |
| Special characters | **Mapping table** (deterministic) | °→`\textdegree{}`, µ→`\textmu{}` |
| **Template mapping** | **LLM** ✨ | Arranging content into the template format — the one job it's good at |
| Compilation | **tectonic/latexmk** (deterministic) | Real compiler, real error logs |
| Verification | **pdftotext + manifest diff** (deterministic) | Catches what the compiler misses |

The LLM is confined to **structural mapping only** — arranging your already-extracted content into the conference template. Everything else is deterministic tooling that can't hallucinate.

---

## Project Structure

```
paper2tex/
├── SKILL.md                      # Agent workflow instructions (start here)
├── README.md                     # You are here
├── LICENSE                       # MIT
├── pyproject.toml                # Python dependencies
│
├── scripts/
│   ├── preflight.py              # Check tool availability
│   ├── preprocess.py             # Symbol font fix, cross-refs, tracked changes
│   ├── extract.py                # Main orchestrator (chains all extractors)
│   ├── extract_math.py           # OMML → MathML → LaTeX
│   ├── extract_tables.py         # XML table parsing + merged cells
│   ├── extract_figures.py        # Embedded + external figure reconciliation
│   ├── extract_bib.py            # Bibliography: Zotero/AnyStyle/Crossref
│   ├── template_spec.py          # Template analysis + 7 tier-1 recipes
│   ├── compile.py                # Compile-fix loop + error classifier
│   ├── verify.py                 # 6-check QA gate + report.md
│   ├── visual_qa.py              # PDF → PNG rendering for visual check
│   ├── overleaf_export.py        # Package into Overleaf-ready zip
│   ├── docling_extract.py        # Optional: IBM Docling for complex docs
│   │
│   ├── prompts/
│   │   ├── rules.md              # 10 hard constraints for LLM assembly
│   │   ├── assemble_section.md   # Per-section assembly prompt template
│   │   └── assemble_preamble.md  # Preamble + author block prompt
│   │
│   └── utils/
│       └── char_map.py           # 100+ Unicode → LaTeX mappings
│
└── tests/
    └── generate_corpus.py        # Generate synthetic test papers
```

---

## FAQ

**"Will it change my text?"**
No. The #1 rule in `SKILL.md` is **verbatim text preservation**. The LLM is explicitly forbidden from rewording, "improving", or reorganizing your prose. Your words stay exactly as written.

**"What about the `?` symbols I keep getting?"**
The `?` bug has three causes: (1) pdflatex can't handle Unicode like ° or µ — we use **xelatex** by default; (2) the LLM re-types math through its tokenizer — we **never** let the LLM touch math; (3) BibTeX keys don't match — our verification gate catches this before delivery.

**"My figures are in a separate folder, not in the .docx"**
The skill auto-scans `figures/`, `figs/`, `images/`, `img/`, `media/`, `assets/` directories next to your `.docx`. It also prefers external files (especially vector formats like PDF/SVG) over the lower-quality embedded copies. You can also pass `--figures-dir` explicitly.

**"Do I need a full TeX Live install (6+ GB)?"**
No. We use **Tectonic** — a single binary that downloads only the packages it needs, on demand. One-command install, ~50 MB.

**"Can I use this with Overleaf?"**
Yes! The skill generates an `overleaf.zip` containing `main.tex`, `references.bib`, and all figures. Just upload it: Overleaf → New Project → Upload Project.

**"What if my paper has MathType equations (legacy)?"**
Legacy MathType equations (OLE objects) can't be extracted deterministically. The skill detects them and flags a warning in the report. You'll need to re-enter those equations manually (or use the equation editor in Word 2016+, which uses OMML that we handle perfectly).

---

## How to Add a New Conference Recipe

Edit `scripts/template_spec.py` and add an entry to `TIER1_RECIPES`:

```python
"your-conference": {
    "name": "Your Conference 2026",
    "document_class": "yourclass",
    "class_options": ["option1"],
    "engine": "xelatex",
    "bib_style": "yourbst",
    "bib_engine": "bibtex",
    "column_mode": "twocolumn",
    "author_format": "\\author{NAME}\\affiliation{INST}",
    "keywords_cmd": "\\keywords{...}",
},
```

Then submit a PR! We especially need recipes for: AAAI, EMNLP, ICLR, ECCV, MICCAI, Elsevier journals, Springer journals.

---

## Contributing

We welcome contributions! Especially:
- **New tier-1 recipes** for conferences you use
- **Test corpus papers** (anonymized `.docx` files that exercise edge cases)
- **Bug reports** with the `.docx` file that failed (anonymize sensitive content)
- **Error classifier patterns** for the compile-fix loop

See [Issues](../../issues) to get started.

## License

MIT — see [LICENSE](LICENSE).
