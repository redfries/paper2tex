import sys
import logging
import zipfile
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from lxml import etree

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'v': 'urn:schemas-microsoft-com:vml',
    'o': 'urn:schemas-microsoft-com:office:office',
}

@dataclass
class PreprocessResult:
    cross_ref_map: Dict[str, str] = field(default_factory=dict)
    citation_type: str = 'none'
    warnings: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    modified_docx_path: Path = None


def get_symbol_map() -> Dict[str, str]:
    """Provides a mapping of ASCII characters to Greek characters/symbols in Symbol font."""
    mapping = {}
    symbol_to_greek_lower = {
        'a': 'α', 'b': 'β', 'c': 'χ', 'd': 'δ', 'e': 'ε', 'f': 'φ', 'g': 'γ', 
        'h': 'η', 'i': 'ι', 'j': 'ϕ', 'k': 'κ', 'l': 'λ', 'm': 'μ', 'n': 'ν', 
        'o': 'ο', 'p': 'π', 'q': 'θ', 'r': 'ρ', 's': 'σ', 't': 'τ', 'u': 'υ', 
        'v': 'ϖ', 'w': 'ω', 'x': 'ξ', 'y': 'ψ', 'z': 'ζ'
    }
    symbol_to_greek_upper = {
        'A': 'Α', 'B': 'Β', 'C': 'Χ', 'D': 'Δ', 'E': 'Ε', 'F': 'Φ', 'G': 'Γ', 
        'H': 'Η', 'I': 'Ι', 'J': 'Φ', 'K': 'Κ', 'L': 'Λ', 'M': 'Μ', 'N': 'Ν', 
        'O': 'Ο', 'P': 'Π', 'Q': 'Θ', 'R': 'Ρ', 'S': 'Σ', 'T': 'Τ', 'U': 'Υ', 
        'V': 'ς', 'W': 'Ω', 'X': 'Ξ', 'Y': 'Ψ', 'Z': 'Ζ'
    }
    mapping.update(symbol_to_greek_lower)
    mapping.update(symbol_to_greek_upper)
    mapping.update({
        '±': '±', '£': '≤', '³': '≥', '²': '²', '°': '°'
    })
    return mapping

def fix_symbol_fonts(tree: etree._Element):
    """Detects and replaces ASCII characters formatted as Symbol font to their unicode equivalent."""
    symbol_map = get_symbol_map()
    symbol_fonts = {'Symbol', 'MT Extra', 'MT Symbol'}
    
    for r in tree.findall('.//w:r', namespaces=NAMESPACES):
        fonts = r.find('.//w:rPr/w:rFonts', namespaces=NAMESPACES)
        if fonts is not None:
            ascii_font = fonts.get(f"{{{NAMESPACES['w']}}}ascii")
            hAnsi_font = fonts.get(f"{{{NAMESPACES['w']}}}hAnsi")
            if ascii_font in symbol_fonts or hAnsi_font in symbol_fonts:
                for t in r.findall('.//w:t', namespaces=NAMESPACES):
                    if t.text:
                        new_text = "".join(symbol_map.get(c, c) for c in t.text)
                        t.text = new_text
                # Remove the font override to let it fallback to default and be readable as normal unicode text
                if f"{{{NAMESPACES['w']}}}ascii" in fonts.attrib:
                    del fonts.attrib[f"{{{NAMESPACES['w']}}}ascii"]
                if f"{{{NAMESPACES['w']}}}hAnsi" in fonts.attrib:
                    del fonts.attrib[f"{{{NAMESPACES['w']}}}hAnsi"]

def accept_tracked_changes(tree: etree._Element):
    """Accepts tracked changes by removing deletions and unwrapping insertions."""
    for wdel in tree.findall('.//w:del', namespaces=NAMESPACES):
        wdel.getparent().remove(wdel)
    
    for wins in tree.findall('.//w:ins', namespaces=NAMESPACES):
        parent = wins.getparent()
        idx = parent.index(wins)
        for child in reversed(wins):
            parent.insert(idx, child)
        parent.remove(wins)

def strip_comments(tree: etree._Element):
    """Strips out all comment references from the document."""
    for tag in ['w:commentRangeStart', 'w:commentRangeEnd', 'w:commentReference']:
        for el in tree.findall(f'.//{tag}', namespaces=NAMESPACES):
            el.getparent().remove(el)

def extract_cross_ref_map(tree: etree._Element) -> Dict[str, str]:
    """Builds a map of bookmarks to semantic labels (e.g., fig:1)."""
    cross_ref_map = {}
    for bm in tree.findall('.//w:bookmarkStart', namespaces=NAMESPACES):
        name = bm.get(f"{{{NAMESPACES['w']}}}name")
        if not name or name.startswith('_GoBack'):
            continue
        
        para = bm.getparent()
        while para is not None and para.tag != f"{{{NAMESPACES['w']}}}p":
            para = para.getparent()
            
        if para is not None:
            texts = [t.text for t in para.findall('.//w:t', namespaces=NAMESPACES) if t.text]
            full_text = "".join(texts).lower()
            if 'fig' in full_text:
                cross_ref_map[name] = 'fig:' + name
            elif 'tab' in full_text:
                cross_ref_map[name] = 'tab:' + name
            elif 'eq' in full_text:
                cross_ref_map[name] = 'eq:' + name
            else:
                cross_ref_map[name] = 'sec:' + name
    return cross_ref_map

