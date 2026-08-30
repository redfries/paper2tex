"""
paper2tex: preflight — Check that all required tools are installed.

Verifies pandoc, tectonic/tinytex, Python dependencies, and OMML2MML.XSL.
Prints human-readable status + install instructions for anything missing.
"""

from __future__ import annotations

import importlib
import logging
import os
import shutil
import subprocess
import sys
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

log = logging.getLogger(__name__)


@dataclass
class ToolStatus:
    """Status of a single required tool."""
    name: str
    found: bool
    path: str | None = None
    version: str | None = None
    install_hint: str | None = None


@dataclass
class PreflightResult:
    """Result of all preflight checks."""
    tools: list[ToolStatus] = field(default_factory=list)
    all_ok: bool = False
    omml2mml_xsl_path: Path | None = None

    def summary(self) -> str:
        lines = ["paper2tex preflight check", "=" * 40]
        for t in self.tools:
            icon = "✅" if t.found else "❌"
            ver = f" (v{t.version})" if t.version else ""
            loc = f" [{t.path}]" if t.path else ""
            lines.append(f"  {icon} {t.name}{ver}{loc}")
            if not t.found and t.install_hint:
                lines.append(f"     → Install: {t.install_hint}")
        lines.append("=" * 40)
        status = "All checks passed ✅" if self.all_ok else "Some checks failed — see above ❌"
        lines.append(status)
        return "\n".join(lines)


def _check_command(name: str, cmd: list[str], version_flag: str = "--version") -> ToolStatus:
    """Check if a command-line tool is available."""
    exe = shutil.which(name)
    if exe is None:
        return ToolStatus(name=name, found=False)
    try:
        result = subprocess.run(
            [exe, version_flag],
            capture_output=True, text=True, timeout=15,
        )
        version_line = (result.stdout or result.stderr).strip().split("\n")[0]
        return ToolStatus(name=name, found=True, path=exe, version=version_line)
    except Exception:
        return ToolStatus(name=name, found=True, path=exe)


def _check_python_package(name: str, import_name: str | None = None) -> ToolStatus:
    """Check if a Python package is importable."""
    mod = import_name or name
    try:
        m = importlib.import_module(mod)
        ver = getattr(m, "__version__", None)
        return ToolStatus(name=f"python:{name}", found=True, version=ver)
    except ImportError:
        return ToolStatus(
            name=f"python:{name}", found=False,
            install_hint=f"pip install {name}",
        )


def _find_omml2mml_xsl() -> Path | None:
    """Locate Microsoft's OMML2MML.XSL stylesheet."""
    candidates = [
        # Standard Office 365 / Office 2021 location
        Path(r"C:\Program Files\Microsoft Office\root\Office16\OMML2MML.XSL"),
        Path(r"C:\Program Files (x86)\Microsoft Office\root\Office16\OMML2MML.XSL"),
        # Office 2019
        Path(r"C:\Program Files\Microsoft Office\Office16\OMML2MML.XSL"),
        # Office 2016
        Path(r"C:\Program Files\Microsoft Office\Office15\OMML2MML.XSL"),
        # Env var override
    ]
    env_path = os.environ.get("OMML2MML_XSL")
    if env_path:
        candidates.insert(0, Path(env_path))

    for p in candidates:
        if p.exists():
            return p
    return None


def run_preflight() -> PreflightResult:
    """Run all preflight checks and return results."""
    result = PreflightResult()

    # --- Command-line tools ---

    # Pandoc
    pandoc = _check_command("pandoc", ["pandoc"])
    if not pandoc.found:
        pandoc.install_hint = "winget install JohnMacFarlane.Pandoc"
    result.tools.append(pandoc)

    # Tectonic (primary LaTeX compiler)
    tectonic = _check_command("tectonic", ["tectonic"])
    if not tectonic.found:
        tectonic.install_hint = (
            "winget install ArtifexSoftware.Tectonic  OR  "
            "scoop install tectonic  OR  "
            "cargo install tectonic"
        )
    result.tools.append(tectonic)

    # latexmk (fallback compiler driver)
    latexmk = _check_command("latexmk", ["latexmk"])
    if not latexmk.found:
        latexmk.install_hint = (
            "Install TinyTeX: https://yihui.org/tinytex/  OR  "
            "Install MiKTeX: winget install MiKTeX.MiKTeX"
        )
    result.tools.append(latexmk)

    # pdftotext (for character verification in final PDF)
    pdftotext = _check_command("pdftotext", ["pdftotext"])
    if not pdftotext.found:
        pdftotext.install_hint = (
            "Install poppler-utils: scoop install poppler  OR  "
            "conda install -c conda-forge poppler"
        )
    result.tools.append(pdftotext)

    # --- Python packages ---
    result.tools.append(_check_python_package("lxml"))
    docx_status = _check_python_package("docx", import_name="docx")
    docx_status.install_hint = "pip install python-docx"
    result.tools.append(docx_status)
    result.tools.append(_check_python_package("requests"))

    # --- OMML2MML.XSL ---
    xsl_path = _find_omml2mml_xsl()
    result.omml2mml_xsl_path = xsl_path
    result.tools.append(ToolStatus(
        name="OMML2MML.XSL",
        found=xsl_path is not None,
        path=str(xsl_path) if xsl_path else None,
        install_hint=(
            "Set env var OMML2MML_XSL to the path of OMML2MML.XSL, "
            "or install Microsoft Office. The file is typically at: "
            r"C:\Program Files\Microsoft Office\root\Office16\OMML2MML.XSL"
        ) if xsl_path is None else None,
    ))

    # --- Overall status ---
    # Pandoc and at least one compiler are required; OMML2MML.XSL is strongly recommended
    required_tools = {"pandoc"}
    compiler_found = any(
        t.found for t in result.tools if t.name in ("tectonic", "latexmk")
    )
    required_found = all(
        t.found for t in result.tools if t.name in required_tools
    )
    python_found = all(
        t.found for t in result.tools if t.name.startswith("python:")
    )
    result.all_ok = required_found and compiler_found and python_found

    return result


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = run_preflight()
    print(result.summary())
    if not result.all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
