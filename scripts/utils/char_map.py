"""
paper2tex: special character mapping utilities.

Maps Unicode special characters to their LaTeX equivalents.
Handles the context-dependent decision: math mode vs text mode.
"""

from __future__ import annotations

# Characters that need math mode ($...$)
MATH_CHAR_MAP: dict[str, str] = {
    "≈": r"\approx",
    "≠": r"\neq",
    "≤": r"\leq",
    "≥": r"\geq",
    "±": r"\pm",
    "×": r"\times",
    "÷": r"\div",
    "·": r"\cdot",
    "∞": r"\infty",
    "∑": r"\sum",
    "∏": r"\prod",
    "∫": r"\int",
    "∂": r"\partial",
    "∇": r"\nabla",
    "√": r"\sqrt{}",
    "∝": r"\propto",
    "∈": r"\in",
    "∉": r"\notin",
    "⊂": r"\subset",
    "⊃": r"\supset",
    "∪": r"\cup",
    "∩": r"\cap",
    "∅": r"\emptyset",
    "∀": r"\forall",
    "∃": r"\exists",
    "→": r"\rightarrow",
    "←": r"\leftarrow",
    "↔": r"\leftrightarrow",
    "⇒": r"\Rightarrow",
    "⇐": r"\Leftarrow",
    "⇔": r"\Leftrightarrow",
    "↑": r"\uparrow",
    "↓": r"\downarrow",
    "′": r"'",
    "″": r"''",
    "‖": r"\|",
    "∥": r"\parallel",
    "⊥": r"\perp",
    "∧": r"\wedge",
    "∨": r"\vee",
    "¬": r"\neg",
    "⊗": r"\otimes",
    "⊕": r"\oplus",
    "†": r"\dagger",
    "‡": r"\ddagger",
    "ℓ": r"\ell",
    "ℝ": r"\mathbb{R}",
    "ℤ": r"\mathbb{Z}",
    "ℕ": r"\mathbb{N}",
    "ℂ": r"\mathbb{C}",
}

# Characters that work in text mode (with appropriate packages)
TEXT_CHAR_MAP: dict[str, str] = {
    "°": r"\textdegree{}",
    "µ": r"\textmu{}",
    "®": r"\textregistered{}",
    "©": r"\textcopyright{}",
    "™": r"\texttrademark{}",
    "§": r"\S{}",
    "¶": r"\P{}",
    "£": r"\pounds{}",
    "€": r"\texteuro{}",
    "¥": r"\textyen{}",
    "—": "---",          # em dash
    "–": "--",            # en dash
    "\u201c": "``",       # left double quote "
    "\u201d": "''",       # right double quote "
    "\u2018": "`",        # left single quote '
    "\u2019": "'",        # right single quote '
    "…": r"\ldots{}",
    "•": r"\textbullet{}",
    "‰": r"\textperthousand{}",
    "fi": "fi",           # fi ligature (let LaTeX handle)
    "fl": "fl",           # fl ligature
}

# Greek letters: can appear in both text and math mode
# In text mode, use textgreek package commands
# In math mode, use standard \alpha, \beta, etc.
GREEK_TEXT_MAP: dict[str, str] = {
    "α": r"\textalpha{}",
    "β": r"\textbeta{}",
    "γ": r"\textgamma{}",
    "δ": r"\textdelta{}",
    "ε": r"\textepsilon{}",
    "ζ": r"\textzeta{}",
    "η": r"\texteta{}",
    "θ": r"\texttheta{}",
    "ι": r"\textiota{}",
    "κ": r"\textkappa{}",
    "λ": r"\textlambda{}",
    "μ": r"\textmu{}",
    "ν": r"\textnu{}",
    "ξ": r"\textxi{}",
    "π": r"\textpi{}",
    "ρ": r"\textrho{}",
    "σ": r"\textsigma{}",
    "τ": r"\texttau{}",
    "υ": r"\textupsilon{}",
    "φ": r"\textphi{}",
    "χ": r"\textchi{}",
    "ψ": r"\textpsi{}",
    "ω": r"\textomega{}",
    "Α": "A",  # Capital alpha is just A in LaTeX
    "Β": "B",
    "Γ": r"\textGamma{}",
    "Δ": r"\textDelta{}",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Θ": r"\textTheta{}",
    "Ι": "I",
    "Κ": "K",
    "Λ": r"\textLambda{}",
    "Μ": "M",
    "Ν": "N",
    "Ξ": r"\textXi{}",
    "Π": r"\textPi{}",
    "Ρ": "P",
    "Σ": r"\textSigma{}",
    "Τ": "T",
    "Υ": r"\textUpsilon{}",
    "Φ": r"\textPhi{}",
    "Χ": "X",
    "Ψ": r"\textPsi{}",
    "Ω": r"\textOmega{}",
}

