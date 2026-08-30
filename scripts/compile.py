"""
paper2tex: compile — Automated LaTeX compile-fix loop.

Compiles .tex files using tectonic (primary) or latexmk (fallback).
Parses .log files, classifies errors, applies deterministic fixes,
and recompiles up to a configurable maximum iterations.

NEVER auto-fixes content — only markup. Content-level problems get
a TODO comment + report entry.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
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


class ErrorCategory(Enum):
    """Categories of LaTeX compilation errors."""
    UNDEFINED_COMMAND = "undefined_command"
    MISSING_PACKAGE = "missing_package"
    CITATION_UNDEFINED = "citation_undefined"
    REFERENCE_UNDEFINED = "reference_undefined"
    MISSING_DOLLAR = "missing_dollar"
    ILLEGAL_PARAM = "illegal_parameter"
    BRACE_MISMATCH = "brace_mismatch"
    ENVIRONMENT_UNDEFINED = "environment_undefined"
    FILE_NOT_FOUND_STY = "file_not_found_sty"
    DIMENSION_TOO_LARGE = "dimension_too_large"
    IMAGE_NOT_FOUND = "image_not_found"
    OPTION_CLASH = "option_clash"
    FONT_NOT_AVAILABLE = "font_not_available"
    OVERFULL_HBOX = "overfull_hbox"
    UNKNOWN = "unknown"


@dataclass
class CompileError:
    """A single classified compilation error."""
    category: ErrorCategory
    message: str
    file: str = ""
    line: int = 0
    context: str = ""          # Surrounding lines from .tex
    auto_fixable: bool = False
    fix_description: str = ""
    fix_applied: bool = False


@dataclass
class CompileResult:
    """Result of the compile-fix loop."""
    success: bool = False
    pdf_path: Path | None = None
    iterations: int = 0
    errors: list[CompileError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    engine_used: str = ""
    log_path: Path | None = None

    def summary(self) -> str:
        status = "✅ Success" if self.success else "❌ Failed"
        lines = [
            f"Compilation: {status}",
            f"Engine: {self.engine_used}",
            f"Iterations: {self.iterations}",
        ]
        if self.errors:
            lines.append(f"Errors remaining: {len(self.errors)}")
            for e in self.errors[:5]:
                lines.append(f"  - [{e.category.value}] {e.message}")
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
        return "\n".join(lines)


# --- Error Classification (14-row table) ---

ERROR_PATTERNS: list[tuple[str, ErrorCategory, bool, str]] = [
    # (regex_pattern, category, auto_fixable, fix_template)
    (
        r"Undefined control sequence.*\\(\w+)",
        ErrorCategory.UNDEFINED_COMMAND,
        True,
        "Add missing package or define command",
    ),
    (
        r"Package (\S+) Not found|File `(\S+\.sty)' not found",
        ErrorCategory.MISSING_PACKAGE,
        True,
        "Install missing package",
    ),
    (
        r"Citation `([^']+)' .* undefined|Warning:.*Citation.*`([^']+)'.*undefined",
        ErrorCategory.CITATION_UNDEFINED,
        True,
        "Fix citation key mismatch",
    ),
    (
        r"Reference `([^']+)' .* undefined|Warning:.*Reference.*`([^']+)'.*undefined",
        ErrorCategory.REFERENCE_UNDEFINED,
        True,
        "Add missing \\label{}",
    ),
    (
        r"Missing \$ inserted",
        ErrorCategory.MISSING_DOLLAR,
        True,
        "Escape special character (_, %, &, #) or wrap in math mode",
    ),
    (
        r"Illegal parameter number in definition",
        ErrorCategory.ILLEGAL_PARAM,
        True,
        "Escape # as \\#",
    ),
    (
        r"Extra }, or forgotten }|Missing } inserted|Extra {",
        ErrorCategory.BRACE_MISMATCH,
        False,
        "Fix brace mismatch (requires manual review)",
    ),
    (
        r"Environment (\w+) undefined",
        ErrorCategory.ENVIRONMENT_UNDEFINED,
        True,
        "Add required package (amsmath, algorithm, etc.)",
    ),
    (
        r"File `([^']+\.sty)' not found",
        ErrorCategory.FILE_NOT_FOUND_STY,
        True,
        "Install package via tectonic/tlmgr",
    ),
    (
        r"Dimension too large",
        ErrorCategory.DIMENSION_TOO_LARGE,
        True,
        "Add [width=\\textwidth] to \\includegraphics",
    ),
    (
        r"cannot find image file|File `([^']+\.\w{3,4})' not found|I can't find file",
        ErrorCategory.IMAGE_NOT_FOUND,
        True,
        "Fix \\includegraphics path",
    ),
    (
        r"Option clash for package (\w+)",
        ErrorCategory.OPTION_CLASH,
        True,
        "Remove duplicate package load",
    ),
    (
        r"Font .* not (?:found|available)|Cannot determine size of graphic",
        ErrorCategory.FONT_NOT_AVAILABLE,
        True,
        "Add \\usepackage{fontspec} for xelatex",
    ),
    (
        r"Overfull \\hbox",
        ErrorCategory.OVERFULL_HBOX,
        False,
        "Content too wide — warn only, don't auto-fix",
    ),
]

# Known command → package mappings for auto-fix
COMMAND_PACKAGE_MAP = {
    "\\multirow": "multirow",
    "\\toprule": "booktabs",
    "\\midrule": "booktabs",
    "\\bottomrule": "booktabs",
    "\\cref": "cleveref",
    "\\Cref": "cleveref",
    "\\eqref": "amsmath",
    "\\align": "amsmath",
    "\\SI": "siunitx",
    "\\si": "siunitx",
    "\\textdegree": "textcomp",
    "\\textmu": "textcomp",
    "\\url": "url",
    "\\href": "hyperref",
    "\\includegraphics": "graphicx",
    "\\subfigure": "subcaption",
    "\\lstlisting": "listings",
}

# Environment → package mappings
ENVIRONMENT_PACKAGE_MAP = {
    "align": "amsmath",
    "align*": "amsmath",
    "equation": "amsmath",
    "equation*": "amsmath",
    "gather": "amsmath",
    "cases": "amsmath",
    "bmatrix": "amsmath",
    "pmatrix": "amsmath",
    "algorithm": "algorithm",
    "algorithmic": "algorithmicx",
    "lstlisting": "listings",
    "minted": "minted",
    "subfigure": "subcaption",
}


def _classify_errors(log_content: str) -> list[CompileError]:
    """Parse a LaTeX .log file and classify errors."""
    errors: list[CompileError] = []
    seen: set[str] = set()  # Deduplicate

    for line in log_content.split("\n"):
        for pattern, category, auto_fixable, fix_desc in ERROR_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                msg = line.strip()[:200]
                dedup_key = f"{category.value}:{match.group()}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    # Try to extract file and line number
                    loc_match = re.match(r"([^:]+):(\d+):", line)
                    errors.append(CompileError(
                        category=category,
                        message=msg,
                        file=loc_match.group(1) if loc_match else "",
                        line=int(loc_match.group(2)) if loc_match else 0,
                        auto_fixable=auto_fixable,
                        fix_description=fix_desc,
                    ))
                break

    return errors


def _apply_fixes(
    tex_path: Path,
    errors: list[CompileError],
) -> list[CompileError]:
    """Apply deterministic fixes to the .tex file for auto-fixable errors.

    Returns the list of errors that were successfully fixed.
    """
    content = tex_path.read_text(encoding="utf-8")
    fixed: list[CompileError] = []
    packages_to_add: set[str] = set()

    for error in errors:
        if not error.auto_fixable:
            continue

        if error.category == ErrorCategory.UNDEFINED_COMMAND:
            # Find which package provides this command
            cmd_match = re.search(r"\\(\w+)", error.message)
            if cmd_match:
                cmd = f"\\{cmd_match.group(1)}"
                if cmd in COMMAND_PACKAGE_MAP:
                    pkg = COMMAND_PACKAGE_MAP[cmd]
                    if f"\\usepackage{{{pkg}}}" not in content:
                        packages_to_add.add(pkg)
                        error.fix_applied = True
                        fixed.append(error)

        elif error.category == ErrorCategory.ENVIRONMENT_UNDEFINED:
            env_match = re.search(r"Environment (\w+)", error.message)
            if env_match:
                env = env_match.group(1)
                if env in ENVIRONMENT_PACKAGE_MAP:
                    pkg = ENVIRONMENT_PACKAGE_MAP[env]
                    if f"\\usepackage{{{pkg}}}" not in content:
                        packages_to_add.add(pkg)
                        error.fix_applied = True
                        fixed.append(error)

        elif error.category == ErrorCategory.MISSING_DOLLAR:
            # Find unescaped _ in text mode and escape them
            # This is a conservative fix: only escape _ outside math mode
            # Simple heuristic: look for lines with bare _ not in $ ... $
            if error.line > 0:
                lines = content.split("\n")
                if error.line <= len(lines):
                    line = lines[error.line - 1]
                    # Escape _ that's not already escaped and not in math
                    new_line = _escape_special_chars_in_line(line)
                    if new_line != line:
                        lines[error.line - 1] = new_line
                        content = "\n".join(lines)
                        error.fix_applied = True
                        fixed.append(error)

        elif error.category == ErrorCategory.ILLEGAL_PARAM:
            if error.line > 0:
                lines = content.split("\n")
                if error.line <= len(lines):
                    line = lines[error.line - 1]
                    # Escape bare # that's not \#
                    new_line = re.sub(r"(?<!\\)#(?!\d)", r"\\#", line)
                    if new_line != line:
                        lines[error.line - 1] = new_line
                        content = "\n".join(lines)
                        error.fix_applied = True
                        fixed.append(error)

        elif error.category == ErrorCategory.OPTION_CLASH:
            pkg_match = re.search(r"package (\w+)", error.message)
            if pkg_match:
                pkg = pkg_match.group(1)
                # Remove duplicate \usepackage lines (keep the first)
                lines = content.split("\n")
                found_first = False
                new_lines = []
                for line in lines:
                    if f"\\usepackage" in line and pkg in line:
                        if not found_first:
                            found_first = True
                            new_lines.append(line)
                        else:
                            # Comment out duplicate
                            new_lines.append(f"% REMOVED duplicate: {line}")
                            error.fix_applied = True
                            fixed.append(error)
                    else:
                        new_lines.append(line)
                content = "\n".join(new_lines)

        elif error.category == ErrorCategory.DIMENSION_TOO_LARGE:
            # Add width constraint to \includegraphics without one
            content = re.sub(
                r"\\includegraphics\{",
                r"\\includegraphics[width=\\textwidth]{",
                content,
                count=1,
            )
            error.fix_applied = True
            fixed.append(error)

    # Insert missing packages into preamble
    if packages_to_add:
        pkg_lines = "\n".join(f"\\usepackage{{{p}}}" for p in sorted(packages_to_add))
        # Insert after \documentclass line
        content = re.sub(
            r"(\\documentclass[^\n]*\n)",
            rf"\1{pkg_lines}\n",
            content,
            count=1,
        )
        log.info("Added packages: %s", ", ".join(sorted(packages_to_add)))

    tex_path.write_text(content, encoding="utf-8", newline="\n")
    return fixed


def _escape_special_chars_in_line(line: str) -> str:
    """Escape special LaTeX characters in a text line.

    Only escapes characters that appear outside of math mode and commands.
    Conservative: only handles _ and & which are the most common culprits.
    """
    # Skip lines that are comments, commands, or math
    stripped = line.strip()
    if stripped.startswith("%") or stripped.startswith("\\"):
        return line

    # Simple check: if line contains $, don't touch it (math mode present)
    if "$" in line:
        return line

    # Escape bare _ (not preceded by \)
    result = re.sub(r"(?<!\\)_(?!{)", r"\\_", line)
    # Escape bare & (not preceded by \, and not in tabular context)
    # Skip this for tabular lines (they legitimately use &)
    if "\\begin{tabular}" not in line and "&" in result:
        # Only escape if it doesn't look like a tabular separator
        if result.count("&") <= 1:  # Tabular rows typically have multiple &
            result = re.sub(r"(?<!\\)&", r"\\&", result)

    return result


def _run_compiler(
    tex_path: Path,
    engine: str = "tectonic",
    timeout: int = 120,
) -> tuple[bool, str, Path | None]:
    """Run a LaTeX compiler and return (success, log_content, pdf_path).

    Args:
        tex_path: Path to the .tex file
        engine: "tectonic" or "latexmk"
        timeout: Max seconds to wait

    Returns:
        (success, log_content, pdf_path_or_None)
    """
    work_dir = tex_path.parent
    stem = tex_path.stem

    if engine == "tectonic":
        exe = shutil.which("tectonic")
        if not exe:
            return False, "tectonic not found", None
        cmd = [exe, str(tex_path), "--keep-logs"]
    elif engine == "latexmk":
        exe = shutil.which("latexmk")
        if not exe:
            return False, "latexmk not found", None
        cmd = [
            exe, "-xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            str(tex_path),
        ]
    else:
        return False, f"Unknown engine: {engine}", None

    env = os.environ.copy()
    env["TEXINPUTS"] = f".{os.pathsep}{work_dir}{os.pathsep}"

    try:
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out", None
    except FileNotFoundError:
        return False, f"{engine} not found on PATH", None

    # Read log file
    log_path = work_dir / f"{stem}.log"
    log_content = ""
    if log_path.exists():
        try:
            log_content = log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            log_content = result.stdout + "\n" + result.stderr

    # Check for PDF
    pdf_path = work_dir / f"{stem}.pdf"
    success = pdf_path.exists() and result.returncode == 0

    return success, log_content, pdf_path if pdf_path.exists() else None


def compile_latex(
    tex_path: Path,
    max_iterations: int = 10,
    preferred_engine: str = "tectonic",
) -> CompileResult:
    """Run the compile-fix loop.

    Args:
        tex_path: Path to the main .tex file
        max_iterations: Maximum fix-recompile cycles
        preferred_engine: "tectonic" or "latexmk"

    Returns:
        CompileResult with success status, errors, and PDF path
    """
    result = CompileResult()

    # Determine engine order
    engines = [preferred_engine]
    if preferred_engine == "tectonic":
        engines.append("latexmk")
    else:
        engines.append("tectonic")

    engine_used = None
    for engine in engines:
        if shutil.which(engine):
            engine_used = engine
            break

    if engine_used is None:
        result.errors.append(CompileError(
            category=ErrorCategory.UNKNOWN,
            message="No LaTeX compiler found (need tectonic or latexmk)",
        ))
        return result

    result.engine_used = engine_used
    log.info("Using compiler: %s", engine_used)

    for iteration in range(1, max_iterations + 1):
        result.iterations = iteration
        log.info("Compile iteration %d / %d", iteration, max_iterations)

        success, log_content, pdf_path = _run_compiler(tex_path, engine_used)

        if success:
            # Check for remaining warnings
            result.success = True
            result.pdf_path = pdf_path
            result.log_path = tex_path.parent / f"{tex_path.stem}.log"

            # Still classify warnings
            errors = _classify_errors(log_content)
            result.warnings = [
                e.message for e in errors
                if e.category == ErrorCategory.OVERFULL_HBOX
            ]
            # Check for citation/reference warnings (PDF exists but has [?])
            cite_errors = [
                e for e in errors
                if e.category in (
                    ErrorCategory.CITATION_UNDEFINED,
                    ErrorCategory.REFERENCE_UNDEFINED,
                )
            ]
            if cite_errors:
                result.warnings.extend(e.message for e in cite_errors)

            log.info("Compilation succeeded on iteration %d", iteration)
            return result

        # Classify errors
        errors = _classify_errors(log_content)
        if not errors:
            # Compilation failed but no classifiable errors — unknown issue
            result.errors = [CompileError(
                category=ErrorCategory.UNKNOWN,
                message="Compilation failed with unclassifiable errors. Check log.",
            )]
            result.log_path = tex_path.parent / f"{tex_path.stem}.log"
            log.warning("Compilation failed with unclassifiable errors")
            return result

        # Try to apply fixes
        fixed = _apply_fixes(tex_path, errors)
        if not fixed:
            # No fixes could be applied — loop would be infinite
            result.errors = [e for e in errors if not e.fix_applied]
            result.log_path = tex_path.parent / f"{tex_path.stem}.log"
            log.warning(
                "Cannot auto-fix remaining %d errors — stopping",
                len(result.errors),
            )
            return result

        log.info("Applied %d fixes, recompiling...", len(fixed))

    # Exhausted iterations
    result.errors = _classify_errors(
        (tex_path.parent / f"{tex_path.stem}.log").read_text(
            encoding="utf-8", errors="replace"
        ) if (tex_path.parent / f"{tex_path.stem}.log").exists() else ""
    )
    log.warning("Exhausted %d iterations without clean compilation", max_iterations)
    return result


def main() -> None:
    """CLI entry point."""
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python compile.py <main.tex> [--engine tectonic|latexmk] [--max-iter N]")
        sys.exit(1)

    tex_path = Path(sys.argv[1])
    engine = "tectonic"
    max_iter = 10

    if "--engine" in sys.argv:
        idx = sys.argv.index("--engine")
        if idx + 1 < len(sys.argv):
            engine = sys.argv[idx + 1]

    if "--max-iter" in sys.argv:
        idx = sys.argv.index("--max-iter")
        if idx + 1 < len(sys.argv):
            max_iter = int(sys.argv[idx + 1])

    result = compile_latex(tex_path, max_iterations=max_iter, preferred_engine=engine)
    print(result.summary())
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
