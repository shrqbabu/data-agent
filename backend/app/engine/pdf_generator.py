"""Executive PDF Report Generator.

Compiles the Final Analytical Report, Duplicates vs Unique Records Summary,
and Suggested Dashboard Visual into a publication-grade PDF report.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        HRFlowable,
        Image,
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page numbers and headers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "ANALYTICS AGENT | EXECUTIVE INTELLIGENCE REPORT")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Running Footer (all pages)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#94A3B8"))
        self.drawString(54, 36, f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · Confidential")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(558, 36, page_str)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)

        self.restoreState()


def generate_pdf_report(
    dataset_name: str,
    total_rows: int,
    unique_records: int,
    duplicate_rows: int,
    quality_score: float,
    report_data: Dict[str, Any],
    dashboard_png_bytes: Optional[bytes] = None,
    prompt: Optional[str] = None,
) -> bytes:
    """Generate an executive PDF containing the final analytical report and suggested dashboard visual."""
    if not REPORTLAB_AVAILABLE:
        return b"%PDF-1.4 Mock PDF fallback - please install reportlab>=4.2"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    )

    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0284C7"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=8,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=12,
        bulletIndent=4,
        spaceAfter=5,
    )

    card_label_style = ParagraphStyle(
        "CardLabel",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )

    card_value_style = ParagraphStyle(
        "CardValue",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,
    )

    elements = []

    # 1. Header & Title Block
    elements.append(Paragraph("Executive Analytics Report", title_style))
    prompt_snippet = f" · Prompt: \"{prompt[:60]}...\"" if prompt and len(prompt) > 60 else (f" · Prompt: \"{prompt}\"" if prompt else "")
    elements.append(
        Paragraph(
            f"Dataset: <b>{dataset_name}</b>{prompt_snippet}",
            subtitle_style,
        )
    )
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=14))

    # 2. Data Health & Profiling KPI Summary (Duplicates vs Uniques)
    dup_pct = (duplicate_rows / total_rows * 100) if total_rows > 0 else 0.0
    kpi_data = [
        [
            Paragraph("TOTAL RECORDS", card_label_style),
            Paragraph("UNIQUE RECORDS", card_label_style),
            Paragraph("DUPLICATE ROWS", card_label_style),
            Paragraph("DATA QUALITY", card_label_style),
        ],
        [
            Paragraph(f"<b>{total_rows:,}</b>", card_value_style),
            Paragraph(f"<b><font color='#059669'>{unique_records:,}</font></b>", card_value_style),
            Paragraph(f"<b><font color='{'#DC2626' if duplicate_rows > 0 else '#059669'}'>{duplicate_rows:,} ({dup_pct:.1f}%)</font></b>", card_value_style),
            Paragraph(f"<b><font color='#0284C7'>{quality_score:.1f}%</font></b>", card_value_style),
        ],
    ]

    kpi_table = Table(kpi_data, colWidths=[126, 126, 126, 126])
    kpi_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 14))

    # 3. Executive Summary
    exec_summary = report_data.get("executive_summary", "Comprehensive analytical evaluation conducted.")
    elements.append(Paragraph("1. Executive Summary", h2_style))
    elements.append(Paragraph(exec_summary, body_style))
    elements.append(Spacer(1, 8))

    # 4. Key Analytical Findings
    key_findings = report_data.get("key_findings", [])
    if key_findings:
        elements.append(Paragraph("2. Key Analytical Findings", h2_style))
        for finding in key_findings:
            elements.append(Paragraph(f"• {finding}", bullet_style))
        elements.append(Spacer(1, 8))

    # 5. Suggested Dashboard Visual (Embedded High-Res Image)
    if dashboard_png_bytes:
        elements.append(KeepTogether([
            Paragraph("3. Suggested Dashboard Visual", h2_style),
            Paragraph("High-resolution analytical dashboard visual synthesized from validated metric registers:", body_style),
            Spacer(1, 4),
        ]))
        try:
            img_buffer = io.BytesIO(dashboard_png_bytes)
            img = Image(img_buffer, width=504, height=270)
            elements.append(img)
            elements.append(Spacer(1, 12))
        except Exception:
            pass

    # 6. Strategic Business Recommendations
    recommendations = report_data.get("recommendations", [])
    if recommendations:
        elements.append(KeepTogether([
            Paragraph("4. Strategic Business Recommendations", h2_style),
            *[Paragraph(f"• {rec}", bullet_style) for rec in recommendations],
            Spacer(1, 8),
        ]))

    # Build PDF with dynamic 2-pass page numbering
    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
