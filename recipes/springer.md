# Springer Publication Recipe (LNCS, Springer Nature)

## Profile
- **Document Classes:**
  - Springer LNCS: `\documentclass{llncs}`
  - Springer Nature Journal: `\documentclass[sn-mathphys]{sn-jnl}`
- **Class Options:** Default single-column / standard page geometry
- **Compiler Engine:** `xelatex` (recommended) or `pdflatex`
- **Column Mode:** One-column (`onecolumn`)
- **Bibliography:** `\bibliographystyle{splncs04}` (LNCS) or `\bibliographystyle{sn-mathphys}` (Springer Nature)

## Float & Layout Rules
- **One-Column Layout:** Since LNCS is single-column, all figures use `\begin{figure}[!t]` with `width=0.9\textwidth` or `\linewidth`.
- **Subfigures:** Arranged side-by-side using `width=0.48\linewidth` (2 subfigures) or `width=0.31\linewidth` (3 subfigures).
- **Tables:** `\begin{table}[!t]` centered with `booktabs` rules.

## Author & Metadata Structure
```latex
\title{Paper Title}
\author{First Author\inst{1} \and Second Author\inst{2}}
\institute{First Institute, City, Country \email{author1@domain.com} \and
Second Institute, City, Country \email{author2@domain.com}}

\maketitle

\begin{abstract}
Abstract text verbatim from source.
\keywords{keyword1 \and keyword2 \and keyword3}
\end{abstract}
```

## Special Constraints
- LNCS does NOT support `hyperref` with certain options enabled without care.
- Springer Nature (`sn-jnl`) has pre-packaged fonts and citation styles.
