"""
paper2tex: extract_figures — Extract figures from .docx and reconcile with external folders.

Pipeline:
1. Extract embedded images from word/media/ (original quality)
2. Parse <w:drawing> elements → map relationship IDs to media files, document position, rotation & flip transforms
3. Apply OpenXML transformations (rotation, flips, EXIF orientation) via Pillow
4. Compute TRUE physical pixel geometry and aspect ratio
5. Parse captions & decompose multi-part subcaptions ((a), (b), (c))
6. Detect subfigure groups with intelligent layout hints (stacked vs side-by-side vs grid)
7. Scan external directories for higher-quality versions & vector formats
8. Reconcile and save clean upright assets to figures/
"""

from __future__ import annotations

import logging
import json
import re
import shutil
import sys
import zipfile
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

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
    from lxml import etree
except ImportError:
    etree = None  # type: ignore

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None  # type: ignore
    ImageOps = None  # type: ignore

log = logging.getLogger(__name__)

# OpenXML namespaces
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps", ".tiff", ".tif", ".bmp", ".gif", ".emf", ".wmf"}
VECTOR_EXTENSIONS = {".pdf", ".svg", ".eps", ".emf"}
SCAN_DIR_NAMES = {"figures", "figs", "images", "img", "pics", "media", "assets", "plots", "graphs"}

CAPTION_PATTERN = re.compile(
    r"(?:Figure|Fig\.?|TABLE|Table|Tab\.?)\s*(\d+)",
    re.IGNORECASE,
)


@dataclass
class FigureEntry:
    """A single figure extracted from the document."""
    fig_id: str                          # e.g., "fig1"
    embedded_path: Path | None           # Path in word/media/
    external_path: Path | None           # Path from external folder (if found)
    output_path: Path | None             # Final path in submission/figures/
    caption: str = ""                    # Full caption string
    main_caption: str = ""               # Caption title without (a)/(b) sub-parts
    subcaptions: dict[str, str] = field(default_factory=dict) # e.g. {"a": "...", "b": "..."}
    subfig_letter: str = ""              # "a", "b", "c", etc.
    label: str = ""                      # e.g., "fig:architecture"
    doc_position: int = 0                # Paragraph index in document
    is_subfigure: bool = False
    subfigure_group: str | None = None
    quality: str = "embedded"            # "vector", "external_raster", "embedded"
    width_hint: str = "\\linewidth"      # Default width for \includegraphics
    aspect_ratio: float = 1.0            # True physical width / height
    orientation: str = "landscape"       # "landscape", "portrait", "square"
    cx_emu: int = 0
    cy_emu: int = 0
    rot_degrees: float = 0.0             # OpenXML rotation in degrees
    flip_h: bool = False
    flip_v: bool = False
    figure_number: int | None = None


@dataclass
class FigureRegistry:
    """All figures extracted from the document."""
    figures: list[FigureEntry] = field(default_factory=list)
    total_count: int = 0
    subfigure_groups: int = 0
    external_matches: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_count": self.total_count,
            "subfigure_groups": self.subfigure_groups,
            "external_matches": self.external_matches,
            "warnings": self.warnings,
            "figures": [
                {
                    "fig_id": f.fig_id,
                    "caption": f.caption,
                    "main_caption": f.main_caption,
                    "subcaptions": f.subcaptions,
                    "subfig_letter": f.subfig_letter,
                    "label": f.label,
                    "output_path": str(f.output_path) if f.output_path else None,
                    "quality": f.quality,
                    "doc_position": f.doc_position,
                    "is_subfigure": f.is_subfigure,
                    "subfigure_group": f.subfigure_group,
                    "aspect_ratio": round(f.aspect_ratio, 3),
                    "orientation": f.orientation,
                    "width_hint": f.width_hint,
                    "figure_number": f.figure_number,
                }
                for f in self.figures
            ],
        }


