# paper2tex — Production Layout & Typography Guidelines

These guidelines define the layout architecture, float mechanics, transformation handling, and sizing rules for converting `.docx` academic papers into publication-ready LaTeX documents across two-column and one-column conference/journal templates.

---

## 1. Core Principles

1. **Seamless Reading Flow (Zero Artificial Float Gaps)**:
   - Floating figures and tables must flow naturally into the layout without breaking the continuity of prose.
   - **Never** inject `\FloatBarrier` (or hard page breaks) before normal sections or subsections.
   - LaTeX's internal float positioning algorithm balances text columns and fills space efficiently when given proper float specifiers (`[!t]`, `[t]`, `[b]`, `[htbp]`).

2. **Single-Column First ("One-Side First") Principle**:
   - In two-column formats (IEEE, ACM, Elsevier, ICML, CVPR), academic page budgets require compact, column-efficient placement.
   - All standard plots, charts, and tables default to a single column (`\begin{figure}[!t]`, `\begin{table}[!t]`).
   - High-resolution or physically large source images scale cleanly to `width=\columnwidth` (or `width=\linewidth`) without manual cropping.

3. **Template-Aware Subfigure Compatibility**:
   - **IEEEtran**: Standard `\usepackage{subcaption}` or `caption` package conflicts with `IEEEtran.cls`. Use `\usepackage[caption=false,font=footnotesize]{subfig}` and `\subfloat[...]{...}`.
   - **ACM / LNCS / Elsevier**: Use `\usepackage{subcaption}` with `\begin{subfigure}[b]{...}`.

---

## 2. Figure Layout Decision Matrix

| Figure Geometry | Subfigures / Panels | Caption / Description | Recommended Environment | Layout & Width Specification |
|---|---|---|---|---|
| Single Image (Any AR <= 2.2) | 1 image | Any | `\begin{figure}[!t]` | `\includegraphics[width=\linewidth]{...}` |
| Ultra-wide Panorama (AR > 2.2) | 1 image | Any | `\begin{figure*}[!t]` | `\includegraphics[width=\textwidth]{...}` |
| Landscape Panels (AR >= 0.85) | 2–3 subfigures (a, b, c) | Descriptive or standard | `\begin{figure}[!t]` (**Vertical Stack**) | `\subfloat` / `subfigure` stacked at `width=0.95\linewidth` with `\\[1ex]` |
| Landscape Panels (AR >= 0.85) | 3 subfigures (a, b, c) | Wide horizontal layout | `\begin{figure*}[!t]` (**Full-Width Span**) | `width=0.31\textwidth` with `\hfill` |
| Narrow / Portrait Panels (AR < 0.8) | 2–3 subfigures | Short labels | `\begin{figure}[!t]` (**Side-by-Side**) | `width=0.31\linewidth` with `\hfill` |
| Multi-panel Grid (4 panels) | 4 subfigures (a–d) | Any | `\begin{figure}[!t]` (**2x2 Grid**) | `width=0.48\linewidth` with `\hfill` and `\\[1ex]` |

---

## 3. Multi-Panel Subfigure Formats

### A. Single-Column Stacked (Recommended for 2–3 Landscape Diagrams in IEEEtran)
```latex
\begin{figure}[!t]
\centering
\subfloat[Case \#1: Greenfield nuclear power plant at a new location.\label{fig:case1}]{%
  \includegraphics[width=0.95\linewidth]{fig1_a.png}%
}\\[1ex]
\subfloat[Case \#2: Partial reuse of retiring coal plant infrastructure.\label{fig:case2}]{%
  \includegraphics[width=0.95\linewidth]{fig1_b.png}%
}\\[1ex]
\subfloat[Case \#3: Maximal reuse of steam cycle and heat sink.\label{fig:case3}]{%
  \includegraphics[width=0.95\linewidth]{fig1_c.png}%
}
\caption{Comparative analysis across three scenarios of techno-economic analysis.}
\label{fig:scenarios}
\end{figure}
```

### B. Single-Column Side-by-Side (for Tall/Portrait Panels in IEEEtran)
```latex
\begin{figure}[!t]
\centering
\subfloat[ROC curve.\label{fig:roc}]{%
  \includegraphics[width=0.31\linewidth]{fig1_a.png}%
}\hfill
\subfloat[PR curve.\label{fig:pr}]{%
  \includegraphics[width=0.31\linewidth]{fig1_b.png}%
}\hfill
\subfloat[Calibration.\label{fig:cal}]{%
  \includegraphics[width=0.31\linewidth]{fig1_c.png}%
}
\caption{Model evaluation curves across test splits.}
\label{fig:curves}
\end{figure}
```

### C. Double-Column Wide Span (`figure*`)
```latex
\begin{figure*}[!t]
\centering
\subfloat[Case \#1.\label{fig:wide_a}]{%
  \includegraphics[width=0.32\textwidth]{fig1_a.png}%
}\hfill
\subfloat[Case \#2.\label{fig:wide_b}]{%
  \includegraphics[width=0.32\textwidth]{fig1_b.png}%
}\hfill
\subfloat[Case \#3.\label{fig:wide_c}]{%
  \includegraphics[width=0.32\textwidth]{fig1_c.png}%
}
\caption{Full-width multi-panel architectural diagram.}
\label{fig:wide_architecture}
\end{figure*}
```

---

## 4. Table Layout & Sizing Rules

1. **Single-Column Default**:
   - Tables with up to 5 columns of concise numerical or text data must render in single-column `\begin{table}[!t]`.
   - Use `\footnotesize` or `\small` to ensure clean column spacing.
   - Use `\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}...}` to distribute columns evenly across the column width.

2. **When to use `\begin{table*}[!t]` (Double-Column)**:
   - Use only when the table has 6 or more columns, or contains long sentence-length descriptions in multiple cells.

3. **Professional `booktabs` Structure**:
```latex
\begin{table}[!t]
\centering
\footnotesize
\caption{Overnight Capital Cost (OCC) Breakdown for Case Studies}
\label{tab:occ_breakdown}
\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lcccc}
\toprule
\textbf{Component} & \textbf{Share (\%)} & \textbf{Cost (\$/kW)} & \textbf{Case 1} & \textbf{Case 2} \\
\midrule
Fuel Inventory & 7.0 & 420 & 0\% & 0\% \\
Land Rights & 0.3 & 18 & 100\% & 100\% \\
Reactor Equipment & 15.0 & 900 & 0\% & 0\% \\
Turbine Equipment & 18.0 & 1080 & 0\% & 90\% \\
Electrical Plant & 15.0 & 900 & 42\% & 42\% \\
\bottomrule
\end{tabular*}
\end{table}
```

---

## 5. Visual QA Checklist

After compiling the document, the visual QA module and reviewer must verify:
- [ ] **Figure Orientation**: All schematics, charts, and text inside figures are upright and legible (no sideways/rotated graphics).
- [ ] **No Subfigure Thumbnail Cramming**: Landscape subfigures are stacked or span across page width, not squished into micro-thumbnails.
- [ ] **Subcaption Integrity**: Sub-panel descriptions `(a)`, `(b)`, `(c)` are positioned under their respective panels with matching labels.
- [ ] **No Float Clumping**: Figures are distributed near their first text mention rather than all clustered at the end.
- [ ] **No Overfull Columns**: Tables and figures do not spill into the column gutter or page margins.
- [ ] **Glyph Integrity**: No `?` or missing square box glyphs in special symbols (°C, µm, ±, ×).
