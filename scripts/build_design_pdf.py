"""Build `ai_process_design.pdf` from `ai_process_design.md`.

This is a *documentation build script*, not part of the live BrewFlow AI
backend. It reads the Milestone 04 process-design markdown and emits a
plain-text styled PDF using `fpdf2` (pure Python, no native binaries).

Run it without adding a permanent dependency:

    uv run --with fpdf2 python scripts/build_design_pdf.py

`uv run --with fpdf2` brings `fpdf2` in for this one invocation only;
nothing is written to `pyproject.toml`.

The output is intentionally simple: a clean printable PDF with headings,
paragraphs, and code/table blocks rendered as monospace. The Mermaid
diagram is included as a fenced text block (the PDF doesn't try to
render the diagram visually — readers should view it in the .md file or
via a Mermaid renderer; the .pdf preserves the source for accessibility
and archival).
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from fpdf import FPDF  # provided by `uv run --with fpdf2 ...`
except ImportError as exc:  # pragma: no cover
    sys.exit(
        "fpdf2 is not installed in this Python environment.\n"
        "Run this script via:\n"
        "    uv run --with fpdf2 python scripts/build_design_pdf.py\n"
        f"(import error: {exc})"
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_MD = REPO_ROOT / "ai_process_design.md"
OUTPUT_PDF = REPO_ROOT / "ai_process_design.pdf"

# Page + font settings
PAGE_W_MM = 210
MARGIN_MM = 18
LINE_HEIGHT = 5
BODY_FONT_SIZE = 10
H1_SIZE = 18
H2_SIZE = 14
H3_SIZE = 12
H4_SIZE = 11
MONO_SIZE = 8


def _wrap_long(text: str, max_chars: int) -> list[str]:
    """Hard-split a string into chunks of `max_chars` so fpdf never sees
    a single token wider than the cell. multi_cell can wrap on spaces but
    can't break a long token that has no whitespace (e.g. a Mermaid line).
    """
    if len(text) <= max_chars:
        return [text]
    out: list[str] = []
    while len(text) > max_chars:
        # Prefer to break at the last space within the window for prose;
        # otherwise hard-break.
        cut = text.rfind(" ", 0, max_chars)
        if cut < int(max_chars * 0.4):  # no good word boundary
            cut = max_chars
        out.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        out.append(text)
    return out


def _sanitize(text: str) -> str:
    """fpdf2 with the bundled Helvetica font is latin-1 only; replace
    Unicode glyphs we use in the source with safe ASCII equivalents.
    """
    replacements = {
        "—": "-",
        "–": "-",
        "→": "->",
        "↓": " (down) ",
        "↑": " (up) ",
        "≤": "<=",
        "≥": ">=",
        "•": "*",
        "✓": "[ok]",
        "✅": "[ok]",
        "❌": "[x]",
        "✗": "[x]",
        "⚠": "(!)",
        "⚠️": "(!)",
        "🟢": "[GRN]",
        "🔴": "[RED]",
        "🟣": "[PURP]",
        "🟠": "[ORG]",
        "🔵": "[BLU]",
        "🟡": "[YEL]",
        "☕": "(coffee)",
        "🎯": "[FV]",
        "📄": "[doc]",
        "📝": "[order]",
        "🔍": "[evi]",
        "🧋": "[barista]",
        "🔗": "[full]",
        "👤": "[mgr]",
        "🧊": "[cold]",
        "🥛": "[oat]",
        "🧾": "[audit]",
        "▶": ">",
        "▾": "v",
        "▼": "v",
        "▲": "^",
        "…": "...",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Anything still outside latin-1 — strip it
    return text.encode("latin-1", errors="replace").decode("latin-1")


class DesignPDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return  # Title page renders the header itself
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, "BrewFlow AI - Final Process Redesign", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R")
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "Milestone 04 - Group 8 - MGTA 495 GenAI for Business",
                  align="C")
        self.set_text_color(0, 0, 0)


def render(md_path: Path, pdf_path: Path) -> None:
    md_lines = md_path.read_text(encoding="utf-8").splitlines()

    pdf = DesignPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", H1_SIZE + 4)
    pdf.set_text_color(60, 35, 20)  # coffee brown
    pdf.cell(0, 14, "BrewFlow AI", align="C")
    pdf.ln(14)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "Final Process Redesign  -  Milestone 04", align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Group 8  -  MGTA 495 GenAI for Business",
             align="C")
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)

    in_code_block = False

    for raw_line in md_lines:
        line = _sanitize(raw_line.rstrip())

        # Code-block fence
        if line.lstrip().startswith("```"):
            in_code_block = not in_code_block
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 4, "--- code/diagram block ---" if in_code_block else "--- end block ---")
            pdf.ln(5)
            pdf.set_text_color(0, 0, 0)
            continue

        if in_code_block:
            pdf.set_font("Courier", "", MONO_SIZE)
            for chunk in _wrap_long(line if line else " ", max_chars=110):
                pdf.set_x(MARGIN_MM); pdf.multi_cell(174, 4, chunk)
            continue

        # Headings
        if line.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", H1_SIZE)
            pdf.set_text_color(60, 35, 20)
            pdf.set_x(MARGIN_MM); pdf.multi_cell(174, 8, line[2:])
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
            continue
        if line.startswith("## "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", H2_SIZE)
            pdf.set_text_color(80, 50, 30)
            pdf.set_x(MARGIN_MM); pdf.multi_cell(174, 7, line[3:])
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
            continue
        if line.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", H3_SIZE)
            pdf.set_x(MARGIN_MM); pdf.multi_cell(174, 6, line[4:])
            pdf.ln(1)
            continue
        if line.startswith("#### "):
            pdf.set_font("Helvetica", "B", H4_SIZE)
            pdf.set_x(MARGIN_MM); pdf.multi_cell(174, 6, line[5:])
            continue

        # Horizontal rule
        if line.strip() in ("---", "***", "___"):
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            y = pdf.get_y()
            pdf.line(MARGIN_MM, y, PAGE_W_MM - MARGIN_MM, y)
            pdf.ln(3)
            continue

        # Blank line
        if not line.strip():
            pdf.ln(3)
            continue

        # Table rows -> mono-spaced
        if line.lstrip().startswith("|"):
            pdf.set_font("Courier", "", MONO_SIZE)
            for chunk in _wrap_long(line, max_chars=130):
                pdf.set_x(MARGIN_MM); pdf.multi_cell(174, 4, chunk)
            continue

        # Bullet list
        if line.lstrip().startswith(("- ", "* ")):
            pdf.set_font("Helvetica", "", BODY_FONT_SIZE)
            for chunk in _wrap_long("  - " + line.lstrip()[2:], max_chars=75):
                pdf.set_x(MARGIN_MM); pdf.multi_cell(174, LINE_HEIGHT, chunk)
            continue

        # Numbered list
        stripped = line.lstrip()
        if stripped[:2].isdigit() and stripped[2:3] == ". ":
            pdf.set_font("Helvetica", "", BODY_FONT_SIZE)
            for chunk in _wrap_long("  " + stripped, max_chars=75):
                pdf.set_x(MARGIN_MM); pdf.multi_cell(174, LINE_HEIGHT, chunk)
            continue

        # Block quote
        if line.lstrip().startswith("> "):
            pdf.set_font("Helvetica", "I", BODY_FONT_SIZE)
            pdf.set_text_color(80, 80, 80)
            for chunk in _wrap_long("    " + line.lstrip()[2:], max_chars=75):
                pdf.set_x(MARGIN_MM); pdf.multi_cell(174, LINE_HEIGHT, chunk)
            pdf.set_text_color(0, 0, 0)
            continue

        # Plain paragraph
        pdf.set_font("Helvetica", "", BODY_FONT_SIZE)
        for chunk in _wrap_long(line, max_chars=75):
            pdf.set_x(MARGIN_MM); pdf.multi_cell(174, LINE_HEIGHT, chunk)

    pdf.output(str(pdf_path))


def main() -> int:
    if not INPUT_MD.exists():
        sys.exit(f"Missing input: {INPUT_MD}")
    render(INPUT_MD, OUTPUT_PDF)
    size_kb = OUTPUT_PDF.stat().st_size / 1024
    print(f"OK: wrote {OUTPUT_PDF.relative_to(REPO_ROOT)}  ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
