from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, Preformatted, SimpleDocTemplate, Spacer


base_dir = Path(__file__).resolve().parent
md_path = base_dir / "solution.md"
pdf_path = base_dir / "solution.pdf"

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleCenter",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        leading=26,
        spaceAfter=16,
    )
)
styles.add(
    ParagraphStyle(
        name="Section",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="SubSection",
        parent=styles["Heading3"],
        fontSize=12,
        leading=15,
        spaceBefore=8,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="CustomBullet",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
        leftIndent=18,
        bulletIndent=12,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="CodeBlock",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=8.5,
        leading=10.5,
        leftIndent=8,
        rightIndent=8,
        borderPadding=6,
        borderColor=colors.lightgrey,
        borderWidth=0.5,
        borderRadius=2,
        backColor=colors.whitesmoke,
        spaceAfter=8,
        spaceBefore=4,
    )
)


def _render_mermaid_to_png(mermaid_code: str, output_path: Path) -> bool:
    """Render Mermaid diagram using Kroki API. Returns True on success."""
    request = Request(
        "https://kroki.io/mermaid/png",
        data=mermaid_code.encode("utf-8"),
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "image/png",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            image_bytes = response.read()
        output_path.write_bytes(image_bytes)
        return True
    except (URLError, TimeoutError, OSError):
        return False


story = []
in_code_block = False
code_block_lang = ""
code_block_lines = []
diagram_counter = 0


def flush_code_block() -> None:
    global diagram_counter
    if not code_block_lines:
        return

    code_text = "\n".join(code_block_lines)
    if code_block_lang.lower() == "mermaid":
        diagram_counter_local = len(list(base_dir.glob("_diagram_*.png"))) + 1
        image_path = base_dir / f"_diagram_{diagram_counter_local}.png"
        if _render_mermaid_to_png(code_text, image_path):
            story.append(Paragraph("Flow Diagram", styles["SubSection"]))
            diagram = Image(str(image_path))
            max_width = A4[0] - (0.7 * inch * 2)
            if diagram.drawWidth > max_width:
                ratio = max_width / diagram.drawWidth
                diagram.drawWidth *= ratio
                diagram.drawHeight *= ratio
            story.append(diagram)
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("Flow Diagram (text fallback)", styles["SubSection"]))
            story.append(Preformatted(code_text, styles["CodeBlock"]))
    else:
        story.append(Preformatted(code_text, styles["CodeBlock"]))


for raw_line in md_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.rstrip("\n")

    if line.startswith("```"):
        if not in_code_block:
            in_code_block = True
            code_block_lang = line[3:].strip()
            code_block_lines = []
        else:
            in_code_block = False
            flush_code_block()
            code_block_lang = ""
            code_block_lines = []
        continue

    if in_code_block:
        code_block_lines.append(line)
        continue

    if not line.strip():
        story.append(Spacer(1, 8))
        continue

    if line.startswith("# "):
        story.append(Paragraph(line[2:], styles["TitleCenter"]))
    elif line.startswith("## "):
        story.append(Paragraph(line[3:], styles["Section"]))
    elif line.startswith("### "):
        story.append(Paragraph(line[4:], styles["SubSection"]))
    elif line.strip() == "---":
        story.append(Spacer(1, 10))
    elif line.startswith("- ") or line.startswith("* "):
        story.append(Paragraph(f"• {line[2:]}", styles["CustomBullet"]))
    else:
        story.append(Paragraph(line, styles["Body"]))

# Handle unclosed fence just in case.
if in_code_block:
    flush_code_block()

def _build_pdf(target_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(target_path),
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    doc.build(story)


output_path = pdf_path
try:
    _build_pdf(output_path)
except PermissionError:
    suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = base_dir / f"solution-{suffix}.pdf"
    _build_pdf(output_path)

print(f"Generated PDF: {output_path}")
