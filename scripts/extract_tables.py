import argparse
import logging
import json
import zipfile
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
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
class TableCell:
    content: str
    colspan: int = 1
    rowspan: int = 1
    alignment: str = 'l'  # l, c, r
    is_header: bool = False

@dataclass
class TableEntry:
    position: int
    latex: str
    caption: str
    label: str
    is_wide: bool
    notes: List[str]
    num_rows: int
    num_cols: int
    has_merged_cells: bool

@dataclass
class TableRegistry:
    tables: List[TableEntry]
    total_count: int
    merged_count: int

    def to_dict(self) -> dict:
        return {
            "total_count": self.total_count,
            "merged_count": self.merged_count,
            "tables": [
                {
                    "position": t.position,
                    "caption": t.caption,
                    "label": t.label,
                    "is_wide": t.is_wide,
                    "notes": t.notes,
                    "num_rows": t.num_rows,
                    "num_cols": t.num_cols,
                    "has_merged_cells": t.has_merged_cells,
                    "latex": t.latex,
                }
                for t in self.tables
            ],
        }

def parse_w_text(element: etree._Element, nsmap: dict) -> str:
    """Extract text from an element, considering math placeholders if any."""
    texts = []
    for t in element.xpath(".//w:t", namespaces=nsmap):
        if t.text:
            texts.append(t.text)
    return "".join(texts).strip()


def _escape_latex_cell(raw: str) -> str:
    if not raw:
        return ""
    t = raw.replace("\u00a0", " ")
    t = re.sub(r"(?<!\\)&", r"\&", t)
    t = re.sub(r"(?<!\\)%", r"\%", t)
    t = re.sub(r"(?<!\\)#", r"\#", t)
    t = re.sub(r"(?<!\\)_", r"\_", t)
    t = re.sub(r"(?<!\\)\$", r"\$", t)
    return t.strip()


