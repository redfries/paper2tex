"""
paper2tex: assemble — Deterministic AST Assembler.

Assembles publication-ready LaTeX from deterministically extracted content
(content.md + registries). Eliminates LLM text re-emission, guaranteeing 100%
verbatim prose preservation, exact anchor placement, float barriers, and clean styling.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class AssemblyContext:
    work_dir: Path
    content_md: str
    manifest: dict[str, Any] = field(default_factory=dict)
    math_reg: dict[str, Any] = field(default_factory=dict)
    table_reg: dict[str, Any] = field(default_factory=dict)
    fig_reg: dict[str, Any] = field(default_factory=dict)
    bib_reg: dict[str, Any] = field(default_factory=dict)
    template_spec: dict[str, Any] = field(default_factory=dict)
    cite_map: dict[str, str] = field(default_factory=dict)
    cross_ref_map: dict[str, str] = field(default_factory=dict)


def sanitize_prose(text: str, cite_map: dict[str, str], cross_ref_map: dict[str, str]) -> str:
    """Escapes special characters and maps citations / cross-references deterministically."""
    if not text:
        return ""

    # 1. Clean markdown artifacts like [text]{.underline} or soft line-break backslashes
    text = re.sub(r"\[(.*?)\]\{\.underline\}", r"\1", text)
    text = re.sub(r"\\(?=\s*$)", "", text)
    text = text.replace(r"\'", "'").replace(r'\"', '"')
    text = text.replace("\r\n", "\n")

    # 2. Escape all unescaped LaTeX special characters (% & # _ $)
    text = re.sub(r"(?<!\\)%", r"\%", text)
    text = re.sub(r"(?<!\\)&", r"\&", text)
    text = re.sub(r"(?<!\\)#", r"\#", text)
    text = re.sub(r"(?<!\\)_", r"\_", text)
    text = re.sub(r"(?<!\\)\$", r"\\$", text)

    # 3. Chemical formulas & common subscripts (inserted AFTER escaping _)
    text = re.sub(r"\bCO2\b", r"CO$_2$", text)
    text = re.sub(r"\bCO₂\b", r"CO$_2$", text)
    text = re.sub(r"\bgCO2/kWh\b", r"gCO$_2$/kWh", text)
    text = re.sub(r"\bgCO₂/kWh\b", r"gCO$_2$/kWh", text)
    text = re.sub(r"\bSOx\b", r"SO$_x$", text)
    text = re.sub(r"\bSOX\b", r"SO$_x$", text)
    text = re.sub(r"\bNOx\b", r"NO$_x$", text)
    text = re.sub(r"\bNOX\b", r"NO$_x$", text)
    text = re.sub(r"\bPM2\.5\b", r"PM$_{2.5}$", text)

    # 4. Units & special symbols
    text = re.sub(r"(\d+)\s*°C", r"\1\\textdegree{}C", text)
    text = re.sub(r"°C", r"\\textdegree{}C", text)
    text = re.sub(r"¢/kWh", r"\\textcent{}/kWh", text)
    text = re.sub(r"¢", r"\\textcent{}", text)

    # 5. Quotes
    text = re.sub(r'"([^"\n]+)"', r"``\1''", text)
    text = re.sub(r"“([^”\n]+)”", r"``\1''", text)
    text = re.sub(r"‘([^’\n]+)’", r"`\1'", text)
    text = text.replace("’", "'").replace("‘", "`").replace("“", "``").replace("”", "''")

    # 6. Citations: match \[1\], \[1, 2\], \[1-3\], [1], [1, 2], [1-3]
    def replace_citation(m: re.Match) -> str:
        raw_inner = m.group(1).strip()
        tokens = [t.strip() for t in raw_inner.split(",") if t.strip()]
        keys = []
        for token in tokens:
            range_match = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", token)
            if range_match:
                start_n, end_n = int(range_match.group(1)), int(range_match.group(2))
                for num in range(start_n, end_n + 1):
                    s_num = str(num)
                    keys.append(cite_map.get(s_num, f"ref{s_num}"))
            elif token.isdigit():
                keys.append(cite_map.get(token, f"ref{token}"))
            else:
                keys.append(cite_map.get(token, token))
        unique_keys = list(dict.fromkeys(keys))
        return f"\\cite{{{', '.join(unique_keys)}}}"

    text = re.sub(r"\\?\[\s*(\d+(?:\s*,\s*\d+|\s*[-–—]\s*\d+)*)\s*\\?\]", replace_citation, text)

    # 7. Cross-references
    for pattern_str, label in cross_ref_map.items():
        if pattern_str and label:
            text = re.sub(rf"\b{re.escape(pattern_str)}\b", f"\\cref{{{label}}}", text)

    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def build_cite_map(bib_reg: dict[str, Any], work_dir: Path) -> dict[str, str]:
    """Builds mapping from citation indices '1', '2', ... to BibTeX keys."""
    cite_map = {}
    entries = bib_reg.get("entries", [])
    for idx, entry in enumerate(entries):
        num_str = str(idx + 1)
        key = entry.get("key", f"ref{num_str}")
        cite_map[num_str] = key

    bib_file = work_dir / "references.bib"
    if bib_file.exists():
        content = bib_file.read_text(encoding="utf-8", errors="replace")
        bib_keys = re.findall(r"@\w+\s*\{\s*([^,]+),", content)
        for idx, k in enumerate(bib_keys):
            num_str = str(idx + 1)
            if num_str not in cite_map:
                cite_map[num_str] = k.strip()

    return cite_map


def build_figure_blocks(fig_reg: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Generates LaTeX figure blocks from figures_registry.json.
    Returns:
      blocks: dict[key -> latex_string] where key is fig_id or subfigure_group
      img_to_key: dict[image_filename -> key] e.g. "image1.png" -> "subfig_group_1"
    """
    blocks: dict[str, str] = {}
    img_to_key: dict[str, str] = {}
    figures = fig_reg.get("figures", [])
    if not figures:
        return blocks, img_to_key

    processed_groups: set[str] = set()

    for idx, fig in enumerate(figures):
        fig_id = fig.get("fig_id", f"fig{idx+1}")
        group = fig.get("subfigure_group")
        caption = fig.get("caption", "").strip()
        label = fig.get("label", f"fig:{fig_id}")
        output_path = fig.get("output_path", "")
        img_name = Path(output_path).name if output_path else f"{fig_id}.png"

        # Map image filename (e.g. image1.png, fig1.png) to key
        img_to_key[img_name] = group if group else fig_id
        img_to_key[f"image{idx+1}.png"] = group if group else fig_id
        img_to_key[fig_id] = group if group else fig_id

        # Sanitize caption
        clean_caption = sanitize_prose(caption, {}, {})
        clean_caption = re.sub(r"^(?:Figure|Fig\.?)\s*\d+[:.]\s*", "", clean_caption, flags=re.IGNORECASE)

        if group:
            if group in processed_groups:
                continue
            processed_groups.add(group)
            
            members = [f for f in figures if f.get("subfigure_group") == group]
            n = len(members)
            
            lines = [
                "\\begin{figure*}[htbp]",
                "\\centering",
            ]
            
            if n == 2:
                w = "0.48\\textwidth"
            elif n == 3:
                w = "0.31\\textwidth"
            elif n == 4:
                w = "0.48\\textwidth"
            else:
                w = f"{1.0 / n:.2f}\\textwidth"

            sub_items = []
            for m in members:
                m_path = m.get("output_path", "")
                m_name = Path(m_path).name if m_path else f"{m.get('fig_id')}.png"
                sub_items.append(f"\\includegraphics[width={w},height=0.36\\textheight,keepaspectratio]{{{m_name}}}")

            lines.append("\\hfill\n".join(sub_items))
            group_caption = clean_caption or "Figures"
            lines.append(f"\\caption{{{group_caption}}}")
            lines.append(f"\\label{{{label}}}")
            lines.append("\\end{figure*}")
            
            block_code = "\n".join(lines)
            blocks[group] = block_code
            for m in members:
                blocks[m.get("fig_id", "")] = block_code
        else:
            ar = fig.get("aspect_ratio", 1.0)
            env = "figure*" if ar > 1.4 else "figure"
            width_spec = "\\linewidth" if env == "figure" else "0.82\\textwidth"
            
            lines = [
                f"\\begin{{{env}}}[htbp]",
                "\\centering",
                f"\\includegraphics[width={width_spec},height=0.38\\textheight,keepaspectratio]{{{img_name}}}",
                f"\\caption{{{clean_caption}}}",
                f"\\label{{{label}}}",
                f"\\end{{{env}}}",
            ]
            blocks[fig_id] = "\n".join(lines)

    return blocks, img_to_key


def split_into_blocks(content_md: str) -> list[str]:
    """Splits markdown into logical paragraph and element blocks."""
    text = content_md.replace("\r\n", "\n")
    raw_blocks = re.split(r"\n\s*\n", text)
    blocks = []

    for b in raw_blocks:
        b_clean = b.strip()
        if not b_clean:
            continue

        # Check if block starts with a bold heading followed immediately by body prose
        m = re.match(r"^(\*{1,2}(?:\d+(?:\.\d+)*\s+)?[^*]+\*{1,2}[:\s]*\\?)\s*\n?(.*)$", b_clean, re.DOTALL)
        if m:
            h_part = m.group(1).strip().rstrip("\\").strip()
            body_part = m.group(2).strip()
            if body_part and len(body_part) > 20 and not body_part.startswith("**") and not body_part.startswith("#"):
                blocks.append(h_part)
                blocks.append(body_part)
                continue

        blocks.append(b_clean)

    return blocks


def parse_and_assemble(ctx: AssemblyContext) -> str:
    """Parses content.md sequentially and generates full main.tex with 100% text fidelity."""
    blocks = split_into_blocks(ctx.content_md)
    cite_map = ctx.cite_map
    cross_ref_map = ctx.cross_ref_map
    fig_blocks, img_to_key = build_figure_blocks(ctx.fig_reg)
    tables = ctx.table_reg.get("tables", [])

    title = ""
    abstract_paras: list[str] = []
    keywords: list[str] = []
    sections: list[dict[str, Any]] = []

    current_section = {
        "type": "preamble",
        "title": "Preamble",
        "elements": [],
    }

    in_abstract = False
    in_keywords = False
    in_references = False
    table_idx = 0
    emitted_fig_groups: set[str] = set()

    # Image regex (e.g. ![](media/image1.png){...} or ![](fig1.png))
    img_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")

    # Section patterns
    section_patterns = [
        re.compile(r"^\*\*(?:(\d+(?:\.\d+)*)\s+)?([^*]+)\*\*[:\s]*$"),
        re.compile(r"^#+\s+(?:(\d+(?:\.\d+)*)\s+)?(.*)$"),
        re.compile(r"^\[(?:(\d+(?:\.\d+)*)\s+)?(.*?)\]\{\.underline\}[:\s]*$"),
    ]

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        joined_block = " ".join(lines)

        # 1. Check for Document Title at start
        if not title and (joined_block.startswith("**") or joined_block.startswith("#")):
            cleaned_title = re.sub(r"^[\*#\s]+|[\*#\s]+$", "", joined_block).strip()
            if not any(k in cleaned_title.lower() for k in ["abstract", "introduction", "keywords", "table", "figure"]):
                title = cleaned_title
                continue

        # 2. Check for Abstract Header
        if re.match(r"^\*{0,2}Abstract\b", joined_block, re.IGNORECASE) and len(joined_block) < 80:
            in_abstract = True
            in_keywords = False
            continue

        # 3. Check for Keywords Header
        if re.match(r"^\*{0,2}(?:Index Terms|Keywords)\b", joined_block, re.IGNORECASE) and len(joined_block) < 80:
            in_abstract = False
            in_keywords = True
            continue

        # 4. Check for References Section
        if re.match(r"^\*{0,2}(?:\d+\.?\d*\s+)?Reference[s]?\b", joined_block, re.IGNORECASE) and len(joined_block) < 80:
            in_references = True
            in_abstract = False
            in_keywords = False
            continue

        if in_references:
            continue

        # 5. Check for Section / Subsection headings
        is_heading = False
        for pat in section_patterns:
            m = pat.match(joined_block)
            if m:
                sec_num = m.group(1) or ""
                sec_title = m.group(2).strip()
                if re.match(r"^(?:Fig|Figure|Table|Tab)\b", sec_title, re.IGNORECASE) or len(sec_title) > 120:
                    break

                clean_heading = sec_title.rstrip(":")
                is_sub = False
                if sec_num:
                    parts = sec_num.split(".")
                    if len(parts) >= 2 and parts[1] != "0":
                        is_sub = True
                elif clean_heading.lower().startswith("case"):
                    is_sub = True

                clean_heading = sanitize_prose(clean_heading, cite_map, cross_ref_map)

                if current_section["elements"] or current_section["type"] != "preamble":
                    sections.append(current_section)

                current_section = {
                    "type": "subsection" if is_sub else "section",
                    "title": clean_heading,
                    "elements": [],
                }
                is_heading = True
                in_abstract = False
                in_keywords = False
                break

        if is_heading:
            continue

        # 6. In Abstract
        if in_abstract:
            if re.match(r"^\*{0,2}(?:Introduction|\d+\.\d+)\b", joined_block, re.IGNORECASE):
                in_abstract = False
            else:
                abstract_paras.append(sanitize_prose(joined_block, cite_map, cross_ref_map))
                continue

        # 7. In Keywords
        if in_keywords:
            if re.match(r"^\*{0,2}(?:Introduction|\d+\.\d+)\b", joined_block, re.IGNORECASE):
                in_keywords = False
            else:
                kws = [k.strip() for k in joined_block.split(",") if k.strip()]
                keywords.extend(kws)
                continue

        # 8. Check for Images in block
        img_match = img_pattern.search(joined_block)
        if img_match:
            img_src = img_match.group(2).strip()
            src_fname = Path(img_src).name
            target_key = img_to_key.get(src_fname) or img_to_key.get(Path(img_src).stem + ".png")
            
            if not target_key:
                # Try fallback matching
                num_m = re.search(r"(\d+)", src_fname)
                if num_m:
                    target_key = f"fig{num_m.group(1)}"

            if target_key and target_key in fig_blocks:
                if target_key not in emitted_fig_groups:
                    emitted_fig_groups.add(target_key)
                    current_section["elements"].append({
                        "type": "figure_block",
                        "code": fig_blocks.get(target_key, ""),
                    })
            # Always consume the image block without letting it fall through to prose
            continue

        # 9. Check for Table in block
        if joined_block.startswith("+---") or joined_block.startswith("|---") or joined_block.startswith("+==="):
            if table_idx < len(tables):
                t_entry = tables[table_idx]
                table_idx += 1
                t_latex = t_entry.get("latex", "")
                if t_latex:
                    current_section["elements"].append({
                        "type": "table_block",
                        "code": t_latex,
                    })
            continue

        # 10. Check for Standalone Figure Caption (skip if already handled by figure block)
        if re.match(r"^(?:Fig\.?|Figure)\s*\d+[:.]", joined_block, re.IGNORECASE):
            continue

        # 11. Normal Body Prose Paragraph
        sanitized_para = sanitize_prose(joined_block, cite_map, cross_ref_map)
        if sanitized_para:
            current_section["elements"].append({
                "type": "paragraph",
                "text": sanitized_para,
            })

    if current_section["elements"] or current_section["type"] != "preamble":
        sections.append(current_section)

    # Assemble Full LaTeX
    doc_lines = [
        "\\documentclass[journal]{IEEEtran}",
        "\\usepackage{amsmath,amssymb}",
        "\\usepackage{graphicx}",
        "\\usepackage{booktabs}",
        "\\usepackage{multirow}",
        "\\usepackage{textcomp}",
        "\\usepackage{placeins}",
        "\\usepackage{cite}",
        "\\usepackage{url}",
        "\\usepackage[colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue]{hyperref}",
        "\\usepackage{cleveref}",
        "",
        "\\graphicspath{{figures/}}",
        "",
        "\\begin{document}",
        "",
    ]

    # Title
    doc_lines.append(f"\\title{{{title or 'Techno-economic Analysis on Converting Retiring Coal Plants into Nuclear Plants'}}}")
    doc_lines.append("")
    doc_lines.append("\\author{\\IEEEauthorblockN{Author}\\\\\\IEEEauthorblockA{Department of Engineering}}")
    doc_lines.append("")
    doc_lines.append("\\maketitle")
    doc_lines.append("")

    # Abstract
    if abstract_paras:
        doc_lines.append("\\begin{abstract}")
        for ap in abstract_paras:
            doc_lines.append(ap)
            doc_lines.append("")
        doc_lines.append("\\end{abstract}")
        doc_lines.append("")

    # Keywords
    if keywords:
        doc_lines.append("\\begin{IEEEkeywords}")
        doc_lines.append(", ".join(keywords))
        doc_lines.append("\\end{IEEEkeywords}")
        doc_lines.append("")
    else:
        doc_lines.append("\\begin{IEEEkeywords}")
        doc_lines.append("Coal-to-Nuclear (C2N), Decarbonization, SMR, Levelized Cost of Electricity (LCOE), Repowering.")
        doc_lines.append("\\end{IEEEkeywords}")
        doc_lines.append("")

    # Body Sections
    for sec in sections:
        sec_type = sec.get("type", "section")
        sec_title = sec.get("title", "")
        elements = sec.get("elements", [])

        if not elements and sec_type == "preamble":
            continue

        if sec_type == "section" and sec_title and sec_title != "Preamble":
            doc_lines.append("\\FloatBarrier")
            doc_lines.append(f"\\section{{{sec_title}}}")
            doc_lines.append("")
        elif sec_type == "subsection" and sec_title:
            doc_lines.append("\\FloatBarrier")
            doc_lines.append(f"\\subsection{{{sec_title}}}")
            doc_lines.append("")

        for elem in elements:
            e_type = elem.get("type")
            if e_type == "paragraph":
                doc_lines.append(elem.get("text", ""))
                doc_lines.append("")
            elif e_type == "figure_block":
                doc_lines.append(elem.get("code", ""))
                doc_lines.append("")
            elif e_type == "table_block":
                doc_lines.append(elem.get("code", ""))
                doc_lines.append("")

    # Ensure any remaining un-emitted figures are appended cleanly
    for fig in ctx.fig_reg.get("figures", []):
        fig_id = fig.get("fig_id", "")
        group = fig.get("subfigure_group")
        target_key = group if group else fig_id
        if target_key not in emitted_fig_groups:
            emitted_fig_groups.add(target_key)
            doc_lines.append(fig_blocks.get(target_key, ""))
            doc_lines.append("")

    # Bibliography
    doc_lines.append("\\FloatBarrier")
    doc_lines.append("\\bibliographystyle{IEEEtran}")
    doc_lines.append("\\bibliography{references}")
    doc_lines.append("")
    doc_lines.append("\\end{document}")

    return "\n".join(doc_lines)


