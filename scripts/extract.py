import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

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

try:
    from scripts.preprocess import preprocess_docx
    from scripts.extract_math import extract_math
    from scripts.extract_tables import extract_tables
    from scripts.extract_figures import extract_figures
    from scripts.extract_bib import extract_bibliography
    from scripts.utils.char_map import detect_special_chars, get_required_packages
except ImportError:
    try:
        from .preprocess import preprocess_docx
        from .extract_math import extract_math
        from .extract_tables import extract_tables
        from .extract_figures import extract_figures
        from .extract_bib import extract_bibliography
        from .utils.char_map import detect_special_chars, get_required_packages
    except ImportError:
        from preprocess import preprocess_docx
        from extract_math import extract_math
        from extract_tables import extract_tables
        from extract_figures import extract_figures
        from extract_bib import extract_bibliography
        from utils.char_map import detect_special_chars, get_required_packages

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    manifest_path: Path
    manifest: Dict[str, Any]
    math_registry: Optional[Dict[str, Any]] = None
    table_registry: Optional[Dict[str, Any]] = None
    figure_registry: Optional[Dict[str, Any]] = None
    bib_registry: Optional[Dict[str, Any]] = None

import shutil
import os

def find_pandoc_exe() -> Optional[str]:
    exe = shutil.which("pandoc")
    if exe:
        return exe
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Pandoc" / "pandoc.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Pandoc" / "pandoc.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Pandoc" / "pandoc.exe",
        Path(r"C:\Program Files\Pandoc\pandoc.exe"),
    ]
    for c in candidates:
        if c and c.exists():
            return str(c)
    return None

def run_pandoc(input_path: Path, output_dir: Path) -> Tuple[Optional[Path], Optional[Path], List[str]]:
    warnings = []
    content_md = output_dir / "content.md"
    content_tex = output_dir / "content.tex"
    pandoc_exe = find_pandoc_exe()

    if not pandoc_exe:
        warnings.append("Pandoc not found. Skipping markdown and latex generation.")
        return None, None, warnings

    # md
    try:
        subprocess.run(
            [pandoc_exe, str(input_path), "-f", "docx", "-t", "markdown", "-o", str(content_md)],
            check=True, capture_output=True, text=True
        )
    except FileNotFoundError:
        warnings.append("Pandoc not found. Skipping markdown generation.")
        content_md = None
    except subprocess.CalledProcessError as e:
        warnings.append(f"Pandoc markdown generation failed: {e.stderr}")
        content_md = None

    # tex
    try:
        subprocess.run(
            [pandoc_exe, str(input_path), "-f", "docx", "-t", "latex", "-o", str(content_tex)],
            check=True, capture_output=True, text=True
        )
    except FileNotFoundError:
        if "Pandoc not found. Skipping markdown generation." not in warnings:
            warnings.append("Pandoc not found. Skipping latex generation.")
        content_tex = None
    except subprocess.CalledProcessError as e:
        warnings.append(f"Pandoc latex generation failed: {e.stderr}")
        content_tex = None

    return content_md, content_tex, warnings

