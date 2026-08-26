# paper2tex Assembly Rules — HARD CONSTRAINTS

You are assembling a LaTeX document from deterministically extracted content.
You are a FORMATTER, not a WRITER. The student's text is sacred.

## The 10 Commandments

1. **VERBATIM TEXT.** Every sentence in the output must appear exactly as written in `content.md`. Zero rewording. No synonyms. No "improvements." No added transitions. No removed sentences.

2. **VERBATIM MATH.** Every equation in the output must be byte-for-byte identical to what's in `math_registry.json`. The OMML→MathML→LaTeX pipeline already produced correct LaTeX. Never "simplify" or "clean up" a formula.

3. **VERBATIM TABLES.** Every table in the output must use the exact LaTeX code from `table_registry.json`. The table extractor already handled merged cells and formatting.

4. **VERBATIM CAPTIONS.** Figure and table captions must be exactly as in the registries. Do not rephrase.

5. **REGISTRY KEYS ONLY.** Every `\label{}`, `\ref{}`, `\cref{}`, `\cite{}` key must come from the registries. Never invent a key. If you need a key that doesn't exist, add a `% TODO(paper2tex): missing key for ...` comment.

6. **NO CONTENT CHANGES.** Do not fix typos, improve grammar, reorganize paragraphs, add transitions, remove redundancy, or change the student's word choices. Even if you see an obvious error.

7. **TODO FOR AMBIGUITY.** If something is unclear (a text box, a merged table, an algorithm, an unmatched figure), insert `% TODO(paper2tex): describe the issue` — never guess silently.

8. **TEMPLATE COMPLIANCE.** Use only the document class, packages, and author commands specified in `template-spec.json`. Do not add unauthorized packages or override template settings.

9. **CHUNKING.** For documents longer than ~8 pages, process one section at a time. Share `registry.json` across chunks to maintain label/cite key consistency.

10. **VERIFY YOUR OUTPUT.** After assembly, mentally check:
    - Section count matches source
    - Every figure has a caption and label
    - Every table has a caption and label
    - Every equation number has a label
    - Every cross-reference uses `\cref{}`, not hardcoded text
    - Every citation uses `\cite{}` with a registry key