def detect_citation_manager(tree: etree._Element) -> str:
    """Detects if a citation manager is used based on field codes."""
    for instr in tree.findall('.//w:instrText', namespaces=NAMESPACES):
        if instr.text:
            text = instr.text.upper()
            if 'ADDIN ZOTERO' in text:
                return 'zotero'
            elif 'ADDIN EN.CITE' in text or 'ADDIN EN.REFLIST' in text:
                return 'endnote'
            elif 'ADDIN MENDELEY' in text:
                return 'mendeley'
    return 'none'

def process_document(xml_bytes: bytes) -> Tuple[bytes, PreprocessResult]:
    """Processes document.xml, applying all rules, and returns modified XML and results."""
    tree = etree.fromstring(xml_bytes)
    result = PreprocessResult()
    
    # 1. Symbol font trap fix
    fix_symbol_fonts(tree)
    
    # 2. Track changes
    accept_tracked_changes(tree)
    
    # 3. Strip comments
    strip_comments(tree)
    
    # 4. Cross reference map
    result.cross_ref_map = extract_cross_ref_map(tree)
    
    # 5. Citation manager detection
    result.citation_type = detect_citation_manager(tree)
    
    # 6. Text Box / Floating Object Detection
    txbx_count = len(tree.findall('.//w:txbxContent', namespaces=NAMESPACES))
    if txbx_count > 0:
        result.warnings.append(f"Found {txbx_count} text boxes. These might not convert well.")
        
    # 7. Legacy Math Detection
    ole_count = len(tree.findall('.//o:OLEObject', namespaces=NAMESPACES))
    if ole_count > 0:
        result.warnings.append(f"Found {ole_count} OLE objects, which could be legacy MathType equations.")

    # 8. Content Counting
    headings = 0
    for pPr in tree.findall('.//w:pPr', namespaces=NAMESPACES):
        pStyle = pPr.find('.//w:pStyle', namespaces=NAMESPACES)
        if pStyle is not None:
            val = pStyle.get(f"{{{NAMESPACES['w']}}}val")
            if val and val.lower().startswith('heading'):
                headings += 1
    
    figures = len(tree.findall('.//wp:inline', namespaces=NAMESPACES)) + len(tree.findall('.//wp:anchor', namespaces=NAMESPACES))
    tables = len(tree.findall('.//w:tbl', namespaces=NAMESPACES))
    equations = len(tree.findall('.//m:oMathPara', namespaces=NAMESPACES)) + len(tree.findall('.//m:oMath', namespaces=NAMESPACES))
    
    result.counts = {
        'sections': headings,
        'figures': figures,
        'tables': tables,
        'equations': equations,
        'footnotes': len(tree.findall('.//w:footnoteReference', namespaces=NAMESPACES))
    }
    
    return etree.tostring(tree, encoding='utf-8', xml_declaration=True), result


def preprocess_docx(docx_path: Path, work_dir: Path) -> PreprocessResult:
    """Run all preprocessing steps on a .docx file.
    
    Returns a PreprocessResult with:
    - cross_ref_map: dict mapping bookmark names to semantic labels
    - citation_type: 'zotero' | 'mendeley' | 'endnote' | 'none'
    - warnings: list of warning strings
    - counts: dict with section/figure/table/equation/footnote counts
    - modified_docx_path: Path to the preprocessed .docx (with Symbol fixes applied)
    """
    logger.info(f"Preprocessing {docx_path} into {work_dir}")
    if not docx_path.exists():
        raise FileNotFoundError(f"File not found: {docx_path}")
        
    work_dir.mkdir(parents=True, exist_ok=True)
    out_docx = work_dir / f"preprocessed_{docx_path.name}"
    
    result = PreprocessResult()
    
    with zipfile.ZipFile(docx_path, 'r') as zin, zipfile.ZipFile(out_docx, 'w') as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                logger.info("Processing word/document.xml")
                new_content, doc_result = process_document(content)
                zout.writestr(item, new_content)
                result = doc_result
            else:
                zout.writestr(item, content)
                
    result.modified_docx_path = out_docx
    logger.info(f"Finished preprocessing. Warnings: {len(result.warnings)}")
    return result

def main():
    parser = argparse.ArgumentParser(description="Preprocess a .docx file for paper2tex.")
    parser.add_argument("input_docx", type=Path, help="Path to the input .docx file")
    parser.add_argument("work_dir", type=Path, help="Path to the working directory")
    args = parser.parse_args()
    
    try:
        res = preprocess_docx(args.input_docx, args.work_dir)
        print("Preprocessing successful.")
        print(f"Modified Docx: {res.modified_docx_path}")
        print(f"Counts: {res.counts}")
        print(f"Citation Type: {res.citation_type}")
        if res.warnings:
            print("Warnings:")
            for w in res.warnings:
                print(f" - {w}")
    except Exception as e:
        logger.error(f"Failed to preprocess {args.input_docx}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
