# paper2tex — Production Layout & Typography Guidelines

These guidelines define the layout architecture, float mechanics, and sizing rules for converting `.docx` academic papers into publication-ready LaTeX documents across two-column and one-column conference/journal templates.

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

---

## 2. Figure Layout Decision Matrix

| Figure Geometry | Subfigures / Panels | Column Mode | Recommended Environment | Width Specification |
|---|---|---|---|---|
| Portrait (Aspect Ratio < 0.8) | Single image | Two-column | `\begin{figure}[!t]` | `\includegraphics[width=\linewidth]{...}` |
| Square / Modest Landscape (0.8 <= AR <= 2.2) | Single image | Two-column | `\begin{figure}[!t]` | `\includegraphics[width=\linewidth]{...}` |
| Ultra-wide Panorama (AR > 2.2) | Single image | Two-column | `\begin{figure*}[!t]` | `\includegraphics[width=\textwidth]{...}` |
| Tall / Narrow Panels (AR < 0.75) | 2–3 subfigures (a, b, c) | Two-column | `\begin{figure}[!t]` (Side-by-side) | `\includegraphics[width=0.31\linewidth]{...}\hfill...` |
| Moderate Landscape Panels | 2 subfigures | Two-column | `\begin{figure}[!t]` (Stacked) OR `\begin{figure*}[!t]` | Stacked: `width=\linewidth` / Wide: `width=0.48\textwidth` |
| Multi-panel Grid (4 panels) | 4 subfigures (a–d) | Two-column | `\begin{figure}[!t]` (2x2 Grid) | `width=0.48\linewidth` with `\hfill` and `\\[1ex]` |
| Any Standard Figure | 1 or more | One-column (LNCS, NeurIPS) | `\begin{figure}[!t]` | `width=0.85\textwidth` or `\linewidth` |

---

## 3. Multi-Panel Subfigure Formats

### A. Single-Column Side-by-Side (for 3 tall/portrait panels)
```latex
\begin{figure}[!t]
\centering
\includegraphics[width=0.31\linewidth]{fig1_a.png}\hfill
\includegraphics[width=0.31\linewidth]{fig1_b.png}\hfill
\includegraphics[width=0.31\linewidth]{fig1_c.png}
\caption{Comparative analysis across three scenarios: (a) Greenfield NPP, (b) Partial reuse, (c) Maximal reuse.}
\label{fig:scenarios}
\end{figure}
```

### B. Single-Column 2x2 Grid (for 4 panels)
```latex
\begin{figure}[!t]
\centering
\includegraphics[width=0.48\linewidth]{panel_a.png}\hfill
\includegraphics[width=0.48\linewidth]{panel_b.png}\\[1ex]
\includegraphics[width=0.48\linewidth]{panel_c.png}\hfill
\includegraphics[width=0.48\linewidth]{panel_d.png}
\caption{System performance metrics under varied conditions: (a) LCOE, (b) CAPEX, (c) Emissions, (d) Efficiency.}
\label{fig:grid_metrics}
\end{figure}
```

### C. Double-Column Wide Span (`figure*`)
```latex
\begin{figure*}[!t]
\centering
\includegraphics[width=0.31\textwidth]{fig1_a.png}\hfill
\includegraphics[width=0.31\textwidth]{fig1_b.png}\hfill
\includegraphics[width=0.31\textwidth]{fig1_c.png}
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

After compiling the document, the visual QA module and LLM reviewer must check:
- [ ] **No Premature Page Ejections**: No page has >95% blank space unless it is the final bibliography page.
- [ ] **No Float Clumping**: Figures are distributed near their first text mention rather than all clustered at the end.
- [ ] **No Overfull Columns**: Tables and figures do not spill into the column gutter or page margins.
- [ ] **Glyph Integrity**: No `?` or missing square box glyphs in special symbols (°C, µm, ±, ×).
- [ ] **Caption Placement**: Captions are clearly anchored immediately below figures and above/below tables according to template conventions.
