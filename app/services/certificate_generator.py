"""
Generates a single PDF certificate using ReportLab.

The template draws everything from scratch (borders, text, ornaments)
so we don't need any external image assets.
"""

from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.config import CERTIFICATES_DIR


# ── colour palette ──────────────────────────────────────────────────────────
PRIMARY_COLOR = HexColor("#722F37")  # Wine Red
ACCENT_COLOR  = HexColor("#D4AF37")  # Gold
DARK_GRAY     = HexColor("#333333")
MED_GRAY      = HexColor("#666666")
LIGHT_GRAY    = HexColor("#999999")
CREAM_BG      = HexColor("#FFFBF0")  # Warm Ivory


def _draw_fitted_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str,
    max_size: float,
    min_size: float = 12,
):
    """Draw *text* centred at (x, y), shrinking the font until it fits."""
    size = max_size
    while size >= min_size:
        if c.stringWidth(text, font_name, size) <= max_width:
            break
        size -= 1
    c.setFont(font_name, size)
    c.drawCentredString(x, y, text)


def generate_certificate_pdf(
    *,
    recipient_name: str,
    event_name: str,
    event_date: str,
    issuer_name: str,
    title: str,
    job_id: int,
    certificate_id: int,
) -> str:
    """Create a PDF certificate and return the absolute file path."""

    job_dir = CERTIFICATES_DIR / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    filepath = job_dir / f"certificate_{certificate_id}.pdf"
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(str(filepath), pagesize=landscape(A4))

    # ── background fill ─────────────────────────────────────────────────
    c.setFillColor(CREAM_BG)
    c.rect(0, 0, page_w, page_h, fill=True, stroke=False)

    # ── outer border (primary) ─────────────────────────────────────────────
    outer_margin = 25
    c.setStrokeColor(PRIMARY_COLOR)
    c.setLineWidth(3)
    c.rect(outer_margin, outer_margin, page_w - 2 * outer_margin, page_h - 2 * outer_margin)

    # ── inner border (accent) ─────────────────────────────────────────────
    inner_margin = 35
    c.setStrokeColor(ACCENT_COLOR)
    c.setLineWidth(1.5)
    c.rect(inner_margin, inner_margin, page_w - 2 * inner_margin, page_h - 2 * inner_margin)

    # ── corner ornaments ────────────────────────────────────────────────
    corner_square_size = 8
    c.setFillColor(ACCENT_COLOR)
    for cx, cy in [
        (inner_margin - 1, inner_margin - 1),
        (page_w - inner_margin - corner_square_size + 1, inner_margin - 1),
        (inner_margin - 1, page_h - inner_margin - corner_square_size + 1),
        (page_w - inner_margin - corner_square_size + 1, page_h - inner_margin - corner_square_size + 1),
    ]:
        c.rect(cx, cy, corner_square_size, corner_square_size, fill=True, stroke=False)

    centre = page_w / 2
    usable = page_w - 2 * inner_margin - 80       # max text width with some padding

    # ── title ───────────────────────────────────────────────────────────
    y = page_h - 100
    c.setFillColor(PRIMARY_COLOR)
    _draw_fitted_text(c, title.upper(), centre, y, usable, "Times-Roman", 36)

    # ── accent rule with diamond ──────────────────────────────────────────
    y -= 20
    line_half_width = 120
    c.setStrokeColor(ACCENT_COLOR)
    c.setLineWidth(2)
    c.line(centre - line_half_width, y, centre + line_half_width, y)

    c.setFillColor(ACCENT_COLOR)
    d = 5
    c.saveState()
    c.translate(centre, y)
    c.rotate(45)
    c.rect(-d / 2, -d / 2, d, d, fill=True, stroke=False)
    c.restoreState()

    # ── "This certificate is proudly presented to" ───────────────────────────────────────
    y -= 45
    c.setFillColor(MED_GRAY)
    c.setFont("Times-Italic", 16)
    c.drawCentredString(centre, y, "This certificate is proudly presented to")

    # ── recipient name ──────────────────────────────────────────────────
    y -= 50
    c.setFillColor(PRIMARY_COLOR)
    _draw_fitted_text(c, recipient_name, centre, y, usable, "Times-Bold", 30)

    name_w = c.stringWidth(recipient_name, "Times-Bold", 30)
    y -= 6
    c.setStrokeColor(ACCENT_COLOR)
    c.setLineWidth(1)
    c.line(centre - name_w / 2 - 20, y, centre + name_w / 2 + 20, y)

    # ── "for outstanding completion of" ────────────────────────────────────
    y -= 35
    c.setFillColor(MED_GRAY)
    c.setFont("Times-Italic", 16)
    c.drawCentredString(centre, y, "for outstanding completion of")

    # ── event name ──────────────────────────────────────────────────────
    y -= 38
    c.setFillColor(DARK_GRAY)
    _draw_fitted_text(c, event_name, centre, y, usable, "Times-Bold", 22)

    # ── formatted date ──────────────────────────────────────────────────
    try:
        dt = datetime.strptime(event_date, "%Y-%m-%d")
        pretty_date = dt.strftime("%B %d, %Y")
    except ValueError:
        pretty_date = event_date

    y -= 40
    c.setFillColor(MED_GRAY)
    c.setFont("Times-Roman", 14)
    c.drawCentredString(centre, y, f"Date: {pretty_date}")

    # ── issuer / signature line ─────────────────────────────────────────
    y -= 55
    signature_line_half = 80
    c.setStrokeColor(DARK_GRAY)
    c.setLineWidth(0.8)
    c.line(centre - signature_line_half, y, centre + signature_line_half, y)

    y -= 18
    c.setFillColor(DARK_GRAY)
    c.setFont("Times-Roman", 13)
    c.drawCentredString(centre, y, issuer_name)

    y -= 16
    c.setFillColor(MED_GRAY)
    c.setFont("Times-Italic", 10)
    c.drawCentredString(centre, y, "Authorized Signatory")

    # ── certificate ID footer ───────────────────────────────────────────
    cert_uid = f"CERT-{job_id:04d}-{certificate_id:06d}"
    c.setFillColor(LIGHT_GRAY)
    c.setFont("Helvetica", 8)
    c.drawCentredString(centre, inner_margin + 12, f"Certificate ID: {cert_uid}")

    c.save()
    return str(filepath)
