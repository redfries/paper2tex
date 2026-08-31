# ACM Publication Recipe (SIGCONF, TOG, TWEB, ACM Small)

## Profile
- **Document Classes:** `acmart`
- **Class Options:**
  - Conference: `\documentclass[sigconf]{acmart}`
  - Journal (Small): `\documentclass[acmsmall]{acmart}`
  - Journal (Large): `\documentclass[acmlarge]{acmart}`
  - Journal (TOG): `\documentclass[acmtog]{acmart}`
- **Compiler Engine:** `xelatex` or `pdflatex`
- **Column Mode:** Two-column for `sigconf` / `acmtog`, One-column for `acmsmall`
- **Bibliography:** `\bibliographystyle{ACM-Reference-Format}`, bib engine `bibtex`

## Float & Layout Rules
- **Single-Column First:** Default to single-column `\begin{figure}[!t]` with `width=\linewidth`.
- **Wide Figures:** `\begin{figure*}[!t]` with `width=\textwidth` only when content requires wide display.
- **Tables:** `\begin{table}[!t]` with `\footnotesize` and `booktabs`.
- **ACM Order Requirement:** `\begin{abstract}` and `\keywords{...}` MUST appear BEFORE `\maketitle`.

## Author & Metadata Structure
```latex
\title{Paper Title}

\author{Author Name}
\affiliation{%
  \institution{University or Institute}
  \city{City}
  \country{Country}
}
\email{author@domain.edu}

\begin{abstract}
Abstract text verbatim from source.
\end{abstract}

\keywords{keyword1, keyword2, keyword3}

\maketitle
```

## Special Constraints
- `acmart` already loads `amsmath`, `graphicx`, `hyperref`, and `color`. Do NOT reload them in the preamble.
- Do NOT use `\usepackage{cite}` — `acmart` uses `natbib` internally.
