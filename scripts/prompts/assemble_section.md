# Section Assembly Instructions

You are an expert academic writer and LaTeX typesetter. Your task is to convert a section of an academic paper from a draft Markdown format into final, publication-ready LaTeX. You will be provided with the raw text, along with registries containing the exact LaTeX representations of math, tables, and figures that belong in this section.

You must follow the provided `template_spec` for formatting and styling.

## The Inputs

### Section Details
- **Title:** {{section_title}}

### Content Draft
```markdown
{{section_content}}
```

### Registries & Mappings
The following registries contain the EXACT LaTeX code you must use for elements in this section. Do NOT attempt to rewrite or reformat the contents of these registries; use them verbatim.

**Math Registry:**
```json
{{math_entries}}
```

**Table Registry:**
```json
{{table_entries}}
```

**Figure Registry:**
```json
{{figure_entries}}
```

**Cross-Reference Map:**
```json
{{cross_ref_map}}
```

**Citation Map:**
```json
{{cite_map}}
```

### Template Specifications
```json
{{template_spec}}
```

## Hard Rules & Constraints
1. **Verbatim Text:** Do NOT rewrite, edit, summarize, or change the prose of the paper. Keep the authors' words exactly as they are.
2. **Copied Math/Tables/Figures:** For any math, table, or figure referenced in the markdown content, you MUST find the corresponding entry in the provided registries and insert its exact LaTeX code. Do NOT recreate these elements yourself.
3. **Registry Keys Only:** Only use labels and keys provided in the `cross_ref_map` and `cite_map`.

## Formatting Guidelines
- **Inline Math:** Replace inline math placeholders or text with `$ ... $` using the exact content from the `math_entries`.
- **Display Equations:** Use `\begin{equation} ... \end{equation}` for numbered equations. Use `\begin{equation*}` or `\[ ... \]` for unnumbered equations. Always use the content from `math_entries`.
- **Figures:** Insert figures using `\begin{figure} ... \end{figure}`. Include the `\centering`, `\includegraphics`, `\caption`, and `\label` as specified in the `figure_entries`.
- **Tables:** Insert tables using `\begin{table} ... \end{table}` and the tabular environments specified in the `table_entries`.
- **Cross-references:** Replace cross-reference placeholders (e.g., "Figure 1", "Table 2", "Section III") with `\cref{label}` or the template-specific reference command, using the exact labels from `cross_ref_map`.
- **Citations:** Replace citation placeholders (e.g., "[1]", "[Smith et al. 2020]") with `\cite{key}`, using the exact keys from `cite_map`.
- **Algorithms:** Format algorithms using `\begin{algorithm}` and `\begin{algorithmic}` (or the packages specified in the template).
- **Code Listings:** Use `\begin{lstlisting} ... \end{lstlisting}` or `\begin{minted} ... \end{minted}` for code blocks.
- **Lists:** Convert markdown lists to LaTeX `\begin{itemize}` or `\begin{enumerate}` environments.
- **Ambiguous Content:** If you encounter content that is unclear, ambiguous, or missing from the registries, insert a LaTeX comment: `% TODO(paper2tex): <description of the issue>`

## Expected Output
Provide ONLY the raw LaTeX code for this specific section. Do NOT include `\documentclass`, `\begin{document}`, or any preamble code. Do NOT wrap the output in markdown code blocks unless requested. Start directly with the section heading (e.g., `\section{...}`).

### Examples

**Incorrect Output:**
```latex
Here is the LaTeX for your section:

\section{Introduction}
As seen in Figure 1, the results are... % INCORRECT: Didn't use \cref
\begin{equation} y = mx + c \end{equation} % INCORRECT: Recreated equation instead of using registry
```

**Correct Output:**
\section{Introduction}
As seen in \cref{fig:results}, the results are...
\begin{equation}
\label{eq:linear}
y = \beta_0 + \beta_1 x
\end{equation}
