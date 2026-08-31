# Machine Learning Conferences Recipe (NeurIPS, ICML, ICLR, CVPR)

## Profile Matrix
| Conference | Document Class | Options / Package | Column Mode | Engine | Bib Style |
|---|---|---|---|---|---|
| **NeurIPS** | `article` / `neurips_2026` | `\usepackage{neurips_2026}` | One-column | `xelatex` | `plain` / `natbib` |
| **ICML** | `article` / `icml2026` | `\usepackage{icml2026}` | Two-column | `pdflatex`/`xelatex` | `icml2026` |
| **ICLR** | `article` / `iclr2026_conference` | `\usepackage{iclr2026_conference}` | One-column | `xelatex` | `iclr2026_conference` |
| **CVPR** | `article` / `cvpr` | `\usepackage{cvpr}` | Two-column | `pdflatex`/`xelatex` | `ieee_fullname` |

## Float & Layout Rules
- **NeurIPS / ICLR (One-column):**
  - Figures default to `\begin{figure}[!t]` with `width=0.85\textwidth` or `\linewidth`.
  - Multi-panel subfigures arranged side-by-side using `width=0.31\linewidth` (3 panels) or `width=0.48\linewidth` (2 panels).
  - Strict 9-page limit: tight spacing, no artificial white space.
- **ICML / CVPR (Two-column):**
  - Single-column first for standard figures (`width=\linewidth`).
  - Wide figures (`\begin{figure*}[!t]`) spanning 2 columns only when comparing multiple experimental curves side-by-side.

## Author & Metadata Structure (NeurIPS)
```latex
\documentclass{article}
\usepackage{neurips_2026}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}

\title{Paper Title}
\author{%
  First Author \\
  Department of Computer Science \\
  University \\
  \texttt{author1@domain.edu} \\
}

\begin{document}
\maketitle

\begin{abstract}
Abstract text verbatim from source.
\end{abstract}
```
