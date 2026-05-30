"""Build `BrewFlow_AI_Project_Guide.docx` from the matching markdown file.

This is a *documentation build script*, not part of the live BrewFlow AI
backend. It reads the teammate guide markdown and emits a formatted Word
document using `python-docx` (pure Python, no native binaries).

Run it without adding a permanent dependency:

    uv run --with python-docx python scripts/build_guide_docx.py

`uv run --with python-docx` pulls `python-docx` in for this one
invocation only; nothing is written to `pyproject.toml`.

The converter handles:
  * `#`/`##`/`###`/`####` headings -> Word heading styles
  * `- ` / `* ` bullet lists -> Word List Bullet style
  * `1. ` / `2. ` ... numbered lists -> Word List Number style
  * Pipe-delimited markdown tables -> real Word tables
  * Fenced ```code``` blocks -> mono-spaced normal paragraphs
  * `> ` blockquotes -> indented italics
  * Inline `**bold**`, `*italic*`, and `` `code` `` runs

It does *not* attempt to render the project's text-flow ASCII diagram
fancily; that is preserved verbatim inside a monospace block.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError as exc:  # pragma: no cover
    sys.exit(
        "python-docx is not installed in this Python environment.\n"
        "Run this script via:\n"
        "    uv run --with python-docx python scripts/build_guide_docx.py\n"
        f"(import error: {exc})"
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_MD = REPO_ROOT / "BrewFlow_AI_Project_Guide.md"
OUTPUT_DOCX = REPO_ROOT / "BrewFlow_AI_Project_Guide.docx"

INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
INLINE_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
INLINE_CODE = re.compile(r"`([^`]+)`")

COFFEE_BROWN = RGBColor(0x4B, 0x2E, 0x1F)


def add_runs(paragraph, text: str, *, italic: bool = False) -> None:
    """Add text to a paragraph, splitting on inline **bold**, *italic*, `code`."""
    # Walk through the string, emitting a run for each inline token.
    pos = 0
    pattern = re.compile(
        r"(\*\*([^*]+)\*\*|`([^`]+)`|\*([^*]+)\*)"
    )
    for m in pattern.finditer(text):
        start, end = m.span()
        if start > pos:
            run = paragraph.add_run(text[pos:start])
            if italic:
                run.italic = True
        if m.group(2) is not None:        # **bold**
            r = paragraph.add_run(m.group(2))
            r.bold = True
            if italic:
                r.italic = True
        elif m.group(3) is not None:      # `code`
            r = paragraph.add_run(m.group(3))
            r.font.name = "Consolas"
            r.font.size = Pt(9)
        elif m.group(4) is not None:      # *italic*
            r = paragraph.add_run(m.group(4))
            r.italic = True
        pos = end
    if pos < len(text):
        r = paragraph.add_run(text[pos:])
        if italic:
            r.italic = True


def set_table_border(table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{border_name}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:color"), "BFBFBF")
        tblBorders.append(b)
    tblPr.append(tblBorders)


def add_table(doc, rows: list[list[str]]) -> None:
    """Render a list-of-rows as a real Word table."""
    if not rows:
        return
    # Drop the separator row (--- | --- ...) if present (second row)
    if len(rows) >= 2 and all(set(c.strip()) <= set("-: ") for c in rows[1]):
        rows = [rows[0]] + rows[2:]
    n_cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=n_cols)
    table.style = "Light Grid Accent 1"
    set_table_border(table)
    for i, row in enumerate(rows):
        for j in range(n_cols):
            cell = table.rows[i].cells[j]
            txt = row[j] if j < len(row) else ""
            cell.text = ""  # clear default paragraph
            p = cell.paragraphs[0]
            add_runs(p, txt)
            if i == 0:
                # header row bold + brown
                for r in p.runs:
                    r.bold = True
                    r.font.color.rgb = COFFEE_BROWN
    doc.add_paragraph()  # spacing after table


def render(md_path: Path, docx_path: Path) -> None:
    doc = Document()

    # ---- Document styles
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    for style_name, size, bold, color in [
        ("Heading 1", 22, True, COFFEE_BROWN),
        ("Heading 2", 16, True, COFFEE_BROWN),
        ("Heading 3", 13, True, RGBColor(0x2B, 0x18, 0x10)),
        ("Heading 4", 12, True, RGBColor(0x40, 0x40, 0x40)),
    ]:
        s = styles[style_name]
        s.font.name = "Calibri"
        s.font.size = Pt(size)
        s.font.bold = bold
        if color:
            s.font.color.rgb = color

    # ---- Front matter
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("BrewFlow AI")
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = COFFEE_BROWN

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = subtitle.add_run("Teammate Project Guide")
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor(0x50, 0x50, 0x50)

    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = note.add_run("Milestone 04  -  Group 8  -  MGTA 495 GenAI for Business")
    r.italic = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

    doc.add_paragraph()  # spacer

    # ---- Walk the markdown
    md_lines = md_path.read_text(encoding="utf-8").splitlines()

    in_code = False
    code_buf: list[str] = []
    table_buf: list[list[str]] = []

    def flush_code():
        nonlocal code_buf
        if code_buf:
            p = doc.add_paragraph()
            for line in code_buf:
                run = p.add_run(line + "\n")
                run.font.name = "Consolas"
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
            code_buf = []

    def flush_table():
        nonlocal table_buf
        if table_buf:
            add_table(doc, table_buf)
            table_buf = []

    i = 0
    while i < len(md_lines):
        raw = md_lines[i].rstrip()
        line = raw

        # Code fence toggle
        if line.lstrip().startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_table()
                in_code = True
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Table row
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_buf.append(cells)
            i += 1
            continue
        else:
            flush_table()

        # Headings
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
            i += 1
            continue
        if line.startswith("## "):
            doc.add_heading(line[3:], level=2)
            i += 1
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:], level=3)
            i += 1
            continue
        if line.startswith("#### "):
            doc.add_heading(line[5:], level=4)
            i += 1
            continue

        # Horizontal rule
        if line.strip() in ("---", "***", "___"):
            p = doc.add_paragraph()
            r = p.add_run("─" * 50)
            r.font.color.rgb = RGBColor(0xC0, 0xC0, 0xC0)
            i += 1
            continue

        # Blank line
        if not line.strip():
            doc.add_paragraph()
            i += 1
            continue

        # Bullet list
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ")):
            p = doc.add_paragraph(style="List Bullet")
            add_runs(p, stripped[2:])
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Number")
            add_runs(p, m.group(2))
            i += 1
            continue

        # Block quote
        if stripped.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            add_runs(p, stripped[2:], italic=True)
            i += 1
            continue

        # Plain paragraph
        p = doc.add_paragraph()
        add_runs(p, line)
        i += 1

    flush_code()
    flush_table()

    doc.save(str(docx_path))


def main() -> int:
    if not INPUT_MD.exists():
        sys.exit(f"Missing input: {INPUT_MD}")
    render(INPUT_MD, OUTPUT_DOCX)
    size_kb = OUTPUT_DOCX.stat().st_size / 1024
    print(f"OK: wrote {OUTPUT_DOCX.relative_to(REPO_ROOT)}  ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
