# 📄 paper2tex

> **Convert your Word paper into conference-formatted LaTeX in seconds — with 0 corrupted math, 0 question marks, and perfectly formatted figures.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

---

## 😫 The Problem Everyone Faces

Every semester, students and researchers go through the same nightmare:

```
[Write in Word] ──► [Paste into ChatGPT] ──► [Paste in Overleaf] ──► [3 Hours of Errors]
                         (Tokenizer ruins         (Missing packages,
                          math & ° symbols)        broken tables & figures)
```

1. **ChatGPT re-types your document through its tokenizer**, corrupting equations, degree symbols (`°`), Greek letters, and chemical subscripts (`CO2`).
2. **Figures get squished, rotated sideways, or clustered** at the very end of the PDF.
3. You spend hours fighting red LaTeX errors right before the submission deadline.

---

## ✨ The Solution: paper2tex

`paper2tex` is an **AI agent skill** that uses a 100% deterministic local toolchain:

* ✅ **Verbatim Text** — Zero rewording or "hallucinations". Your exact prose is preserved.
* ✅ **Perfect Math** — Equations are extracted directly from Microsoft Word's XML equation engine (`OMML → MathML → LaTeX`).
* ✅ **Smart Figures** — Automatically handles subfigures `(a)`, `(b)`, `(c)`, auto-corrects rotated/sideways images, and scales them cleanly to column width.
* ✅ **Auto-Compile & Fix** — Compiles locally, reads the error log, automatically repairs missing packages, and produces a publication-ready PDF.

---

## 🚀 1-Click Install for AI Agents (Copy & Paste)

Copy and paste this single prompt directly into **Antigravity, Claude Code, Cursor, OpenCode, Codex, or Windsurf**:

```text
Install the paper2tex skill globally. Clone https://github.com/redfries/paper2tex.git into my global agent skills directory (or ~/.gemini/antigravity/skills/paper2tex, ~/.claude/skills/paper2tex, or current workspace skills), ensure prerequisites are installed (pandoc, tectonic, and python packages: lxml, python-docx, Pillow, pymupdf, requests), and run `python scripts/preflight.py` to verify that paper2tex is ready.
```

---

## ⚡ How to Ask Your Agent to Convert a Paper

To make sure your AI uses `paper2tex`'s local toolchain (instead of trying to rewrite the document from memory), use an explicit command:

```text
Use paper2tex skill to convert "paper.docx" into IEEE conference format.
```

Or for other conferences/journals:

```text
Use paper2tex skill to format "thesis.docx" for ACM SIGCONF, my figures are in ./figures.
```
```text
Run paper2tex on "manuscript.docx" targeting Springer LNCS.
```

---

## 🖼️ How to Provide Figures (The Visual Guide)

`paper2tex` is designed to handle figures cleanly even if you are non-technical.

### 1. The Recommended Folder Structure

Place your Word file and an optional `figures/` folder in the same place (supports `.png`, `.jpg`, `.pdf`, `.svg`):

```
my_paper_project/
│
├── my_paper.docx               <-- Your main paper draft
│
└── figures/                    <-- (Optional folder with your images)
    ├── fig1_a.png              <-- Subfigure (a) (Regular PNG, JPG, or PDF)
    ├── fig1_b.png              <-- Subfigure (b)
    ├── fig1_c.png              <-- Subfigure (c)
    ├── fig2.png                <-- Standalone Figure 2
    └── fig3.pdf                <-- (Optional) Vector PDF plot from Python/Matplotlib
```

> 💡 **Any format works!** You can use everyday `.png` or `.jpg` images, or export vector `.pdf` / `.svg` plots from Python/MATLAB. Or if you don't have a folder, just say **`extract`** and `paper2tex` gets them right out of Word!

---

### 2. Single Figures vs. Multi-Panel Subfigures

Here is how to set up your images and captions in Word so the output is flawless:

#### Case A: Single Figure (1 Image)

```
[ Your Chart or Image ]

Caption in Word:
Fig. 2: System performance comparison under varied load conditions.
```
* **What paper2tex does**: Scales the image to fit the exact column width cleanly and anchors the caption directly underneath.

---

#### Case B: Multi-Panel Subfigures (a, b, c)

When you have multiple related diagrams in one figure:

```
┌────────────────────────────────────────┐
│  [ Subfigure A: Greenfield Layout ]    │  <-- (a)
├────────────────────────────────────────┤
│  [ Subfigure B: Partial Reuse Layout ] │  <-- (b)
├────────────────────────────────────────┤
│  [ Subfigure C: Maximal Reuse Layout ] │  <-- (c)
└────────────────────────────────────────┘

Caption in Word:
Fig. 1: The three different scenarios. (a) Case #1: greenfield nuclear power plant; (b) Case #2: reuse of retiring coal plant infrastructure; (c) Case #3: maximal reuse of turbine components.
```

* **What paper2tex does**:
  1. Detects `(a)`, `(b)`, `(c)` automatically.
  2. Splits the main title from each sub-description.
  3. Stacks wide landscape schematics vertically (or places tall charts side-by-side) with official `(a)`, `(b)`, `(c)` subcaptions beneath each panel.
  4. Rotates any sideways images upright automatically.

---

### 3. The Upfront Clarification Question

When you tell an AI agent to run `paper2tex`, the agent will ask:
> *"Do you have a dedicated `figures/` folder with high-resolution/vector images (e.g., `./figures`), or should I extract the embedded images directly from the Word document?"*

* **Simply reply `extract`**: The agent will extract, auto-rotate, and format all embedded images directly from your `.docx`.
* **Or reply with your folder path** (e.g., `./figures`): The agent will use your high-res vector (`.pdf`, `.svg`) or 300+ DPI images for crystal-clear print quality.

---

## 📋 Supported Conferences & Journals

`paper2tex` includes built-in recipes for all major academic templates:

| Venue / Organization | Template Class | Output Engine | Default Columns |
|---|---|---|---|
| **IEEE Conferences** | `IEEEtran` | XeLaTeX | 2 Columns |
| **IEEE Transactions & Journals** | `IEEEtran` | XeLaTeX | 2 Columns |
| **ACM SIGCONF (CCS, CHI, SIGMOD)** | `acmart` | XeLaTeX | 2 Columns |
| **Springer LNCS** | `llncs` | XeLaTeX | 1 Column |
| **NeurIPS** | `neurips` | XeLaTeX | 1 Column |
| **ICML / CVPR** | `icml` / `cvpr` | pdfLaTeX / XeLaTeX | 2 Columns |
| **Elsevier / MDPI / Nature** | Generic / Custom | XeLaTeX | Custom |

> 💡 **Have a custom conference template?** Just provide the template `.zip` file from the conference website. `paper2tex` will automatically extract its `.cls` file and configure the preamble.

---

## 🛠️ Manual Installation & CLI (For Developers)

If you prefer to run `paper2tex` manually from your command line:

### 1. Install System Tools

```powershell
# Windows (PowerShell)
winget install JohnMacFarlane.Pandoc
winget install tectonic

# Python Dependencies
pip install lxml python-docx Pillow pymupdf requests
```

### 2. Clone & Install

```bash
git clone https://github.com/redfries/paper2tex.git
cd paper2tex
pip install -e .
```

### 3. Verify System Setup

```bash
python scripts/preflight.py
```

### 4. Run the Pipeline

```bash
# 1. Extract content and figures
python scripts/extract.py paper.docx work/

# 2. Select target template
python scripts/template_spec.py "ieee-conference" work/

# 3. Assemble publication-ready LaTeX
python scripts/assemble.py work/

# 4. Compile to PDF with automatic fix loop
python scripts/compile.py work/main.tex

# 5. Verify character & citation fidelity
python scripts/verify.py work/main.tex
```

---

## ❓ Frequently Asked Questions (FAQ)

#### Will this change or reword my writing?
**Never.** The #1 core rule of `paper2tex` is **100% verbatim text preservation**. No text is summarized, reworded, or dropped.

#### Why did my figures look tiny or sideways before?
Microsoft Word stores rotated images with internal rotation angle transforms (`rot=5400000`). If tools extract the raw file without reading Word's XML transform, the image displays sideways. `paper2tex` reads the OpenXML transformation tags and normalizes every graphic with Pillow so it appears upright and at full readability.

#### Can I upload the output to Overleaf?
**Yes!** `paper2tex` produces an `overleaf.zip` inside `work/submission/`. You can upload this zip file directly into Overleaf (Overleaf → *New Project* → *Upload Project*) and compile instantly with 0 errors.

#### Do I need to install a 6 GB TeX Live distribution?
**No.** `paper2tex` uses **Tectonic** by default — a lightweight, modern TeX engine that automatically downloads only the packages your document requires on the fly (~50 MB).

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details. Open-source and free for all students, researchers, and developers.