GREEK_MATH_MAP: dict[str, str] = {
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\varepsilon",
    "ζ": r"\zeta",
    "η": r"\eta",
    "θ": r"\theta",
    "ι": r"\iota",
    "κ": r"\kappa",
    "λ": r"\lambda",
    "μ": r"\mu",
    "ν": r"\nu",
    "ξ": r"\xi",
    "π": r"\pi",
    "ρ": r"\rho",
    "σ": r"\sigma",
    "τ": r"\tau",
    "υ": r"\upsilon",
    "φ": r"\varphi",
    "χ": r"\chi",
    "ψ": r"\psi",
    "ω": r"\omega",
    "Γ": r"\Gamma",
    "Δ": r"\Delta",
    "Θ": r"\Theta",
    "Λ": r"\Lambda",
    "Ξ": r"\Xi",
    "Π": r"\Pi",
    "Σ": r"\Sigma",
    "Υ": r"\Upsilon",
    "Φ": r"\Phi",
    "Ψ": r"\Psi",
    "Ω": r"\Omega",
}

# Unicode subscript/superscript digits → LaTeX math
SUBSCRIPT_MAP: dict[str, str] = {
    "₀": "_0", "₁": "_1", "₂": "_2", "₃": "_3", "₄": "_4",
    "₅": "_5", "₆": "_6", "₇": "_7", "₈": "_8", "₉": "_9",
    "₊": "_{+}", "₋": "_{-}", "₌": "_{=}",
    "ₐ": "_a", "ₑ": "_e", "ₒ": "_o", "ₓ": "_x",
    "ₙ": "_n", "ₘ": "_m", "ₚ": "_p", "ₛ": "_s", "ₜ": "_t",
}

SUPERSCRIPT_MAP: dict[str, str] = {
    "⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4",
    "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9",
    "⁺": "^{+}", "⁻": "^{-}", "⁼": "^{=}",
    "ⁿ": "^n",
}

# Characters that must be escaped in LaTeX text mode
ESCAPE_CHARS: dict[str, str] = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}


def detect_special_chars(text: str) -> dict[str, int]:
    """Detect and count all special characters in text.

    Returns: {character: count}
    """
    all_special = set()
    all_special.update(MATH_CHAR_MAP.keys())
    all_special.update(TEXT_CHAR_MAP.keys())
    all_special.update(GREEK_TEXT_MAP.keys())
    all_special.update(SUBSCRIPT_MAP.keys())
    all_special.update(SUPERSCRIPT_MAP.keys())

    found: dict[str, int] = {}
    for char in all_special:
        count = text.count(char)
        if count > 0:
            found[char] = count

    return found


def get_required_packages(chars: dict[str, int]) -> set[str]:
    """Determine which LaTeX packages are needed for the detected characters."""
    packages: set[str] = set()

    for char in chars:
        if char in TEXT_CHAR_MAP:
            cmd = TEXT_CHAR_MAP[char]
            if "textdegree" in cmd or "textmu" in cmd:
                packages.add("textcomp")
            if "texteuro" in cmd:
                packages.add("eurosym")
        if char in GREEK_TEXT_MAP:
            packages.add("textgreek")
        if char in SUBSCRIPT_MAP or char in SUPERSCRIPT_MAP:
            pass  # These go in math mode, no extra package needed
        if char in MATH_CHAR_MAP:
            cmd = MATH_CHAR_MAP[char]
            if "mathbb" in cmd:
                packages.add("amssymb")

    return packages
