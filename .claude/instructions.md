When the user asks to convert a .docx paper to LaTeX or format a paper for a conference, read and follow the instructions in AGENTS.md (or SKILL.md for full detail).

Key points:
- Run scripts/extract.py to extract all content deterministically  
- Never rewrite the student's text — verbatim only
- Never regenerate math — use math_registry.json values
- Never invent citation keys — use references.bib keys
- Always run scripts/verify.py before delivering
