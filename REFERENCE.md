# paper2tex — Technical Reference & Architecture

This reference document provides technical specifications for the extraction, assembly, compilation, and verification pipelines in `paper2tex`.

---

## 1. Deterministic Extraction Pipeline

### 1.1 Math Conversion (OMML → MathML → LaTeX)
- Native Word equations are stored in OpenXML as Office Math Markup Language (`<m:oMath>` / `<m:oMathPara>`).
- We convert OMML to MathML using Microsoft Office's native `OMML2MML.XSL` stylesheet (via `lxml.etree.XSLT`), then parse MathML directly to clean LaTeX math expressions.
- **Guarantee**: Equations, fractions, summation bounds, matrix structures, Greek letters, and accents are converted deterministically without hallucination or truncation.

### 1.2 Table Extraction & XML Parsing
- Tables are parsed directly from `<w:tbl>` XML elements.
- Handles cell colspans (`<w:gridSpan>`), rowspans (`<w:vMerge>`), and text alignment (`<w:jc>`).
- Auto-generates clean `booktabs` LaTeX with `\toprule`, `\midrule`, `\bottomrule`, and `\cmidrule(lr){...}` for grouped multi-column subheaders.

### 1.3 Figure & Media Reconciliation
- Embedded images are extracted directly from `word/media/` inside the docx zip archive.
- Extents (`<wp:extent cx="..." cy="...">`) are converted from EMUs (English Metric Units) to compute aspect ratio and orientation.
- Scans external directories (e.g. `figures/`, `img/`, `assets/`) for high-resolution or vector replacements (`.pdf`, `.svg`, `.eps`).

### 1.4 Bibliography Parsing & Crossref Validation
- Extracts reference entries from the bibliography section or citation manager fields (Zotero, Mendeley, EndNote).
- Cleans and structures entries into standard BibTeX (`@article`, `@inproceedings`, `@book`, `@techreport`, `@misc`).
- Reconciles missing DOIs, URLs, and metadata via Crossref API when enabled.

---

## 2. Special Characters & Symbol Font Trap Defense

Word documents frequently contain legacy Symbol font encodings where ASCII letters represent Greek characters (e.g., ASCII `m` in Symbol font renders as `μ`, ASCII `a` renders as `α`).
The preprocessor (`scripts/preprocess.py`) intercepts all `<w:r>` elements with `<w:rFonts w:ascii="Symbol"/>` and maps character codes directly to Unicode codepoints (U+03B1 for α, U+03BC for μ, U+00B0 for °, U+2248 for ≈, etc.).

---

## 3. Package Auto-Detection Matrix

| Detected Content | Auto-loaded Package | Rationale |
|---|---|---|
| Math equations & alignments | `amsmath`, `amssymb` | `align`, `equation`, math symbols |
| Professional tables | `booktabs` | `\toprule`, `\midrule`, `\bottomrule` |
| Multi-row table cells | `multirow` | `\multirow` command support |
| Graphics & figures | `graphicx` | `\includegraphics` support |
| Hyperlinks & citations | `hyperref` | Interactive PDF links |
| Cross-references | `cleveref` | Semantic `\cref{...}` cross-referencing |
| SI units & degrees | `textcomp` / `siunitx` | Clean `°C`, `µm`, currency symbols |
| Bibliography sorting | `cite` (IEEE) / `natbib` | Numeric & author-year citation sorting |

---

## 4. Compiler Auto-Fix Taxonomy

During the compile-fix loop (`scripts/compile.py`), the compiler catches and automatically repairs common TeX diagnostics:

| Log Error Pattern | Root Cause | Automatic Repair |
|---|---|---|
| `Undefined control sequence \X` | Missing macro or symbol package | Injects required package or defines macro |
| `Package X Not found` | Missing style file | Adds safe fallback package or downloads via tectonic |
| `Citation 'key' undefined` | In-text key mismatch with `.bib` | Aligns key between `.tex` and `references.bib` |
| `Reference 'label' undefined` | Missing anchor label | Adds `\label{}` at corresponding figure/table/section |
| `Environment align undefined` | Missing AMS math | Injects `\usepackage{amsmath,amssymb}` |
| `Option clash for package X` | Duplicate package import | Deduplicates package inclusion in preamble |