def extract(docx_path: Path, work_dir: Path, figures_dir: Optional[Path] = None) -> ExtractionResult:
    if not figures_dir:
        figures_dir = work_dir / "figures"
        
    figures_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    all_warnings = []
    
    # Safe copy in case file is currently locked/opened in MS Word
    safe_docx = work_dir / f"safe_{docx_path.name}"
    try:
        shutil.copy2(docx_path, safe_docx)
        target_docx = safe_docx
    except Exception:
        target_docx = docx_path

    # 1. Preprocess
    logger.info("Running preprocessor...")
    try:
        prep_result = preprocess_docx(target_docx, work_dir)
        preprocessed_docx = prep_result.modified_docx_path
        cross_ref_map = prep_result.cross_ref_map
        citation_type = prep_result.citation_type
        counts = prep_result.counts
        all_warnings.extend(prep_result.warnings)
    except Exception as e:
        logger.error(f"Preprocessor failed: {e}")
        all_warnings.append(f"Preprocessor failed: {e}")
        preprocessed_docx = docx_path
        cross_ref_map = {}
        citation_type = "unknown"
        counts = {}

    # 2. Extract Math
    logger.info("Extracting math...")
    math_registry = None
    try:
        math_reg_obj = extract_math(preprocessed_docx, work_dir)
        math_registry = math_reg_obj.to_dict() if hasattr(math_reg_obj, "to_dict") else math_reg_obj
    except Exception as e:
        logger.error(f"Math extraction failed: {e}")
        all_warnings.append(f"Math extraction failed: {e}")

    # 3. Extract Tables
    logger.info("Extracting tables...")
    table_registry = None
    try:
        table_reg_obj = extract_tables(preprocessed_docx, work_dir)
        table_registry = table_reg_obj.to_dict() if hasattr(table_reg_obj, "to_dict") else table_reg_obj
    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        all_warnings.append(f"Table extraction failed: {e}")

    # 4. Extract Figures
    logger.info("Extracting figures...")
    figure_registry = None
    try:
        fig_reg_obj = extract_figures(preprocessed_docx, work_dir, figures_dir=figures_dir)
        figure_registry = fig_reg_obj.to_dict() if hasattr(fig_reg_obj, "to_dict") else fig_reg_obj
    except Exception as e:
        logger.error(f"Figure extraction failed: {e}")
        all_warnings.append(f"Figure extraction failed: {e}")

    # 5. Extract Bibliography
    logger.info("Extracting bibliography...")
    bib_registry = None
    try:
        bib_reg_obj = extract_bibliography(preprocessed_docx, work_dir, citation_type=citation_type)
        bib_registry = bib_reg_obj.to_dict() if hasattr(bib_reg_obj, "to_dict") else bib_reg_obj
    except Exception as e:
        logger.error(f"Bibliography extraction failed: {e}")
        all_warnings.append(f"Bibliography extraction failed: {e}")

    # 6. Pandoc
    logger.info("Running Pandoc conversion...")
    content_md, content_tex, pandoc_warnings = run_pandoc(preprocessed_docx, work_dir)
    all_warnings.extend(pandoc_warnings)

    # 7 & 8. Special characters & packages
    logger.info("Detecting special characters and packages...")
    special_chars = {}
    required_packages = []
    
    if content_md and content_md.exists():
        try:
            text = content_md.read_text(encoding="utf-8")
            special_chars = detect_special_chars(text)
            required_packages = sorted(list(get_required_packages(special_chars)))
        except Exception as e:
            logger.error(f"Special char detection failed: {e}")
            all_warnings.append(f"Special char detection failed: {e}")
    else:
        logger.warning("No markdown content available for special char detection.")
        all_warnings.append("No markdown content available for special char detection.")

    # 9. Build Manifest
    manifest = {
        "counts": counts if counts else {
            "sections": 0, "figures": 0, "tables": 0,
            "display_equations": 0, "inline_equations": 0,
            "footnotes": 0, "references": 0
        },
        "special_chars": special_chars,
        "cross_ref_map": cross_ref_map,
        "citation_type": citation_type,
        "warnings": all_warnings,
        "required_packages": required_packages,
        "registries": {
            "math": "math_registry.json" if (work_dir / "math_registry.json").exists() else None,
            "table": "table_registry.json" if (work_dir / "table_registry.json").exists() else None,
            "figures": "figures_registry.json" if (work_dir / "figures_registry.json").exists() else None,
            "bib": "bib_registry.json" if (work_dir / "bib_registry.json").exists() else None
        }
    }

    manifest_path = work_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    logger.info(f"Extraction complete. Manifest saved to {manifest_path}")

    return ExtractionResult(
        manifest_path=manifest_path,
        manifest=manifest,
        math_registry=math_registry,
        table_registry=table_registry,
        figure_registry=figure_registry,
        bib_registry=bib_registry
    )

def main():
    parser = argparse.ArgumentParser(description="Paper2Tex extraction pipeline.")
    parser.add_argument("input_docx", type=Path, help="Path to input .docx file")
    parser.add_argument("work_dir", type=Path, help="Working directory for outputs")
    parser.add_argument("--figures-dir", type=Path, help="Directory to save extracted figures (defaults to work_dir/figures)")

    args = parser.parse_args()

    extract(args.input_docx, args.work_dir, args.figures_dir)

if __name__ == "__main__":
    main()
