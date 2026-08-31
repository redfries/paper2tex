"""
paper2tex: verify_text_fidelity — Bidirectional Text Fidelity & Hallucination Verifier.

Compares extracted markdown content (content.md) against generated LaTeX (main.tex)
at the AST/paragraph level to detect:
1. Dropped paragraphs (Source -> Target missing)
2. Silent rewrites / paraphrasing (Source -> Target similarity between 60% and 95%)
3. Hallucinated text (Target -> Source missing)
4. Caption alterations (captions not matching registry verbatim)
"""

from __future__ import annotations

import argparse
import difflib
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
class ParagraphMatch:
    source_index: int
    source_preview: str
    target_index: int | None
    target_preview: str | None
    similarity: float
    status: str  # "MATCH", "REWRITE", "DROPPED", "HALLUCINATION"
    diff: str = ""


@dataclass
class CaptionCheck:
    element_id: str  # e.g., "fig1", "tab1"
    expected_caption: str
    found_caption: str | None
    passed: bool
    details: str = ""


@dataclass
class FidelityResult:
    total_source_paras: int = 0
    matched_paras: int = 0
    dropped_paras: list[ParagraphMatch] = field(default_factory=list)
    rewritten_paras: list[ParagraphMatch] = field(default_factory=list)
    hallucinated_paras: list[ParagraphMatch] = field(default_factory=list)
    caption_checks: list[CaptionCheck] = field(default_factory=list)
    fidelity_score: float = 100.0  # 0.0 to 100.0
    passed: bool = True

    def to_report_md(self) -> str:
        lines = [
            "### Text Fidelity & Hallucination Analysis",
            "",
            f"- **Overall Text Fidelity Score:** `{self.fidelity_score:.1f}%`",
            f"- **Source Paragraphs Analyzed:** {self.total_source_paras}",
            f"- **Exact / Verbatim Matches:** {self.matched_paras}",
            f"- **Dropped Paragraphs:** {len(self.dropped_paras)}",
            f"- **Rewritten / Paraphrased Paragraphs:** {len(self.rewritten_paras)}",
            f"- **Hallucinated Additions:** {len(self.hallucinated_paras)}",
            "",
        ]

        if self.caption_checks:
            lines.append("#### Caption Verification")
            for c in self.caption_checks:
                icon = "✅" if c.passed else "❌"
                lines.append(f"- {icon} **{c.element_id}**: {c.details or 'Verbatim match'}")
            lines.append("")

        if self.dropped_paras:
            lines.append("#### ❌ Dropped Paragraphs (Source -> Missing in TeX)")
            for d in self.dropped_paras:
                lines.append(f"- **Source Para #{d.source_index + 1}:**")
                lines.append(f"  > {d.source_preview}")
            lines.append("")

        if self.rewritten_paras:
            lines.append("#### ⚠️ Rewritten / Paraphrased Paragraphs (Similarity 60%-95%)")
            for r in self.rewritten_paras:
                lines.append(f"- **Source Para #{r.source_index + 1}** (Similarity: `{r.similarity * 100:.1f}%`):")
                lines.append(f"  - *Source:* {r.source_preview}")
                lines.append(f"  - *Output:* {r.target_preview}")
            lines.append("")

        if self.hallucinated_paras:
            lines.append("#### ❌ Hallucinated Text (Found in TeX, not in Source)")
            for h in self.hallucinated_paras:
                lines.append(f"- **TeX Para #{h.target_index}:**")
                lines.append(f"  > {h.target_preview}")
            lines.append("")

        return "\n".join(lines)


def normalize_text_for_comparison(text: str) -> str:
    """Normalizes prose for comparison across markdown and LaTeX escaping."""
    if not text:
        return ""

    # Unescape common LaTeX commands
    t = text
    t = t.replace(r"\$", "$").replace(r"\%", "%").replace(r"\&", "&").replace(r"\#", "#").replace(r"\_", "_")
    t = t.replace(r"\textdegree{}C", "°C").replace(r"\textdegree", "°")
    t = t.replace(r"\textcent{}/kWh", "¢/kWh").replace(r"\textcent{}", "¢")
    t = re.sub(r"CO\$_2\$", "CO2", t)
    t = re.sub(r"SO\$_x\$", "SOx", t)
    t = re.sub(r"NO\$_x\$", "NOx", t)
    t = re.sub(r"PM\$\_\{2\.5\}\$", "PM2.5", t)

    # Normalize unicode subscripts
    subscripts = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    t = t.translate(subscripts)

    # Strip citations like \cite{...} or [1], [1, 2], \[1\], \[1-3\]
    t = re.sub(r"\\cite\{[^}]*\}", "", t)
    t = re.sub(r"\\?\[\s*\d+(?:\s*,\s*\d+|\s*[-–—]\s*\d+)*\s*\\?\]", "", t)
    t = re.sub(r"\\cref\{[^}]*\}", "", t)

    # Strip markdown formatting
    t = re.sub(r"\[(.*?)\]\{\.underline\}", r"\1", t)
    t = re.sub(r"[*_~`]", "", t)

    # Strip quotes
    t = t.replace("``", '"').replace("''", '"').replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    # Remove commas in numbers (e.g. 3,000 -> 3000)
    t = re.sub(r"(\d),(\d)", r"\1\2", t)

    # Lowercase & collapse whitespace
    t = re.sub(r"[^\w\s]", " ", t)  # Replace punctuation with spaces
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def extract_paragraphs_from_md(md_path: Path) -> list[str]:
    """Extracts body prose paragraphs from content.md."""
    if not md_path.exists():
        return []

    content = md_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    raw_blocks = re.split(r"\n\s*\n", content)
    paragraphs: list[str] = []

    in_references = False

    for block in raw_blocks:
        b_s = block.strip()
        if not b_s:
            continue

        # Check references section
        if re.match(r"^\*{0,2}(?:\d+\.?\d*\s+)?Reference[s]?\b", b_s, re.IGNORECASE) and len(b_s) < 80:
            in_references = True
            continue
        if in_references:
            continue

        # Check table
        if b_s.startswith("+---") or b_s.startswith("|---") or b_s.startswith("+==="):
            continue

        # Check if block starts with a bold heading followed immediately by body prose
        m = re.match(r"^(\*{1,2}(?:\d+(?:\.\d+)*\s+)?[^*]+\*{1,2}[:\s]*\\?)\s*\n?(.*)$", b_s, re.DOTALL)
        if m:
            body_part = m.group(2).strip()
            if body_part and len(body_part) > 25 and not body_part.startswith("**") and not body_part.startswith("#"):
                lines = [l.strip() for l in body_part.split("\n") if l.strip()]
                para = " ".join(lines)
                if len(para) >= 25:
                    paragraphs.append(para)
            continue

        # Check headings or titles
        if b_s.startswith("#") or (b_s.startswith("**") and b_s.endswith("**") and len(b_s) < 120):
            continue
        if re.match(r"^\[.*?\]\{\.underline\}[:\s]*$", b_s):
            continue

        # Check image markup or standalone caption
        if b_s.startswith("![") or b_s.startswith("![](") or re.match(r"^(?:Fig\.?|Figure)\s*\d+[:.]", b_s, re.IGNORECASE):
            continue

        lines = [l.strip() for l in b_s.split("\n") if l.strip()]
        para = " ".join(lines)

        # Skip if very short text (e.g. labels, single words)
        if len(para) < 25:
            continue

        paragraphs.append(para)

    return paragraphs


def extract_paragraphs_from_tex(tex_path: Path) -> list[str]:
    """Extracts body prose paragraphs from main.tex."""
    if not tex_path.exists():
        return []

    content = tex_path.read_text(encoding="utf-8", errors="replace")
    
    # Strip environments like table, figure, tabular, abstract, keywords, thebibliography
    # Keep abstract text
    abstract_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.DOTALL)
    abstract_text = abstract_match.group(1).strip() if abstract_match else ""

    # Remove preambles before \begin{document}
    doc_body_match = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", content, re.DOTALL)
    body = doc_body_match.group(1) if doc_body_match else content

    # Remove figures
    body = re.sub(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", "", body, flags=re.DOTALL)
    # Remove tables
    body = re.sub(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", "", body, flags=re.DOTALL)
    # Remove display math
    body = re.sub(r"\\begin\{(?:equation|align|gather|multline)\*?\}.*?\\end\{(?:equation|align|gather|multline)\*?\}", "", body, flags=re.DOTALL)
    body = re.sub(r"\\\[.*?\\\]", "", body, flags=re.DOTALL)
    # Remove author, title, maketitle, bibliographystyle, bibliography, FloatBarrier
    body = re.sub(r"\\(?:title|author|maketitle|FloatBarrier|bibliographystyle|bibliography)\*?\{[^}]*\}", "", body)
    body = re.sub(r"\\(?:maketitle|FloatBarrier)", "", body)
    # Remove \section, \subsection, \subsubsection
    body = re.sub(r"\\(?:sub)*section\*?\{[^}]*\}", "", body)
    # Remove \begin{IEEEkeywords}...\end{IEEEkeywords} and \begin{tabular}...\end{tabular}
    body = re.sub(r"\\begin\{IEEEkeywords\}.*?\\end\{IEEEkeywords\}", "", body, flags=re.DOTALL)
    body = re.sub(r"\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}", "", body, flags=re.DOTALL)
    # Remove \begin{abstract}, \end{abstract}
    body = re.sub(r"\\begin\{abstract\}", "", body)
    body = re.sub(r"\\end\{abstract\}", "", body)

    raw_blocks = body.split("\n\n")
    paragraphs: list[str] = []

    for block in raw_blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip() and not l.strip().startswith("%")]
        para = " ".join(lines).strip()
        if not para or len(para) < 25:
            continue
        # Skip if pure macro or environment leftover
        if para.startswith("\\") and len(para.split()) < 3:
            continue
        paragraphs.append(para)

    return paragraphs


def verify_text_fidelity(
    md_path: Path,
    tex_path: Path,
    fig_reg_path: Path | None = None,
    table_reg_path: Path | None = None,
    min_similarity: float = 0.95,
) -> FidelityResult:
    """Performs bidirectional text fidelity and caption verification."""
    result = FidelityResult()

    source_paras = extract_paragraphs_from_md(md_path)
    target_paras = extract_paragraphs_from_tex(tex_path)

    result.total_source_paras = len(source_paras)

    norm_source = [normalize_text_for_comparison(p) for p in source_paras]
    norm_target = [normalize_text_for_comparison(p) for p in target_paras]

    matched_source_indices = set()
    matched_target_indices = set()

    # 1. Source -> Target (Check for Dropped & Rewritten Paragraphs)
    for s_idx, s_norm in enumerate(norm_source):
        if not s_norm:
            continue

        best_sim = 0.0
        best_t_idx = None

        for t_idx, t_norm in enumerate(norm_target):
            if not t_norm:
                continue

            # Exact match or substring inclusion
            if s_norm == t_norm or (len(s_norm) > 40 and s_norm in t_norm) or (len(t_norm) > 40 and t_norm in s_norm):
                sim = 1.0
            else:
                sim = difflib.SequenceMatcher(None, s_norm, t_norm).ratio()

            if sim > best_sim:
                best_sim = sim
                best_t_idx = t_idx

        s_raw = source_paras[s_idx]
        t_raw = target_paras[best_t_idx] if best_t_idx is not None else None

        if best_sim >= min_similarity:
            result.matched_paras += 1
            matched_source_indices.add(s_idx)
            if best_t_idx is not None:
                matched_target_indices.add(best_t_idx)
        elif best_sim >= 0.60:
            result.rewritten_paras.append(ParagraphMatch(
                source_index=s_idx,
                source_preview=s_raw[:120] + ("..." if len(s_raw) > 120 else ""),
                target_index=best_t_idx,
                target_preview=(t_raw[:120] + ("..." if len(t_raw) > 120 else "")) if t_raw else "",
                similarity=best_sim,
                status="REWRITE",
            ))
            matched_source_indices.add(s_idx)
            if best_t_idx is not None:
                matched_target_indices.add(best_t_idx)
        else:
            result.dropped_paras.append(ParagraphMatch(
                source_index=s_idx,
                source_preview=s_raw[:120] + ("..." if len(s_raw) > 120 else ""),
                target_index=None,
                target_preview=None,
                similarity=best_sim,
                status="DROPPED",
            ))

    # 2. Target -> Source (Check for Hallucinated Additions)
    for t_idx, t_norm in enumerate(norm_target):
        if t_idx in matched_target_indices:
            continue
        if len(t_norm) < 60:  # Skip trivial snippets
            continue

        best_sim = 0.0
        for s_norm in norm_source:
            if not s_norm:
                continue
            sim = difflib.SequenceMatcher(None, t_norm, s_norm).ratio()
            if sim > best_sim:
                best_sim = sim

        if best_sim < 0.60:
            t_raw = target_paras[t_idx]
            result.hallucinated_paras.append(ParagraphMatch(
                source_index=-1,
                source_preview="",
                target_index=t_idx + 1,
                target_preview=t_raw[:120] + ("..." if len(t_raw) > 120 else ""),
                similarity=best_sim,
                status="HALLUCINATION",
            ))

    # 3. Caption Verification
    if fig_reg_path and fig_reg_path.exists():
        tex_content = tex_path.read_text(encoding="utf-8", errors="replace") if tex_path.exists() else ""
        norm_tex = normalize_text_for_comparison(tex_content)
        fig_reg = json.loads(fig_reg_path.read_text(encoding="utf-8", errors="replace"))

        for fig in fig_reg.get("figures", []):
            fig_id = fig.get("fig_id", "")
            raw_caption = fig.get("caption", "").strip()
            if not raw_caption:
                continue
            
            # Clean caption
            clean_cap = re.sub(r"^(?:Figure|Fig\.?)\s*\d+[:.]\s*", "", raw_caption, flags=re.IGNORECASE)
            norm_cap = normalize_text_for_comparison(clean_cap)

            passed = (norm_cap in norm_tex) or (difflib.SequenceMatcher(None, norm_cap, norm_tex).find_longest_match(0, len(norm_cap), 0, len(norm_tex)).size > len(norm_cap) * 0.85)

            result.caption_checks.append(CaptionCheck(
                element_id=fig_id,
                expected_caption=raw_caption[:80],
                found_caption=clean_cap[:80] if passed else "MISMATCH / MISSING",
                passed=passed,
                details="" if passed else f"Caption for {fig_id} was modified or missing in .tex",
            ))

    # Compute overall score
    if result.total_source_paras > 0:
        result.fidelity_score = (result.matched_paras / result.total_source_paras) * 100.0
    else:
        result.fidelity_score = 100.0

    # Determine overall pass
    failed_captions = sum(1 for c in result.caption_checks if not c.passed)
    result.passed = (
        len(result.dropped_paras) == 0 and
        len(result.hallucinated_paras) == 0 and
        len(result.rewritten_paras) == 0 and
        failed_captions == 0 and
        result.fidelity_score >= 95.0
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Bidirectional Text Fidelity Verifier for paper2tex.")
    parser.add_argument("content_md", type=Path, help="Path to content.md")
    parser.add_argument("main_tex", type=Path, help="Path to main.tex")
    parser.add_argument("--fig-reg", type=Path, help="Path to figures_registry.json")
    parser.add_argument("--table-reg", type=Path, help="Path to table_registry.json")
    args = parser.parse_args()

    result = verify_text_fidelity(args.content_md, args.main_tex, args.fig_reg, args.table_reg)
    print(result.to_report_md())
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
