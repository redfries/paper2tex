# Elsevier Publication Recipe (cas-dc, cas-sc, elsarticle)

## Profile
- **Document Classes:**
  - Complex Article Two-Column: `\documentclass[a4paper,fleqn]{cas-dc}`
  - Complex Article Single-Column: `\documentclass[a4paper,fleqn]{cas-sc}`
  - Standard Elsevier: `\documentclass[5p,twocolumn]{elsarticle}` or `\documentclass[review]{elsarticle}`
- **Compiler Engine:** `xelatex` or `pdflatex`
- **Column Mode:** Two-column for `cas-dc` / `5p`, Single-column for `cas-sc` / `review`
- **Bibliography:** `\bibliographystyle{elsarticle-num}` or `\bibliographystyle{cas-model2-names}`

## Float & Layout Rules
- **Two-Column Mode:** Single-column first for standard figures (`width=\linewidth`), `figure*` (`width=\textwidth`) only for wide multi-plots.
- **Float Placement:** `[!t]`, `[b]`, never use `\FloatBarrier` mid-section.
- **Tables:** `\begin{table}[!t]` with `\footnotesize` and `booktabs`.

## Author & Metadata Structure (cas-dc)
```latex
\title[mode = title]{Paper Title}

\author[1]{Author Name}[type=editor, auid=000, bioid=1]
\affiliation[1]{organization={Department, University},
                city={City},
                country={Country}}

\begin{abstract}
Abstract text verbatim from source.
\end{abstract}

\begin{keywords}
keyword1 \sep keyword2 \sep keyword3
\end{keywords}

\maketitle
```
