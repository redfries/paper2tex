# paper2tex — Examples & Usage Patterns

This guide demonstrates typical end-to-end conversion workflows with `paper2tex`.

---

## Example 1: Convert a Word Paper to IEEE Conference Format

### User Request
> "Convert my paper `C2N_draft.docx` to IEEE conference format."

### Workflow Execution
1. **Preflight**:
   ```bash
   python -m scripts.preflight
   ```
2. **Extraction & Preprocessing**:
   ```bash
   python -m scripts.extract "C2N_draft.docx" "work/c2n"
   ```
3. **Template Specification**:
   ```bash
   python -m scripts.template_spec "ieee-conference" "work/c2n"
   ```
4. **Deterministic Assembly**:
   ```bash
   python -m scripts.assemble "work/c2n"
   ```
5. **Compilation Loop**:
   ```bash
   python -m scripts.compile "work/c2n/main.tex"
   ```
6. **Verification & Visual QA**:
   ```bash
   python -m scripts.verify "work/c2n"
   python -m scripts.visual_qa "work/c2n/main.pdf" "work/c2n"
   ```

### Result
- `main.pdf` compiled cleanly with 0 float voids, compact single-column subfigures, and verified bibliography.

---

## Example 2: Convert to ACM SIGCONF Format

### User Request
> "Format this paper for ACM SIGCONF with the official template."

### Workflow Execution
```bash
# Extract
python -m scripts.extract "paper.docx" "work/acm_run"

# Apply ACM SIGCONF recipe
python -m scripts.template_spec "acm-sigconf" "work/acm_run"

# Assemble main.tex with ACM author blocks and metadata
python -m scripts.assemble "work/acm_run"

# Compile with tectonic/latexmk
python -m scripts.compile "work/acm_run/main.tex"
```

---

## Example 3: Subfigure Layout Adaptation

### Scenario
Source paper contains Figure 1 with three narrow vertical sub-panels:
- (a) Greenfield plant schematic (Aspect Ratio: 0.51)
- (b) Partial reuse schematic (Aspect Ratio: 0.51)
- (c) Maximal reuse schematic (Aspect Ratio: 0.53)

### Generated LaTeX (Single-Column Side-by-Side)
```latex
\begin{figure}[!t]
\centering
\includegraphics[width=0.31\linewidth]{fig1.png}\hfill
\includegraphics[width=0.31\linewidth]{fig2.png}\hfill
\includegraphics[width=0.31\linewidth]{fig3.png}
\caption{The three scenarios: (a) Greenfield NPP, (b) Partial reuse, (c) Maximal reuse.}
\label{fig:three_scenarios}
\end{figure}
```

### Advantage
Fits cleanly within a single column without pushing text to subsequent pages or leaving blank gaps.
