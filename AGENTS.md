# Agent Instructions for paper2tex

> **If you are an AI agent** (Claude Code, Cursor, OpenCode, Windsurf, Copilot, etc.),
> this file tells you how to use this tool. Read this first.

## TL;DR

You are converting a student's `.docx` paper to conference-formatted `.tex`.
You have a full deterministic extraction pipeline. Your **only creative job** is assembling the extracted content into the template structure. Everything else is scripted.

## Step-by-Step

### 1. Run preflight check

```bash
python scripts/preflight.py
```

If anything is missing, install it (the script prints exact install commands).

### 2. Run the main extraction pipeline

```bash
python scripts/extract.py <paper.docx> work/ [--figures-dir <path>]
```

This creates `work/manifest.json` and all registry files:
- `work/content.md` — full document text as Markdown
- `work/content.tex` — Pandoc's LaTeX output (reference only)
- `work/math_registry.json` — all equations as LaTeX
- `work/table_registry.json` — all tables as LaTeX `\begin{tabular}` blocks
- `work/figures/` — all figures, best quality available
- `work/references.bib` — bibliography in BibTeX format
- `work/manifest.json` — counts, cross-ref map, special chars, warnings

### 3. Analyze the template

```bash
python scripts/template_spec.py "<conference name or template.zip>" work/
```

This creates `work/template-spec.json` with document class, packages, author format, bib style.

### 4. Assemble main.tex (YOUR JOB)

Read `scripts/prompts/rules.md` for the 10 hard rules. The critical ones:

1. **Text is VERBATIM** from `content.md` — zero rewording
2. **Math is COPIED** from `math_registry.json` — never rewrite equations
3. **Tables are COPIED** from `table_registry.json` — never restructure
4. **Figures use** paths from the `work/figures/` directory
5. **Cross-references** use `\cref{label}` from `manifest.json` cross_ref_map
6. **Citations** use `\cite{key}` from `references.bib` keys
7. **Ambiguous content** → `% TODO(paper2tex): describe issue` comment

Build `work/main.tex` following the template spec. See `scripts/prompts/assemble_preamble.md` for preamble format and `scripts/prompts/assemble_section.md` for per-section assembly.

### 5. Compile

```bash
python scripts/compile.py work/main.tex
```

If errors remain after auto-fix, read the error, fix **markup only** (never content), recompile.

### 6. Verify

```bash
python scripts/verify.py work/main.tex
```

This produces `work/report.md`. If any **error-level** checks fail, fix and re-verify.

### 7. Package for delivery

```bash
# Copy final files to submission/
mkdir work/submission
copy work/main.tex work/submission/
copy work/references.bib work/submission/
xcopy work/figures work/submission/figures/ /E

# Create Overleaf zip
python scripts/overleaf_export.py work/submission/
```

Present `report.md` to the student.

## ABSOLUTE RULES (non-negotiable)

- **NEVER rewrite, improve, or edit the student's text.** Verbatim only.
- **NEVER regenerate math.** Use the registry values byte-for-byte.
- **NEVER invent citation keys or labels.** Registry keys only.
- **NEVER skip verification.** Run verify.py before delivering.
- **When in doubt**, add `% TODO(paper2tex): ...` comment. Don't guess.
