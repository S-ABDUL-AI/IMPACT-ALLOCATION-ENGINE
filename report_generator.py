"""
PDF report generator for GovFund Allocation Engine.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _currency(v: float) -> str:
    return f"${float(v):,.0f}"


def _save_plot_to_png(fig) -> BytesIO:
    bio = BytesIO()
    fig.savefig(bio, format="png", dpi=180, bbox_inches="tight")
    bio.seek(0)
    return bio


def _build_cover(
    total_budget: float,
    scenario: str,
    region_scope: str,
) -> bytes:
    """Dark cover page built separately to avoid style bleed into body pages."""
    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=LETTER, leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    eye = ParagraphStyle(
        "eye",
        parent=styles["Normal"],
        textColor=colors.HexColor("#C9A84C"),
        fontSize=9,
        leading=11,
    )
    title = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#0A1F44"),
        fontSize=22,
        leading=26,
    )
    sub = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        textColor=colors.HexColor("#2C3E50"),
        fontSize=11,
        leading=15,
    )
    story = [
        Spacer(1, 1.2 * inch),
        Paragraph("GovFund Allocation Engine · Malaria CEA Portfolio", eye),
        Spacer(1, 0.2 * inch),
        Paragraph("Cost Effectiveness Decision Brief", title),
        Spacer(1, 0.15 * inch),
        Paragraph("Where should this dollar go?", title),
        Spacer(1, 0.35 * inch),
        Paragraph(
            f"Modeled budget: <b>{_currency(total_budget)}</b> · Scenario: <b>{scenario}</b> · Scope: <b>{region_scope}</b>",
            sub,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph(
            f"Generated on {date.today().isoformat()} for policy and portfolio review. "
            "This report is decision support and should be used with implementation evidence and governance review.",
            sub,
        ),
    ]
    doc.build(story)
    return bio.getvalue()


def _build_body(
    alloc: pd.DataFrame,
    scored: pd.DataFrame,
    total_budget: float,
    scenario: str,
    region_scope: str,
    data_source: str,
) -> bytes:
    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=LETTER, leftMargin=0.65 * inch, rightMargin=0.65 * inch)
    styles = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=styles["Heading2"], textColor=colors.HexColor("#0A1F44"), fontSize=14)
    b = ParagraphStyle("b", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#2C3E50"))

    ranked = alloc.sort_values("final_score", ascending=False).reset_index(drop=True)
    top = ranked.iloc[0]
    top_share = 100.0 * float(top["allocation"]) / float(total_budget) if float(total_budget) else 0.0

    story = [
        Paragraph("Executive Summary", h),
        Paragraph(
            f"<b>Recommendation:</b> Under <b>{scenario}</b>, <b>{top['intervention_name']}</b> is the top allocation "
            f"at about <b>{top_share:.0f}%</b> of <b>{_currency(total_budget)}</b>.",
            b,
        ),
        Spacer(1, 0.12 * inch),
        Paragraph(
            f"<b>Context:</b> {len(alloc)} interventions in scope ({region_scope}). Data source: {data_source}. "
            "Primary use case is malaria intervention prioritization.",
            b,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Policy Brief: Risk · Implication · Action", h),
        Paragraph(
            f"<b>Risk:</b> {int((alloc['uncertainty_level'] > 0.25).sum())} interventions show elevated uncertainty.",
            b,
        ),
        Paragraph(
            f"<b>Implication:</b> Current modeled envelope {_currency(total_budget)} concentrates on top-ranked interventions.",
            b,
        ),
        Paragraph(
            "<b>Action:</b> Prioritize top-ranked intervention, then stress test scenario and cost assumptions before final commitment.",
            b,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Allocation Table", h),
    ]

    table_df = ranked[
        ["intervention_name", "region", "final_score", "allocation", "evidence_strength", "uncertainty_level"]
    ].copy()
    table_df["final_score"] = table_df["final_score"].map(lambda x: f"{float(x):.5f}")
    table_df["allocation"] = table_df["allocation"].map(_currency)
    data = [list(table_df.columns)] + table_df.values.tolist()
    t = Table(data, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A1F44")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E6EC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F6F1")]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.2 * inch))

    # Add two compact charts via matplotlib
    fig1, ax1 = plt.subplots(figsize=(5.8, 2.2))
    plot_alloc = ranked.sort_values("allocation", ascending=True)
    ax1.barh(plot_alloc["intervention_name"], plot_alloc["allocation"], color="#0A1F44")
    ax1.set_title("Allocation by intervention (USD)")
    ax1.grid(False)
    img1 = _save_plot_to_png(fig1)
    plt.close(fig1)

    fig2, ax2 = plt.subplots(figsize=(5.8, 2.2))
    plot_score = ranked.sort_values("final_score", ascending=True)
    ax2.barh(plot_score["intervention_name"], plot_score["final_score"], color="#C9A84C")
    ax2.set_title("Final score ranking")
    ax2.grid(False)
    img2 = _save_plot_to_png(fig2)
    plt.close(fig2)

    from reportlab.platypus import Image

    story.append(Paragraph("Charts", h))
    story.append(Image(img1, width=6.2 * inch, height=2.3 * inch))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Image(img2, width=6.2 * inch, height=2.3 * inch))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "Built by Sherriff Abdul-Hamid · Product leader specializing in government digital services, "
            "safety net benefits delivery, and decision support tools for underserved communities.",
            ParagraphStyle("foot", parent=b, fontSize=8.5, textColor=colors.HexColor("#6B7280")),
        )
    )

    doc.build(story)
    return bio.getvalue()


def build_report_bytes(
    alloc: pd.DataFrame,
    scored: pd.DataFrame,
    total_budget: float,
    scenario: str,
    region_scope: str,
    data_source: str,
) -> bytes:
    """
    Build and return merged PDF bytes.
    """
    cover_pdf = _build_cover(total_budget=total_budget, scenario=scenario, region_scope=region_scope)
    body_pdf = _build_body(
        alloc=alloc,
        scored=scored,
        total_budget=total_budget,
        scenario=scenario,
        region_scope=region_scope,
        data_source=data_source,
    )

    writer = PdfWriter()
    for src in (cover_pdf, body_pdf):
        reader = PdfReader(BytesIO(src))
        for page in reader.pages:
            writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
