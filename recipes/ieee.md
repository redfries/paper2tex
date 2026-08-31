# IEEE Publication Recipe (Conference & Transactions)

## Profile
- **Document Classes:** `IEEEtran`
- **Class Options:**
  - Conference: `\documentclass[conference]{IEEEtran}`
  - Journal/Transaction: `\documentclass[journal]{IEEEtran}`
  - Letters: `\documentclass[journal,10pt,twocolumn]{IEEEtran}`
- **Compiler Engine:** `xelatex` (Unicode-native default) or `pdflatex`
- **Column Mode:** Two-column (`twocolumn`)
- **Bibliography:** `\bibliographystyle{IEEEtran}`, bib engine `bibtex`

## Float & Layout Rules
- **Single-Column First:** All standard figures and charts scale with `\columnwidth` / `\linewidth`.
- **Subfigures:** Grouped subfigures (e.g. 3 portrait panels a, b, c) are packed side-by-side inside ONE column using `width=0.31\linewidth` with `\hfill`.
- **Double-Column Spanning (`figure*` / `table*`):** Used ONLY for ultra-wide plots (aspect ratio > 2.2) or wide tables (>5 columns). Always use `[!t]` positioning.
- **Float Placement:** Use `[!t]`, `[b]`, `[htbp]`. Never insert `\FloatBarrier` before sections.
- **Tables:** Styled with `booktabs` (`\toprule`, `\midrule`, `\bottomrule`), `\footnotesize`, and `\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}...}`.

## Author & Metadata Structure
```latex
\title{Paper Title}
\author{
  \IEEEauthorblockN{Author Name}
  \IEEEauthorblockA{Department, University/Company, City, Country\\
  Email: author@domain.com}
}
\maketitle

\begin{abstract}
Abstract text verbatim from source.
\end{abstract}

\begin{IEEEkeywords}
Keyword1, Keyword2, Keyword3
\end{IEEEkeywords}
```

## Special Constraints
- Do NOT use package `caption` or `subcaption` without disabling IEEE caption overrides, or use native IEEE subfigures/side-by-side `\includegraphics`.
- In-text citations formatted via `\usepackage{cite}` as `\cite{key1, key2}` producing `[1], [2]` or `[1]--[3]`.