def extract_tables(docx_path: Path, work_dir: Path) -> TableRegistry:
    """Extract all tables from a .docx and generate LaTeX.
    
    Returns TableRegistry with:
    - tables: list of TableEntry(position, latex, caption, label, is_wide, notes, ...)
    - total_count: int
    - merged_count: int (tables that have merged cells)
    """
    
    with zipfile.ZipFile(docx_path) as docx_zip:
        with docx_zip.open('word/document.xml') as f:
            tree = etree.parse(f)
            
    root = tree.getroot()
    nsmap = root.nsmap
    
    if 'w' not in nsmap:
        nsmap['w'] = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    
    body = root.find('w:body', nsmap)
    if body is None:
        return TableRegistry([], 0, 0)
        
    tables = []
    table_index = 0
    merged_tables_count = 0
    
    elements = list(body)
    
    for i, elem in enumerate(elements):
        if elem.tag == f"{{{nsmap['w']}}}tbl":
            # Skip empty placeholder tables with no text in any cell
            cells = elem.xpath('.//w:tc', namespaces=nsmap)
            all_text = "".join(parse_w_text(c, nsmap) for c in cells).strip()
            if not all_text:
                continue

            table_index += 1
            
            caption = ""
            label = f"tab:table{table_index}"
            notes = []
            
            # Simple caption extraction: paragraph before
            if i > 0 and elements[i-1].tag == f"{{{nsmap['w']}}}p":
                prev_text = parse_w_text(elements[i-1], nsmap)
                if "Table" in prev_text or "Caption" in etree.tostring(elements[i-1]).decode():
                    caption = prev_text
            
            # Simple notes extraction: paragraph after
            if i + 1 < len(elements) and elements[i+1].tag == f"{{{nsmap['w']}}}p":
                next_text = parse_w_text(elements[i+1], nsmap)
                if next_text and (next_text.startswith('*') or next_text.startswith('†') or next_text.startswith('‡')):
                    notes.append(next_text)

            tblGrid = elem.find('w:tblGrid', nsmap)
            num_cols = 0
            if tblGrid is not None:
                num_cols = len(tblGrid.findall('w:gridCol', nsmap))
                
            has_merged = False
            
            rows = elem.findall('w:tr', nsmap)
            num_rows = len(rows)
            
            cell_matrix: Dict[int, Dict[int, TableCell]] = {}
            for r in range(num_rows):
                cell_matrix[r] = {}
                
            rowspan_tracker = {}
            
            for r_idx, row in enumerate(rows):
                cells = row.findall('w:tc', nsmap)
                c_idx = 0
                for cell in cells:
                    while c_idx in cell_matrix[r_idx]:
                        c_idx += 1
                        
                    tcPr = cell.find('w:tcPr', nsmap)
                    
                    colspan = 1
                    rowspan_val = None
                    alignment = 'l'
                    
                    if tcPr is not None:
                        gridSpan = tcPr.find('w:gridSpan', nsmap)
                        if gridSpan is not None:
                            colspan = int(gridSpan.get(f"{{{nsmap['w']}}}val", 1))
                            has_merged = True
                            
                        vMerge = tcPr.find('w:vMerge', nsmap)
                        if vMerge is not None:
                            has_merged = True
                            val = vMerge.get(f"{{{nsmap['w']}}}val")
                            rowspan_val = 'restart' if val == 'restart' else 'continue'
                                
                        jc = cell.xpath('.//w:p/w:pPr/w:jc', namespaces=nsmap)
                        if jc:
                            val = jc[0].get(f"{{{nsmap['w']}}}val")
                            if val == 'center': alignment = 'c'
                            elif val == 'right': alignment = 'r'
                            
                    content = parse_w_text(cell, nsmap)
                    is_header = (r_idx == 0)
                    
                    cell_obj = TableCell(content=content, colspan=colspan, rowspan=1, alignment=alignment, is_header=is_header)
                    
                    if rowspan_val == 'restart':
                        rowspan_tracker[c_idx] = {'start_row': r_idx, 'cell': cell_obj}
                    elif rowspan_val == 'continue':
                        if c_idx in rowspan_tracker:
                            tracker = rowspan_tracker[c_idx]
                            tracker['cell'].rowspan += 1
                            cell_obj.content = ""
                            cell_obj.rowspan = 0 # Mark as continuation
                    
                    for cs in range(colspan):
                        if cs == 0:
                            cell_matrix[r_idx][c_idx + cs] = cell_obj
                        else:
                            # Dummy cell for colspan
                            cell_matrix[r_idx][c_idx + cs] = TableCell("", 1, 1, alignment, is_header)
                            cell_matrix[r_idx][c_idx + cs].colspan = 0 # Mark as continuation
                        
                    c_idx += colspan
                    
            is_wide = num_cols >= 4
            
            latex_lines = []
            env = "table*" if is_wide else "table"
            latex_lines.append(f"\\begin{{{env}}}[htbp]")
            latex_lines.append(f"\\centering")
            if caption:
                clean_cap = _escape_latex_cell(caption)
                latex_lines.append(f"\\caption{{{clean_cap}}}")
                latex_lines.append(f"\\label{{{label}}}")
                
            if is_wide:
                cols_format = "l" + "c" * (num_cols - 1)
                latex_lines.append(f"\\begin{{tabular*}}{{\\textwidth}}{{@{{\\extracolsep{{\\fill}}}}{cols_format}}}")
            else:
                cols_format = "l" * num_cols
                latex_lines.append(f"\\begin{{tabular}}{{{cols_format}}}")
            latex_lines.append(f"\\toprule")
            
            for r_idx in range(num_rows):
                rendered_row_tex = []
                c_idx = 0
                cmidrules = []
                while c_idx < num_cols:
                    cell = cell_matrix[r_idx].get(c_idx)
                    if cell is None:
                        c_idx += 1
                        continue
                        
                    if cell.rowspan == 0:
                        rendered_row_tex.append("")
                        c_idx += 1
                    elif cell.colspan == 0:
                        c_idx += 1
                    else:
                        text = _escape_latex_cell(cell.content)
                        if cell.is_header or r_idx < 2:
                            # Bold headers if not empty
                            if text and not text.startswith("\\textbf{"):
                                text = f"\\textbf{{{text}}}"
                        if cell.colspan > 1 and cell.rowspan > 1:
                            text = f"\\multicolumn{{{cell.colspan}}}{{c}}{{\\multirow{{{cell.rowspan}}}{{*}}{{{text}}}}}"
                            cmidrules.append(f"\\cmidrule(lr){{{c_idx + 1}-{c_idx + cell.colspan}}}")
                        elif cell.colspan > 1:
                            text = f"\\multicolumn{{{cell.colspan}}}{{c}}{{{text}}}"
                            cmidrules.append(f"\\cmidrule(lr){{{c_idx + 1}-{c_idx + cell.colspan}}}")
                        elif cell.rowspan > 1:
                            text = f"\\multirow{{{cell.rowspan}}}{{*}}{{{text}}}"
                        rendered_row_tex.append(text)
                        c_idx += cell.colspan
                        
                latex_lines.append(" & ".join(rendered_row_tex) + " \\\\")
                if r_idx == 0 and cmidrules:
                    latex_lines.append(" ".join(cmidrules))
                elif r_idx == 1 or (r_idx == 0 and not cmidrules):
                    latex_lines.append("\\midrule")
                    
            latex_lines.append("\\bottomrule")
            if is_wide:
                latex_lines.append("\\end{tabular*}")
            else:
                latex_lines.append("\\end{tabular}")
            if notes:
                latex_lines.append("\\vspace{1ex}")
                latex_lines.append("\\raggedright")
                for note in notes:
                    latex_lines.append(f"\\small {_escape_latex_cell(note)} \\par")
            latex_lines.append(f"\\end{{{env}}}")
            
            table_entry = TableEntry(
                position=i,
                latex="\n".join(latex_lines),
                caption=caption,
                label=label,
                is_wide=is_wide,
                notes=notes,
                num_rows=num_rows,
                num_cols=num_cols,
                has_merged_cells=has_merged
            )
            tables.append(table_entry)
            if has_merged:
                merged_tables_count += 1
                
    registry = TableRegistry(tables=tables, total_count=len(tables), merged_count=merged_tables_count)

    if work_dir:
        work_path = Path(work_dir)
        if work_path.suffix == ".json":
            out_file = work_path
        else:
            work_path.mkdir(parents=True, exist_ok=True)
            out_file = work_path / "table_registry.json"
        out_file.write_text(json.dumps(registry.to_dict(), indent=2), encoding="utf-8", newline="\n")
        logger.info(f"Saved table registry to {out_file}")

    return registry

def main():
    parser = argparse.ArgumentParser(description="Extract tables from a .docx file and convert to LaTeX")
    parser.add_argument("input", type=Path, help="Path to input .docx file")
    parser.add_argument("work_dir", type=Path, help="Path to working directory")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
        
    args.work_dir.mkdir(parents=True, exist_ok=True)
    
    registry = extract_tables(args.input, args.work_dir)
    logger.info(f"Extracted {registry.total_count} tables ({registry.merged_count} with merged cells)")
    
    for i, t in enumerate(registry.tables):
        out_file = args.work_dir / f"table_{i+1}.tex"
        # Ensure correct line endings
        out_file.write_bytes(t.latex.replace("\r\n", "\n").encode("utf-8"))
        logger.info(f"Wrote {out_file}")

if __name__ == '__main__':
    main()