def parse_subcaptions(caption: str) -> tuple[str, dict[str, str]]:
    """Splits a composite caption with (a), (b), (c) markers into main title + subcaption dict."""
    if not caption:
        return "", {}

    cleaned = re.sub(r"^(?:Figure|Fig\.?|TABLE|Table)\s*\d+[:.]\s*", "", caption, flags=re.IGNORECASE).strip()
    parts = re.split(r"\(\s*([a-hA-H])\s*\)", cleaned)
    if len(parts) >= 3:
        main_title = parts[0].strip().rstrip(":-–—, ")
        sub_dict = {}
        for i in range(1, len(parts), 2):
            letter = parts[i].lower()
            text = parts[i + 1].strip().rstrip(";., ")
            sub_dict[letter] = text
        return main_title, sub_dict

    return cleaned, {}


def _extract_embedded_media(docx_path: Path, work_dir: Path) -> dict[str, Path]:
    """Extract all files from word/media/ in the docx zip."""
    media_dir = work_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    extracted = {}

    with zipfile.ZipFile(docx_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("word/media/"):
                filename = Path(name).name
                if filename:
                    target = media_dir / filename
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    extracted[filename] = target
                    log.debug("Extracted: %s → %s", name, target)

    log.info("Extracted %d media files from docx", len(extracted))
    return extracted


def _build_relationship_map(docx_path: Path) -> dict[str, str]:
    """Parse word/_rels/document.xml.rels to map rId → media filename."""
    rId_to_file: dict[str, str] = {}

    with zipfile.ZipFile(docx_path, "r") as zf:
        rels_path = "word/_rels/document.xml.rels"
        if rels_path not in zf.namelist():
            log.warning("No document.xml.rels found in docx")
            return rId_to_file

        with zf.open(rels_path) as f:
            tree = etree.parse(f)

        for rel in tree.getroot():
            rel_type = rel.get("Type", "")
            if "image" in rel_type.lower() or "media" in rel_type.lower():
                rId = rel.get("Id", "")
                target = rel.get("Target", "")
                filename = Path(target).name
                if rId and filename:
                    rId_to_file[rId] = filename

    return rId_to_file


def _parse_drawings(doc_xml: etree._Element, rId_map: dict[str, str]) -> list[dict]:
    """Parse all <w:drawing> elements to extract figure information, including OpenXML transforms."""
    drawings = []
    body = doc_xml.find(".//w:body", namespaces=NS)
    if body is None:
        return drawings

    paragraphs = body.findall("w:p", namespaces=NS)

    for para_idx, para in enumerate(paragraphs):
        for drawing in para.findall(".//w:drawing", namespaces=NS):
            inline = drawing.find("wp:inline", namespaces=NS)
            anchor = drawing.find("wp:anchor", namespaces=NS)
            container = inline if inline is not None else anchor

            if container is None:
                continue

            blip = container.find(".//a:blip", namespaces=NS)
            if blip is None:
                continue

            r_embed = blip.get(f"{{{NS['r']}}}embed", "")
            filename = rId_map.get(r_embed, "")

            doc_pr = container.find(".//wp:docPr", namespaces=NS)
            if doc_pr is None:
                doc_pr = container.find("wp:docPr", namespaces=NS)
            alt_text = ""
            if doc_pr is not None:
                alt_text = doc_pr.get("descr", "") or doc_pr.get("name", "")

            # Get extent (dimensions in EMUs)
            extent = container.find(".//wp:extent", namespaces=NS)
            if extent is None:
                extent = container.find("wp:extent", namespaces=NS)
            cx_emu = 0
            cy_emu = 0
            if extent is not None:
                try:
                    cx_emu = int(extent.get("cx", 0))
                    cy_emu = int(extent.get("cy", 0))
                except Exception:
                    pass

            # Parse OpenXML rotation & flip transforms
            rot_degrees = 0.0
            flip_h = False
            flip_v = False
            xfrm = container.find(".//a:xfrm", namespaces=NS)
            if xfrm is not None:
                rot_str = xfrm.get("rot")
                if rot_str:
                    try:
                        rot_degrees = int(rot_str) / 60000.0
                    except Exception:
                        pass
                flip_h = xfrm.get("flipH") == "1"
                flip_v = xfrm.get("flipV") == "1"

            drawings.append({
                "rId": r_embed,
                "filename": filename,
                "paragraph_index": para_idx,
                "is_inline": inline is not None,
                "alt_text": alt_text,
                "cx_emu": cx_emu,
                "cy_emu": cy_emu,
                "rot_degrees": rot_degrees,
                "flip_h": flip_h,
                "flip_v": flip_v,
            })

    log.info("Found %d drawings in document", len(drawings))
    return drawings


def _find_captions(
    doc_xml: etree._Element,
    drawings: list[dict],
) -> dict[int, str]:
    """Find captions for figures by looking at nearby paragraphs."""
    body = doc_xml.find(".//w:body", namespaces=NS)
    if body is None:
        return {}

    paragraphs = body.findall("w:p", namespaces=NS)
    captions: dict[int, str] = {}

    caption_paragraphs: dict[int, str] = {}
    for para_idx, para in enumerate(paragraphs):
        pPr = para.find("w:pPr", namespaces=NS)
        if pPr is not None:
            pStyle = pPr.find("w:pStyle", namespaces=NS)
            if pStyle is not None:
                style_val = pStyle.get(f"{{{NS['w']}}}val", "")
                if "caption" in style_val.lower():
                    text = _get_paragraph_text(para)
                    if text.strip():
                        caption_paragraphs[para_idx] = text.strip()

    for para_idx, para in enumerate(paragraphs):
        if para_idx in caption_paragraphs:
            continue
        text = _get_paragraph_text(para)
        if CAPTION_PATTERN.match(text.strip()):
            caption_paragraphs[para_idx] = text.strip()

    for draw_idx, draw in enumerate(drawings):
        draw_para = draw["paragraph_index"]
        for offset in [1, 2, -1, 3, -2, 4]:
            check_para = draw_para + offset
            if check_para in caption_paragraphs:
                caption_text = caption_paragraphs[check_para]
                if re.match(r"(?:Figure|Fig\.?)", caption_text, re.IGNORECASE):
                    captions[draw_idx] = caption_text
                    break
                elif not re.match(r"(?:Table|Tab\.?)", caption_text, re.IGNORECASE):
                    captions[draw_idx] = caption_text
                    break

    return captions


def _get_paragraph_text(para) -> str:
    """Extract plain text from a paragraph element."""
    texts = []
    for t in para.iter(f"{{{NS['w']}}}t"):
        if t.text:
            texts.append(t.text)
    return "".join(texts)


def _scan_external_figures(docx_path: Path, figures_dir: Path | None = None) -> dict[str, Path]:
    """Scan directories near the docx for external figure files."""
    external: dict[str, Path] = {}
    parent = docx_path.parent

    dirs_to_scan: list[Path] = []
    if figures_dir and figures_dir.exists():
        dirs_to_scan.append(figures_dir)

    for name in SCAN_DIR_NAMES:
        candidate = parent / name
        if candidate.exists() and candidate.is_dir():
            dirs_to_scan.append(candidate)

    dirs_to_scan.append(parent)

    for d in dirs_to_scan:
        pattern = d.rglob("*") if d != parent else d.glob("*")
        for f in pattern:
            if f.is_file() and f.suffix.lower() in FIGURE_EXTENSIONS:
                key = f.stem.lower().replace("-", "_").replace(" ", "_")
                if key not in external:
                    external[key] = f

    log.info("Found %d external figure files", len(external))
    return external


def _process_image_transform(
    src_path: Path,
    dst_path: Path,
    rot_degrees: float = 0.0,
    flip_h: bool = False,
    flip_v: bool = False,
    cx_emu: int = 0,
    cy_emu: int = 0,
) -> tuple[float, str]:
    """Applies rotation, flips, and EXIF orientation via Pillow.

    Returns:
        (true_aspect_ratio, orientation_str)
    """
    if Image is None or not src_path.exists():
        shutil.copy2(src_path, dst_path)
        return 1.0, "landscape"

    try:
        with Image.open(src_path) as img:
            if ImageOps is not None:
                img = ImageOps.exif_transpose(img)

            w_raw, h_raw = img.size
            raw_is_landscape = w_raw >= h_raw

            is_90_or_270 = (
                abs(rot_degrees - 90) < 1.0
                or abs(rot_degrees - 270) < 1.0
                or abs(rot_degrees + 90) < 1.0
                or abs(rot_degrees + 270) < 1.0
            )
            disp_w = cy_emu if is_90_or_270 and cy_emu > 0 else cx_emu
            disp_h = cx_emu if is_90_or_270 and cx_emu > 0 else cy_emu
            disp_is_landscape = (disp_w >= disp_h) if (disp_w > 0 and disp_h > 0) else raw_is_landscape

            if is_90_or_270 and (raw_is_landscape != disp_is_landscape):
                img = img.rotate(-rot_degrees, expand=True)
            elif rot_degrees in (180.0, -180.0):
                img = img.rotate(180, expand=True)

            if flip_h:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if flip_v:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            dst_path.parent.mkdir(parents=True, exist_ok=True)
            fmt = img.format or "PNG"
            img.save(dst_path, format=fmt)

            w, h = img.size
            ar = (w / h) if h > 0 else 1.0
            orient = "landscape" if ar > 1.15 else ("portrait" if ar < 0.85 else "square")
            return ar, orient
    except Exception as e:
        log.warning("Image processing transform failed for %s: %s", src_path.name, e)
        shutil.copy2(src_path, dst_path)
        return 1.0, "landscape"


def _reconcile_figures(
    drawings: list[dict],
    captions: dict[int, str],
    embedded_files: dict[str, Path],
    external_files: dict[str, Path],
    output_dir: Path,
) -> list[FigureEntry]:
    """Match embedded figures to external versions, apply OpenXML transforms, prefer higher quality."""
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    entries: list[FigureEntry] = []

    for draw_idx, draw in enumerate(drawings):
        fig_num = draw_idx + 1
        fig_id = f"fig{fig_num}"
        embedded_filename = draw["filename"]
        embedded_path = embedded_files.get(embedded_filename)

        if embedded_path:
            ext = embedded_path.suffix.lower()
        else:
            ext = ".png"

        external_path: Path | None = None
        quality = "embedded"

        if embedded_filename:
            stem = Path(embedded_filename).stem.lower().replace("-", "_").replace(" ", "_")
            if stem in external_files:
                external_path = external_files[stem]

        if external_path:
            ext = external_path.suffix.lower()
            if ext in VECTOR_EXTENSIONS:
                quality = "vector"
            else:
                quality = "external_raster"

        output_ext = ext if ext != ".svg" else ".pdf"
        output_filename = f"{fig_id}{output_ext}"
        output_path = figures_dir / output_filename

        source = external_path if external_path else embedded_path
        rot_deg = draw.get("rot_degrees", 0.0)
        flip_h = draw.get("flip_h", False)
        flip_v = draw.get("flip_v", False)

        aspect_ratio = 1.0
        orientation = "landscape"

        if source and source.exists():
            if ext == ".svg":
                _convert_svg_to_pdf(source, output_path)
            elif ext in VECTOR_EXTENSIONS:
                shutil.copy2(source, output_path)
            else:
                aspect_ratio, orientation = _process_image_transform(
                    source, output_path, rot_deg, flip_h, flip_v,
                    cx_emu=draw.get("cx_emu", 0),
                    cy_emu=draw.get("cy_emu", 0),
                )

        caption = captions.get(draw_idx, "")
        main_title, subcaptions = parse_subcaptions(caption)
        label = _generate_label(main_title or caption, fig_id)

        entries.append(FigureEntry(
            fig_id=fig_id,
            embedded_path=embedded_path,
            external_path=external_path,
            output_path=output_path,
            caption=caption,
            main_caption=main_title,
            subcaptions=subcaptions,
            label=label,
            doc_position=draw["paragraph_index"],
            quality=quality,
            aspect_ratio=aspect_ratio,
            orientation=orientation,
            cx_emu=draw.get("cx_emu", 0),
            cy_emu=draw.get("cy_emu", 0),
            rot_degrees=rot_deg,
            flip_h=flip_h,
            flip_v=flip_v,
        ))

    return entries


def _generate_label(caption: str, fallback: str) -> str:
    """Generate a LaTeX label from a caption string."""
    if not caption:
        return f"fig:{fallback}"

    cleaned = re.sub(r"^(?:Figure|Fig\.?)\s*\d+[:.]\s*", "", caption, flags=re.IGNORECASE)
    words = re.findall(r"[a-zA-Z]+", cleaned)
    if words:
        slug = "_".join(w.lower() for w in words[:3])
        return f"fig:{slug}"
    return f"fig:{fallback}"


def _convert_svg_to_pdf(svg_path: Path, pdf_path: Path) -> bool:
    """Convert SVG to PDF using inkscape or cairosvg."""
    inkscape = shutil.which("inkscape")
    if inkscape:
        try:
            import subprocess
            subprocess.run(
                [inkscape, str(svg_path), f"--export-filename={pdf_path}"],
                capture_output=True, timeout=30, check=True,
            )
            return True
        except Exception as e:
            log.warning("Inkscape SVG→PDF failed: %s", e)

    try:
        import cairosvg  # type: ignore
        cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
        return True
    except Exception as e:
        log.warning("cairosvg SVG→PDF failed: %s", e)

    shutil.copy2(svg_path, pdf_path.with_suffix(".svg"))
    return False


def _extract_fig_num(caption: str) -> int | None:
    if not caption:
        return None
    m = re.search(r"(?:Figure|Fig\.?)\s*(\d+)", caption, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _detect_subfigure_groups(
    figures: list[FigureEntry],
    doc_xml: etree._Element,
) -> list[FigureEntry]:
    """Detect groups of figures that should be subfigures, correlate subcaptions, and deduplicate."""
    if len(figures) < 2:
        return figures

    for f in figures:
        f.figure_number = _extract_fig_num(f.caption)

    i = 0
    group_id = 0
    letters = ["a", "b", "c", "d", "e", "f", "g", "h"]

    while i < len(figures):
        group = [i]
        j = i + 1
        while j < len(figures):
            f_i = figures[i]
            f_j = figures[j]
            pos_close = (figures[j].doc_position - figures[j - 1].doc_position) <= 4

            same_fig_num = (
                f_i.figure_number is not None and
                f_j.figure_number is not None and
                f_i.figure_number == f_j.figure_number
            )
            same_caption = (
                bool(f_i.caption) and
                f_i.caption.strip() == f_j.caption.strip()
            )
            has_subfig_marker = bool(
                re.search(r"\([a-d]\)", f_i.caption) or
                re.search(r"\([a-d]\)", f_j.caption)
            )

            diff_fig_num = (
                f_i.figure_number is not None and
                f_j.figure_number is not None and
                f_i.figure_number != f_j.figure_number
            )

            if pos_close and not diff_fig_num and (same_fig_num or same_caption or (has_subfig_marker and f_j.figure_number is None)):
                group.append(j)
                j += 1
            else:
                break

        if len(group) >= 2:
            def _get_hash(fig_idx: int) -> str:
                fp = Path(figures[fig_idx].output_path)
                if not fp.exists() and figures[fig_idx].embedded_path:
                    fp = Path(figures[fig_idx].embedded_path)
                if fp.exists():
                    try:
                        return hashlib.sha256(fp.read_bytes()).hexdigest()
                    except Exception:
                        return f"path:{fp.name}"
                return f"idx:{fig_idx}"

            group_hashes = [_get_hash(idx) for idx in group]
            unique_hashes = set(group_hashes)
            has_subfig_caption = bool(figures[group[0]].subcaptions)

            if len(unique_hashes) == 1 and not has_subfig_caption:
                primary_idx = group[0]
                figures[primary_idx].is_subfigure = False
                figures[primary_idx].subfigure_group = None
                figures[primary_idx].width_hint = "\\linewidth"
                for dup_idx in group[1:]:
                    figures[dup_idx].subfigure_group = "__DUPLICATE_DROP__"
            else:
                group_id += 1
                group_name = f"subfig_group_{group_id}"
                n = len(group)
                avg_ar = sum(figures[idx].aspect_ratio for idx in group) / n if n > 0 else 1.0

                if avg_ar >= 1.0:
                    w = "0.95\\linewidth"
                elif avg_ar < 0.8 and n <= 3:
                    w = f"{0.95 / n:.2f}\\linewidth"
                elif n == 4:
                    w = "0.48\\linewidth"
                else:
                    w = f"{0.96 / n:.2f}\\textwidth"

                for g_pos, idx in enumerate(group):
                    figures[idx].is_subfigure = True
                    figures[idx].subfigure_group = group_name
                    figures[idx].width_hint = w
                    if g_pos < len(letters):
                        figures[idx].subfig_letter = letters[g_pos]

        i = j if j > i + 1 else i + 1

    figures = [f for f in figures if f.subfigure_group != "__DUPLICATE_DROP__"]
    return figures


def extract_figures(
    docx_path: Path,
    work_dir: Path,
    figures_dir: Path | None = None,
) -> FigureRegistry:
    """Extract all figures from a .docx and reconcile with external sources."""
    if etree is None:
        raise ImportError("lxml is required: pip install lxml")

    registry = FigureRegistry()
    work_dir.mkdir(parents=True, exist_ok=True)

    embedded_files = _extract_embedded_media(docx_path, work_dir)
    rId_map = _build_relationship_map(docx_path)

    with zipfile.ZipFile(docx_path, "r") as zf:
        with zf.open("word/document.xml") as f:
            doc_tree = etree.parse(f)
    doc_xml = doc_tree.getroot()

    drawings = _parse_drawings(doc_xml, rId_map)
    captions = _find_captions(doc_xml, drawings)
    external_files = _scan_external_figures(docx_path, figures_dir)

    figures = _reconcile_figures(
        drawings, captions, embedded_files, external_files, work_dir,
    )
    figures = _detect_subfigure_groups(figures, doc_xml)

    registry.figures = figures
    registry.total_count = len(figures)
    registry.subfigure_groups = len(set(
        f.subfigure_group for f in figures if f.subfigure_group
    ))
    registry.external_matches = sum(1 for f in figures if f.external_path is not None)

    generic_names = [f for f in figures if f.embedded_path and f.embedded_path.stem.startswith("image")]
    if generic_names and not registry.external_matches:
        registry.warnings.append(
            f"{len(generic_names)} figures have generic names (image1, image2...) "
            "and no external matches were found. Consider providing a --figures-dir."
        )

    missing_captions = [f for f in figures if not f.caption]
    if missing_captions:
        registry.warnings.append(
            f"{len(missing_captions)} figures have no detected caption."
        )

    log.info(
        "Figure extraction complete: %d figures, %d subfigure groups, %d external matches",
        registry.total_count, registry.subfigure_groups, registry.external_matches,
    )

    if work_dir:
        work_path = Path(work_dir)
        if work_path.suffix == ".json":
            out_file = work_path
        else:
            work_path.mkdir(parents=True, exist_ok=True)
            out_file = work_path / "figures_registry.json"
        out_file.write_text(json.dumps(registry.to_dict(), indent=2), encoding="utf-8", newline="\n")
        log.info(f"Saved figures registry to {out_file}")

    return registry


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python extract_figures.py <input.docx> <work_dir> [--figures-dir <path>]")
        sys.exit(1)

    docx_path = Path(sys.argv[1])
    work_dir = Path(sys.argv[2])
    figures_dir = None

    if "--figures-dir" in sys.argv:
        idx = sys.argv.index("--figures-dir")
        if idx + 1 < len(sys.argv):
            figures_dir = Path(sys.argv[idx + 1])

    registry = extract_figures(docx_path, work_dir, figures_dir)
    print(json.dumps(registry.to_dict(), indent=2))


if __name__ == "__main__":
    main()
