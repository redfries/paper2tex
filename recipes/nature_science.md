# Nature, Science & Multidisciplinary Journals Recipe

## Profile Matrix
| Journal / Publisher | Document Class | Column Mode | Engine | Bib Style |
|---|---|---|---|---|
| **Nature** | `article` / `nature` | Two-column / One-column | `xelatex` | `naturemag` |
| **Science** | `article` | One-column (submission) | `pdflatex`/`xelatex` | `Science` |
| **MDPI** | `Definitions/mdpi` | Two-column | `xelatex` | `mdpi` |
| **PLOS** | `article` | One-column | `pdflatex` | `plos2015` |

## Float & Layout Rules
- **Nature / Science:** Figures are strictly budgeted by column width (89 mm single-column = `\columnwidth`, 183 mm double-column = `\textwidth`).
- **Captions:** Captions must have bold introductory sentence followed by detailed description.
- **Sectioning:** Nature uses unnumbered bold headings (`\section*{...}` or `\subsection*{...}`).

## Author & Metadata Structure (Nature Style)
```latex
\documentclass{article}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage[super,comma,sort&compress]{natbib}

\title{Paper Title}
\author{Author Name$^{1,2,*}$ \& Second Author$^{1}$}

\begin{document}
\maketitle

\noindent $^{1}$Department of Physics, University, City, Country.\\
$^{2}$Institute of Advanced Studies, City, Country.\\
$^{*}$e-mail: corresponding@university.edu

\begin{abstract}
Abstract verbatim from source.
\end{abstract}
```
