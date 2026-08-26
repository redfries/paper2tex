# Preamble and Front Matter Generation

Your task is to generate the complete preamble and front matter for a LaTeX document, up to and including the `\maketitle` command. You will use the provided template specifications, detected packages, and extracted author information.

## Inputs

### Template Specification
**Document Class & Options:**
```json
{{template_spec}}
```

### Detected Packages
These packages are required based on the document's content:
```json
{{detected_packages}}
```

### Paper Details
**Title:** {{title}}
**Bibliography Style:** {{bib_style}}

**Abstract:**
```text
{{abstract_text}}
```

**Keywords:**
```text
{{keywords}}
```

**Raw Author Information:**
```text
{{author_info}}
```

## Generation Rules

1. **Document Class:** Start with the correct `\documentclass[options]{class}` as specified in the `template_spec`.
2. **Packages:** Include all required packages from `template_spec` and `detected_packages`.
3. **Package Order:** Pay strict attention to package loading order:
   - `amsmath`, `amssymb`, `amsfonts` should generally be loaded early.
   - `graphicx` is required for figures.
   - `hyperref` MUST be the second-to-last package loaded.
   - `cleveref` MUST be the absolute last package loaded (after `hyperref`).
4. **Author Block:** Format the author block according to the specific rules of the document class. Parse the `author_info` and map it to the correct LaTeX commands.
5. **Front Matter:** Include the `\title`, `\author` (and affiliations), `\begin{document}`, `\maketitle`, abstract environment, and keywords environment as dictated by the class.

## Examples of Author Blocks by Template

### IEEEtran Example
```latex
\author{\IEEEauthorblockN{1\textsuperscript{st} Given Name Surname}
\IEEEauthorblockA{\textit{dept. name of organization (of Aff.)} \\
\textit{name of organization (of Aff.)}\\
City, Country \\
email address or ORCID}
\and
\IEEEauthorblockN{2\textsuperscript{nd} Given Name Surname}
\IEEEauthorblockA{\textit{dept. name of organization (of Aff.)} \\
\textit{name of organization (of Aff.)}\\
City, Country \\
email address or ORCID}}
```

### ACM (acmart) Example
```latex
\author{Ben Trovato}
\email{trovato@corporation.com}
\orcid{1234-5678-9012}
\affiliation{%
  \institution{Institute for Clarity in Documentation}
  \streetaddress{P.O. Box 1212}
  \city{Dublin}
  \state{Ohio}
  \country{USA}
  \postcode{43017-6221}
}
```

### LNCS (llncs) Example
```latex
\author{First Author\inst{1}\orcidID{0000-1111-2222-3333} \and
Second Author\inst{2,3}\orcidID{1111-2222-3333-4444} \and
Third Author\inst{3}\orcidID{2222--3333-4444-5555}}
\authorrunning{F. Author et al.}
\institute{Princeton University, Princeton NJ 08544, USA \and
Springer Heidelberg, Tiergartenstr. 17, 69121 Heidelberg, Germany
\email{lncs@springer.com}\\
\url{http://www.springer.com/gp/computer-science/lncs} \and
ABC Institute, Rupert-Karls-University Heidelberg, Heidelberg, Germany\\
\email{\{abc,lncs\}@uni-heidelberg.de}}
```

## Expected Output
Generate ONLY the raw LaTeX code starting from `\documentclass` and ending exactly after `\maketitle` (and abstract/keywords if they are placed after `\maketitle` in this specific class). Do not output markdown code blocks unless requested.
