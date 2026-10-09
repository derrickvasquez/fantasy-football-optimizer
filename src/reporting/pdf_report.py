from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PURPLE = colors.HexColor("#7C3AED")
DARK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F3F4F6")
GREEN = colors.HexColor("#16A34A")
RED = colors.HexColor("#DC2626")


def _safe(value: Any, fallback: str = "-") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def build_report_pdf(
    my_picks: list[dict[str, Any]],
    report: dict[str, Any],
    league_name: str,
) -> bytes:
    """Build a downloadable fantasy draft report card PDF in memory."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title="Fantasy Football Draft Report Card",
        author="Fantasy Football Draft Optimizer",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=25,
        textColor=DARK,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=PURPLE,
        spaceBefore=8,
        spaceAfter=7,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=DARK,
    )

    story = [
        Paragraph("Fantasy Football Draft Report Card", title_style),
        Paragraph(league_name, subtitle_style),
    ]

    overall = _safe(report.get("grade"))
    metric_data = [
        ["OVERALL", "DRAFT VALUE", "ROSTER", "RB/WR DEPTH", "BYE BALANCE", "DISCIPLINE"],
        [
            overall,
            _safe(report.get("value_grade")),
            _safe(report.get("construction_grade")),
            _safe(report.get("depth_grade")),
            _safe(report.get("bye_grade")),
            _safe(report.get("discipline_grade")),
        ],
    ]
    metrics = Table(metric_data, colWidths=[1.12 * inch] * 6, rowHeights=[0.28 * inch, 0.5 * inch])
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 17),
                ("TEXTCOLOR", (0, 1), (0, 1), PURPLE),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 12)])

    best = report.get("best_value")
    reach = report.get("biggest_reach")
    callout_rows = []
    if best:
        callout_rows.append(
            [
                Paragraph("<b>Best Value</b>", body_style),
                Paragraph(
                    f"{best['name']} - Pick {best['overall_pick']} "
                    f"({best['value_delta']:+.0f} vs ADP)",
                    body_style,
                ),
            ]
        )
    if reach:
        callout_rows.append(
            [
                Paragraph("<b>Biggest Reach</b>", body_style),
                Paragraph(
                    f"{reach['name']} - Pick {reach['overall_pick']} "
                    f"({reach['value_delta']:+.0f} vs ADP)",
                    body_style,
                ),
            ]
        )
    if callout_rows:
        callouts = Table(callout_rows, colWidths=[1.25 * inch, 5.55 * inch])
        callouts.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#EEEEEE")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([callouts, Spacer(1, 8)])

    story.append(Paragraph("Starting Lineup", section_style))
    slot_rows = [["Slot", "Player", "Pos", "Team", "Bye"]]
    for slot, player in report.get("slots", {}).items():
        if player:
            slot_rows.append(
                [slot, player["name"], player["position"], player["team"], _safe(player.get("bye"))]
            )
        else:
            slot_rows.append([slot, "Open", "-", "-", "-"])

    roster_table = Table(slot_rows, colWidths=[0.75 * inch, 3.35 * inch, 0.65 * inch, 0.75 * inch, 0.55 * inch])
    roster_table.setStyle(_table_style())
    story.extend([roster_table, Spacer(1, 8)])

    bench = report.get("bench", [])
    story.append(Paragraph("Bench", section_style))
    if bench:
        bench_rows = [["Player", "Pos", "Team", "Bye", "Pick"]]
        for player in bench:
            bench_rows.append(
                [
                    player["name"],
                    player["position"],
                    player["team"],
                    _safe(player.get("bye")),
                    player["overall_pick"],
                ]
            )
        bench_table = Table(bench_rows, colWidths=[3.55 * inch, 0.7 * inch, 0.8 * inch, 0.6 * inch, 0.7 * inch])
        bench_table.setStyle(_table_style())
        story.append(bench_table)
    else:
        story.append(Paragraph("No bench players drafted.", body_style))

    story.extend([PageBreak(), Paragraph("Pick-by-Pick Draft Review", section_style)])
    pick_rows = [["Rnd", "Overall", "Player", "Pos", "Team", "ESPN ADP", "Value"]]
    for pick in my_picks:
        adp = float(pick.get("espn_adp", pick["overall_pick"]))
        delta = float(pick["overall_pick"]) - adp
        value_text = f"{delta:+.1f}" if pick["position"] not in {"K", "DST"} else "Special"
        pick_rows.append(
            [
                pick["round"],
                pick["overall_pick"],
                pick["name"],
                pick["position"],
                pick["team"],
                f"{adp:.1f}",
                value_text,
            ]
        )

    pick_table = Table(
        pick_rows,
        colWidths=[0.42 * inch, 0.55 * inch, 2.65 * inch, 0.5 * inch, 0.6 * inch, 0.75 * inch, 0.65 * inch],
        repeatRows=1,
    )
    pick_table.setStyle(_table_style())
    story.extend([pick_table, Spacer(1, 12)])

    methodology = report.get("methodology")
    if methodology:
        story.extend([
            Paragraph("How the grade is calculated", section_style),
            Paragraph(methodology, body_style),
            Spacer(1, 10),
        ])

    story.append(
        Paragraph(
            "Generated by Fantasy Football Draft Optimizer. Grades are decision-support metrics, not guarantees of season results.",
            ParagraphStyle(
                "FooterNote",
                parent=body_style,
                fontSize=7.5,
                textColor=MUTED,
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(story)
    return buffer.getvalue()


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TEXTCOLOR", (0, 1), (-1, -1), DARK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )
