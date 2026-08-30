import os
import sys
import json
import zipfile
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from lxml import etree

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

logger = logging.getLogger(__name__)

@dataclass
class MathEquation:
    position: int
    latex: str
    is_display: bool
    eq_number: Optional[str]
    original_omml: str

@dataclass
class MathRegistry:
    equations: List[MathEquation] = field(default_factory=list)
    inline_count: int = 0
    display_count: int = 0

    def to_dict(self) -> dict:
        return {
            "inline_count": self.inline_count,
            "display_count": self.display_count,
            "total_count": self.inline_count + self.display_count,
            "equations": [
                {
                    "position": eq.position,
                    "latex": eq.latex,
                    "is_display": eq.is_display,
                    "eq_number": eq.eq_number,
                    "original_omml": eq.original_omml,
                }
                for eq in self.equations
            ],
        }

UNICODE_MATH_MAP = {
    '×': '\\times',
    '±': '\\pm',
    '÷': '\\div',
    '≤': '\\leq',
    '≥': '\\geq',
    '≠': '\\neq',
    '≈': '\\approx',
    '∞': '\\infty',
    'α': '\\alpha',
    'β': '\\beta',
    'γ': '\\gamma',
    'δ': '\\delta',
    'ε': '\\epsilon',
    'θ': '\\theta',
    'λ': '\\lambda',
    'μ': '\\mu',
    'π': '\\pi',
    'σ': '\\sigma',
    'φ': '\\phi',
    'ω': '\\omega',
    'Δ': '\\Delta',
    'Σ': '\\Sigma',
    'Ω': '\\Omega',
    '∫': '\\int',
    '∬': '\\iint',
    '∭': '\\iiint',
    '∮': '\\oint',
    '∑': '\\sum',
    '∏': '\\prod',
    '√': '\\sqrt',
    '∂': '\\partial',
    '∇': '\\nabla',
    '∈': '\\in',
    '∉': '\\notin',
    '⊂': '\\subset',
    '⊃': '\\supset',
    '∪': '\\cup',
    '∩': '\\cap',
    '→': '\\rightarrow',
    '←': '\\leftarrow',
    '↑': '\\uparrow',
    '↓': '\\downarrow',
    '↔': '\\leftrightarrow',
    '⇒': '\\Rightarrow',
    '⇐': '\\Leftarrow',
    '⇔': '\\Leftrightarrow',
    '∀': '\\forall',
    '∃': '\\exists',
    '∅': '\\emptyset',
    '°': '^\\circ',
    '−': '-',
    '·': '\\cdot',
}

def find_omml2mml_xslt() -> Optional[Path]:
    """Find the Microsoft OMML2MML.XSL stylesheet."""
    paths = [
        Path(r'C:\Program Files\Microsoft Office\root\Office16\OMML2MML.XSL'),
        Path(r'C:\Program Files (x86)\Microsoft Office\root\Office16\OMML2MML.XSL'),
        Path(r'C:\Program Files\Microsoft Office\Office16\OMML2MML.XSL'),
        Path(r'C:\Program Files (x86)\Microsoft Office\Office16\OMML2MML.XSL'),
    ]
    for p in paths:
        if p.exists():
            return p
    return None

def mathml_to_latex(node: etree._Element) -> str:
    """Convert MathML elements to LaTeX."""
    if node is None:
        return ""
    
    # Handle the text node itself if applicable (though usually within elements)
    if isinstance(node, str):
        return node
        
    tag = etree.QName(node.tag).localname
    
    if tag == 'math':
        return "".join(mathml_to_latex(child) for child in node)
    elif tag == 'mrow':
        return "{" + "".join(mathml_to_latex(child) for child in node) + "}"
    elif tag == 'mfrac':
        children = list(node)
        num = mathml_to_latex(children[0]) if len(children) > 0 else ""
        den = mathml_to_latex(children[1]) if len(children) > 1 else ""
        return f"\\frac{{{num}}}{{{den}}}"
    elif tag == 'msqrt':
        inner = "".join(mathml_to_latex(child) for child in node)
        return f"\\sqrt{{{inner}}}"
    elif tag == 'mroot':
        children = list(node)
        base = mathml_to_latex(children[0]) if len(children) > 0 else ""
        index = mathml_to_latex(children[1]) if len(children) > 1 else ""
        return f"\\sqrt[{index}]{{{base}}}"
    elif tag == 'msub':
        children = list(node)
        base = mathml_to_latex(children[0]) if len(children) > 0 else ""
        sub = mathml_to_latex(children[1]) if len(children) > 1 else ""
        return f"{base}_{{{sub}}}"
    elif tag == 'msup':
        children = list(node)
        base = mathml_to_latex(children[0]) if len(children) > 0 else ""
        sup = mathml_to_latex(children[1]) if len(children) > 1 else ""
        return f"{base}^{{{sup}}}"
    elif tag == 'msubsup':
        children = list(node)
        base = mathml_to_latex(children[0]) if len(children) > 0 else ""
        sub = mathml_to_latex(children[1]) if len(children) > 1 else ""
        sup = mathml_to_latex(children[2]) if len(children) > 2 else ""
        return f"{base}_{{{sub}}}^{{{sup}}}"
    elif tag == 'munderover':
        children = list(node)
        base = mathml_to_latex(children[0]) if len(children) > 0 else ""
        under = mathml_to_latex(children[1]) if len(children) > 1 else ""
        over = mathml_to_latex(children[2]) if len(children) > 2 else ""
        return f"{base}_{{{under}}}^{{{over}}}"
    elif tag == 'munder':
        children = list(node)
        base = mathml_to_latex(children[0]) if len(children) > 0 else ""
        under = mathml_to_latex(children[1]) if len(children) > 1 else ""
        return f"\\underset{{{under}}}{{{base}}}"
    elif tag == 'mover':
        children = list(node)
        base = mathml_to_latex(children[0]) if len(children) > 0 else ""
        over = mathml_to_latex(children[1]) if len(children) > 1 else ""
        return f"\\overset{{{over}}}{{{base}}}"
    elif tag == 'mi':
        text = node.text or ""
        text = text.strip()
        if len(text) > 1:
            return f"\\mathrm{{{text}}}"
        return UNICODE_MATH_MAP.get(text, text)
    elif tag == 'mn':
        text = node.text or ""
        return text.strip()
    elif tag == 'mo':
        text = node.text or ""
        text = text.strip()
        return UNICODE_MATH_MAP.get(text, text)
    elif tag == 'mtext':
        text = node.text or ""
        return f"\\text{{{text}}}"
    elif tag == 'mspace':
        return "\\quad "
    elif tag == 'mfenced':
        open_delim = node.get('open', '(')
        close_delim = node.get('close', ')')
        inner = "".join(mathml_to_latex(child) for child in node)
        return f"\\left{open_delim} {inner} \\right{close_delim}"
    elif tag == 'mtable':
        rows = [mathml_to_latex(child) for child in node if etree.QName(child.tag).localname == 'mtr']
        content = " \\\\ ".join(rows)
        return f"\\begin{{matrix}} {content} \\end{{matrix}}"
    elif tag == 'mtr':
        cols = [mathml_to_latex(child) for child in node if etree.QName(child.tag).localname == 'mtd']
        return " & ".join(cols)
    elif tag == 'mtd':
        return "".join(mathml_to_latex(child) for child in node)
    else:
        # Fallback for unknown tags
        return "".join(mathml_to_latex(child) for child in node)

def convert_omml_to_mathml(omml_node: etree._Element, xslt_transform) -> etree._Element:
    return xslt_transform(omml_node).getroot()

def extract_math(docx_path: Path, work_dir: Path) -> MathRegistry:
    """Extract all math from a .docx and convert to LaTeX.
    
    Returns MathRegistry with:
    - equations: list of MathEquation(position, latex, is_display, eq_number, original_omml)
    - inline_count: int
    - display_count: int
    """
    logger.info(f"Extracting math from {docx_path}")
    
    xslt_path = find_omml2mml_xslt()
    if xslt_path:
        xslt = etree.parse(str(xslt_path))
        transform = etree.XSLT(xslt)
    else:
        logger.warning("OMML2MML.XSL not found, falling back to pandoc's texmath (not implemented natively in script yet)")
        transform = None
        
    registry = MathRegistry()
    
    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'
    }
    
    with zipfile.ZipFile(docx_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = etree.parse(f)
            
    root = tree.getroot()
    
    paragraphs = root.xpath('//w:p', namespaces=namespaces)
    for p_idx, p in enumerate(paragraphs):
        omath_paras = p.xpath('.//m:oMathPara', namespaces=namespaces)
        for omath_para in omath_paras:
            # Try to detect equation numbering
            text_nodes = p.xpath('.//w:t/text()', namespaces=namespaces)
            text_str = "".join(text_nodes).strip()
            
            eq_num = None
            if "# (" in text_str and ")" in text_str:
                eq_num = text_str.split("# (")[-1].split(")")[0]
            
            for omath in omath_para.xpath('.//m:oMath', namespaces=namespaces):
                if transform:
                    mml = transform(omath)
                    latex = mathml_to_latex(mml.getroot())
                else:
                    latex = ""
                
                omml_str = etree.tostring(omath, encoding='unicode')
                eq = MathEquation(
                    position=p_idx,
                    latex=latex,
                    is_display=True,
                    eq_number=eq_num,
                    original_omml=omml_str
                )
                registry.equations.append(eq)
                registry.display_count += 1
                
        # Find inline oMath (not in oMathPara)
        omaths = p.xpath('.//m:oMath[not(ancestor::m:oMathPara)]', namespaces=namespaces)
        for omath in omaths:
            if transform:
                mml = transform(omath)
                latex = mathml_to_latex(mml.getroot())
            else:
                latex = ""
                
            omml_str = etree.tostring(omath, encoding='unicode')
            eq = MathEquation(
                position=p_idx,
                latex=latex,
                is_display=False,
                eq_number=None,
                original_omml=omml_str
            )
            registry.equations.append(eq)
            registry.inline_count += 1

    if work_dir:
        work_path = Path(work_dir)
        if work_path.suffix == ".json":
            out_file = work_path
        else:
            work_path.mkdir(parents=True, exist_ok=True)
            out_file = work_path / "math_registry.json"
        out_file.write_text(json.dumps(registry.to_dict(), indent=2), encoding="utf-8", newline="\n")
        logger.info(f"Saved math registry to {out_file}")
            
    return registry

def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Extract math from docx.")
    parser.add_argument("docx_path", type=Path, help="Path to input .docx file")
    parser.add_argument("work_dir", type=Path, help="Path to working directory")
    args = parser.parse_args()
    
    if not args.docx_path.exists():
        logger.error(f"Input file not found: {args.docx_path}")
        return
        
    registry = extract_math(args.docx_path, args.work_dir)
    logger.info(f"Extracted {registry.display_count} display equations and {registry.inline_count} inline equations.")

if __name__ == '__main__':
    main()