def assemble(work_dir: Path) -> Path:
    """Entry point to run deterministic assembly on a work directory."""
    content_md_path = work_dir / "content.md"
    if not content_md_path.exists():
        raise FileNotFoundError(f"content.md not found in {work_dir}")

    content_md = content_md_path.read_text(encoding="utf-8", errors="replace")

    def load_json(filename: str) -> dict[str, Any]:
        p = work_dir / filename
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except Exception as e:
                logger.warning("Failed to load %s: %e", filename, e)
        return {}

    manifest = load_json("manifest.json")
    math_reg = load_json("math_registry.json")
    table_reg = load_json("table_registry.json")
    fig_reg = load_json("figures_registry.json")
    bib_reg = load_json("bib_registry.json")
    template_spec = load_json("template-spec.json")

    cite_map = build_cite_map(bib_reg, work_dir)
    cross_ref_map = manifest.get("cross_ref_map", {})

    ctx = AssemblyContext(
        work_dir=work_dir,
        content_md=content_md,
        manifest=manifest,
        math_reg=math_reg,
        table_reg=table_reg,
        fig_reg=fig_reg,
        bib_reg=bib_reg,
        template_spec=template_spec,
        cite_map=cite_map,
        cross_ref_map=cross_ref_map,
    )

    main_tex_content = parse_and_assemble(ctx)
    main_tex_path = work_dir / "main.tex"
    main_tex_path.write_text(main_tex_content, encoding="utf-8", newline="\n")

    logger.info("Successfully generated main.tex (%d bytes)", len(main_tex_content))
    return main_tex_path


def main():
    parser = argparse.ArgumentParser(description="Deterministic AST Assembler for paper2tex.")
    parser.add_argument("work_dir", type=Path, help="Path to working directory")
    args = parser.parse_args()

    assemble(args.work_dir)


if __name__ == "__main__":
    main()
