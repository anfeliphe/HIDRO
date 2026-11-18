"""
Multi-page Water Demand PDF report (ReportLab + charts from report_charts).
Page 1: cover band + title + table of contents only (no charts).
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape

from app.services.report_charts import (
    forecast_chart_bytes,
    parcel_map_by_demand_bytes,
    parcel_map_by_land_use_bytes,
    pie_chart_bytes,
)

W = A4[0]


def _png_flowable(
    buf: io.BytesIO,
    target_width: float,
    max_height: float | None = None,
    hAlign: str = "CENTER",
) -> RLImage:
    """Scale PNG to target width; preserve aspect ratio (avoids stretched maps/charts)."""
    buf.seek(0)
    ir = ImageReader(buf)
    iw, ih = ir.getSize()
    aspect = ih / float(max(iw, 1))
    w = target_width
    h = w * aspect
    if max_height is not None and h > max_height:
        h = max_height
        w = h / aspect
    buf.seek(0)
    return RLImage(buf, width=w, height=h, hAlign=hAlign)


def _fmt_m3(liters: float) -> str:
    m3 = liters / 1000.0
    if m3 >= 1e6:
        return f"{m3 / 1e6:.2f}M m³"
    if m3 >= 1e3:
        return f"{m3 / 1e3:.2f}K m³"
    return f"{m3:.2f} m³"


def _para_block(text: str, style: ParagraphStyle) -> list:
    if not (text or "").strip():
        return []
    safe = escape(text.strip()).replace("\n", "<br/>")
    return [Paragraph(safe, style), Spacer(1, 0.04 * inch)]


def _footer(canvas, doc, muted):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#1d4ed8"))
    canvas.setLineWidth(2)
    canvas.line(0.5 * inch, 0.62 * inch, W - 0.5 * inch, 0.62 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(muted)
    canvas.drawCentredString(W / 2, 0.45 * inch, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()


def build_water_demand_report_pdf(data: dict[str, Any], ai_sections: dict[str, str]) -> bytes:
    """
    ai_sections: executive, findings, recommendations, limitations (plain text).
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.58 * inch,
        title="Informe HIDRO",
    )

    styles = getSampleStyleSheet()
    brand_blue = colors.HexColor("#1d4ed8")
    brand_light = colors.HexColor("#dbeafe")
    slate = colors.HexColor("#0f172a")
    muted = colors.HexColor("#64748b")

    title_style = ParagraphStyle(
        "T",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=brand_blue,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    subtitle = ParagraphStyle(
        "S",
        parent=styles["Normal"],
        fontSize=11,
        textColor=muted,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=slate,
        spaceBefore=2,
        spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading3"],
        fontSize=11.5,
        textColor=brand_blue,
        spaceBefore=6,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    body = ParagraphStyle(
        "B",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        textColor=slate,
    )
    small = ParagraphStyle("Sm", parent=styles["Normal"], fontSize=8.5, textColor=muted, alignment=TA_CENTER)

    story: list[Any] = []

    # --- Page 1: Cover + TOC only ---
    cover_band = Table(
        [[Paragraph("<b><font color='white'>HIDRO · DEMANDA DE AGUA</font></b>", ParagraphStyle("cb", alignment=TA_CENTER, fontSize=9))]],
        colWidths=[6.9 * inch],
    )
    cover_band.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), brand_blue),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(cover_band)
    story.append(Spacer(1, 0.22 * inch))

    story.append(Paragraph("Informe de demanda de agua", title_style))
    story.append(
        Paragraph(
            "Análisis del territorio &mdash; estimaciones por escenario",
            subtitle,
        )
    )
    gen = data.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    scenario_label = escape(str(data.get("scenario_label", "")))
    lu = escape({"All":"Todos","Residential":"Residencial","Commercial":"Comercial","Mixed-use":"Mixto","Industrial":"Industrial","Official":"Oficial","Multiuser":"Multiusuario"}.get(str(data.get("land_use_filter")),str(data.get("land_use_filter", "Todos"))))
    gr = data.get("growth_rate", 2)
    hy = data.get("horizon_years", 5)
    meta = (
        f"<b>Generado:</b> {escape(gen)} &nbsp;|&nbsp; "
        f"<b>Escenario:</b> {scenario_label} &nbsp;|&nbsp; "
        f"<b>Crecimiento:</b> {gr}% / año &nbsp;|&nbsp; "
        f"<b>Horizonte:</b> {hy} años &nbsp;|&nbsp; "
        f"<b>Filtro de uso:</b> {lu}"
    )
    story.append(Paragraph(meta, ParagraphStyle("Meta", parent=body, alignment=TA_CENTER, fontSize=9)))
    story.append(Spacer(1, 0.26 * inch))

    story.append(Paragraph("<font color='#1d4ed8'><b>Contenido</b></font>", ParagraphStyle("TOC", fontSize=16, alignment=TA_CENTER, fontName="Helvetica-Bold", textColor=brand_blue, spaceAfter=10)))
    toc_rows = [
        ["#", "Sección", "Página"],
        ["1", "Resumen ejecutivo y análisis", "2"],
        ["2", "Indicadores principales", "3"],
        ["3", "Distribución por uso y demanda", "4"],
        ["4", "Distribución espacial de los predios", "5"],
        ["5", "Proyección de demanda", "6"],
        ["6", "Comparación de escenarios (0,09 y 0,1 m³/persona)", "7"],
        ["7", "Registro de predios (muestra)", "8"],
        ["8", "Calidad de datos, supuestos y limitaciones", "9"],
        ["9", "Anexo y parámetros del informe", "10"],
    ]
    toc_table = Table(toc_rows, colWidths=[0.45 * inch, 5.0 * inch, 0.9 * inch])
    toc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, brand_light]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(toc_table)
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph(
            "<i>La numeración sigue el orden de impresión. El informe incluye gráficos, mapas y tablas de HIDRO.</i>",
            small,
        )
    )

    story.append(PageBreak())

    # --- Section 1: AI ---
    exec_t = (ai_sections.get("executive") or "").strip()
    find_t = (ai_sections.get("findings") or "").strip()
    rec_t = (ai_sections.get("recommendations") or "").strip()
    lim_t = (ai_sections.get("limitations") or "").strip()

    story.append(Paragraph("1. Resumen ejecutivo y análisis", h1))
    story.extend(_para_block(exec_t or "El análisis no está disponible.", body))
    story.append(Paragraph("<b>Hallazgos principales</b>", h2))
    story.extend(_para_block(find_t or "—", body))
    story.append(Paragraph("<b>Recomendaciones</b>", h2))
    story.extend(_para_block(rec_t or "—", body))
    story.append(Paragraph("<b>Alcance y limitaciones del análisis</b>", h2))
    story.extend(_para_block(lim_t or "—", body))
    story.append(
        Paragraph(
            "<i>El análisis se genera con los indicadores de HIDRO y tiene carácter orientativo.</i>",
            small,
        )
    )

    story.append(PageBreak())

    # --- KPI ---
    story.append(Paragraph("2. Indicadores principales", h1))
    sm = data.get("summary") or {}
    pop = sm.get("population", 0)
    kpi_data = [
        ["Indicador", "Valor"],
        ["Demanda diaria estimada", _fmt_m3(float(sm.get("daily", 0)))],
        ["Demanda mensual estimada", _fmt_m3(float(sm.get("monthly", 0)))],
        ["Demanda anual estimada", _fmt_m3(float(sm.get("yearly", 0)))],
        ["Habitantes informados", f"{int(pop):,}"],
    ]
    t = Table(kpi_data, colWidths=[2.5 * inch, 3.7 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Paragraph(
            "<b>Indicadores:</b> Estos indicadores corresponden al escenario por persona seleccionado "
            f"({scenario_label}) y al filtro de uso ({lu}).",
            body,
        )
    )

    story.append(PageBreak())

    # --- Land use ---
    breakdown = data.get("breakdown") or []
    sizes = [float(b.get("consumption", 0) or 0) for b in breakdown]
    labels = [{"Residential":"Residencial","Commercial":"Comercial","Mixed-use":"Mixto","Industrial":"Industrial","Official":"Oficial","Multiuser":"Multiusuario"}.get(b.get("type"),str(b.get("type", ""))) for b in breakdown]
    pie_colors = ["#3b82f6", "#14b8a6", "#f59e0b"]

    story.append(Paragraph("3. Distribución por uso y demanda", h1))
    rows = [["Uso", "Predios", "Participación (%)", "Demanda anual"]]
    for b in breakdown:
        rows.append(
            [
                {"Residential":"Residencial","Commercial":"Comercial","Mixed-use":"Mixto","Industrial":"Industrial","Official":"Oficial","Multiuser":"Multiusuario"}.get(b.get("type"),str(b.get("type", ""))),
                str(b.get("count", "")),
                f"{b.get('percentage', '0')}%",
                _fmt_m3(float(b.get("consumption", 0))),
            ]
        )
    if len(rows) == 1:
        rows.append(["—", "—", "—", "—"])
    t2 = Table(rows, colWidths=[1.45 * inch, 0.95 * inch, 0.95 * inch, 2.85 * inch])
    t2.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(t2)
    story.append(Spacer(1, 0.05 * inch))
    if sum(sizes) > 0:
        pie_buf = pie_chart_bytes(labels, sizes, pie_colors[: len(labels)])
        story.append(_png_flowable(pie_buf, 5.5 * inch, max_height=4.0 * inch))

    story.append(Spacer(1, 0.12 * inch))

    # --- Maps (embed land-use and demand figures independently) ---
    story.append(Paragraph("4. Distribución espacial de los predios", h1))
    pts = data.get("parcel_points") or []
    buf_land = parcel_map_by_land_use_bytes(pts)
    buf_dem = parcel_map_by_demand_bytes(pts)
    map_col_w = 3.05 * inch
    map_max_h = 3.05 * inch
    if buf_land and buf_dem:
        story.append(
            Paragraph(
                "Los gráficos representan el territorio: <b>izquierda</b>, predios por uso; "
                "<b>derecha</b>, intensidad relativa de demanda o habitantes cuando la demanda es uniforme.",
                body,
            )
        )
        story.append(Spacer(1, 0.06 * inch))
        m1 = _png_flowable(buf_land, map_col_w, map_max_h)
        m2 = _png_flowable(buf_dem, map_col_w, map_max_h)
        mt = Table([[m1, m2]], colWidths=[map_col_w, map_col_w])
        mt.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (1, 0), (1, 0), 22),
                    ("RIGHTPADDING", (0, 0), (0, 0), 6),
                ]
            )
        )
        story.append(mt)
    elif buf_land:
        story.append(
            Paragraph(
                "Predios por uso; no se pudo generar el mapa de demanda.",
                body,
            )
        )
        story.append(Spacer(1, 0.06 * inch))
        story.append(_png_flowable(buf_land, 6.5 * inch, max_height=3.75 * inch))
    elif buf_dem:
        story.append(
            Paragraph(
                "Intensidad relativa; no se pudo generar el mapa de usos.",
                body,
            )
        )
        story.append(Spacer(1, 0.06 * inch))
        story.append(_png_flowable(buf_dem, 6.5 * inch, max_height=3.75 * inch))
    else:
        story.append(
            Paragraph(
                "<i>No hay coordenadas disponibles para generar los mapas.</i>",
                body,
            )
        )

    story.append(PageBreak())

    # --- Forecast ---
    fc = data.get("forecast") or {}
    years_x = list(range(len(fc.get("year90", []))))
    y90 = fc.get("year90") or []
    y100 = fc.get("year100") or []
    story.append(Paragraph("5. Proyección de demanda", h1))
    story.append(
        Paragraph(
            f"Crecimiento compuesto del <b>{escape(str(gr))}%</b> anual durante <b>{escape(str(hy))}</b> años "
            "aplicado a la demanda anual actual en ambos escenarios.",
            body,
        )
    )
    story.append(Spacer(1, 0.06 * inch))
    if years_x and y90 and y100 and len(y90) == len(y100):
        line_buf = forecast_chart_bytes(years_x, y90, y100, float(gr), int(hy))
        story.append(_png_flowable(line_buf, 6.35 * inch, max_height=4.0 * inch))
        story.append(Spacer(1, 0.06 * inch))
        fh = [["Año", "0.09 m³/c (anual)", "0.1 m³/c (anual)"]]
        for i in range(len(y90)):
            fh.append([str(i), _fmt_m3(float(y90[i])), _fmt_m3(float(y100[i]))])
        tft = Table(fh, colWidths=[0.85 * inch, 2.45 * inch, 2.45 * inch])
        tft.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(tft)

    story.append(Spacer(1, 0.12 * inch))

    # --- Scenario ---
    story.append(Paragraph("6. Comparación de escenarios (0,09 y 0,1 m³/persona)", h1))
    sc = data.get("scenario_comparison") or {}
    sct = Table(
        [
            ["Escenario", "Demanda anual (aproximada)"],
            ["0.09 m³/c", _fmt_m3(float(sc.get("low", 0)))],
            ["0.1 m³/c", _fmt_m3(float(sc.get("high", 0)))],
            ["Difference (anual)", _fmt_m3(float(sc.get("diff", 0)))],
        ],
        colWidths=[2.2 * inch, 3.5 * inch],
    )
    sct.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(sct)
    story.append(Spacer(1, 0.06 * inch))
    story.append(
        Paragraph(
            "El escenario de 0,1 m³/persona aumenta la demanda anual frente al de 0,09 m³/persona, "
            "con los mismos habitantes y usos del predio.",
            body,
        )
    )

    story.append(Spacer(1, 0.12 * inch))

    # --- Parcel sample ---
    story.append(Paragraph("7. Registro de predios (muestra)", h1))
    sample = data.get("parcel_sample") or []
    pr = [["Predio", "Uso", "Habitantes", "Latitud", "Longitud"]]
    for row in sample[:35]:
        pr.append(
            [
                escape(str(row.get("parcel_id", "")))[:18],
                {"Residential":"Residencial","Commercial":"Comercial","Mixed-use":"Mixto","Industrial":"Industrial","Official":"Oficial","Multiuser":"Multiusuario"}.get(row.get("land_use"),str(row.get("land_use", "")))[:14],
                str(row.get("population", "")),
                f"{float(row.get('lat', 0)):.5f}",
                f"{float(row.get('lng', 0)):.5f}",
            ]
        )
    if len(pr) == 1:
        pr.append(["—", "—", "—", "—", "—"])
    pt = Table(pr, colWidths=[1.1 * inch, 1.1 * inch, 0.85 * inch, 1.1 * inch, 1.1 * inch])
    pt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    story.append(pt)
    story.append(Spacer(1, 0.06 * inch))
    story.append(
        Paragraph(
            f"<i>Se muestran hasta 35 de {data.get('parcel_stats', {}).get('total', 0)} predios incluidos.</i>",
            small,
        )
    )

    story.append(Spacer(1, 0.12 * inch))

    # --- Limitations ---
    story.append(Paragraph("8. Calidad de datos, supuestos y limitaciones", h1))
    story.append(
        Paragraph(
            "<b>Modelo:</b> Vivienda: habitantes por dotación. Referencias EAAB: tabla 1 por sector y diámetro (m³/suscriptor/mes); anual equivalente = mensual por 12. La tabla 2 es total de obra y se excluye de demanda recurrente. Otros modelos provisionales: cantidad por litros/unidad por días de operación. "
            "Solo la parte residencial cambia entre 0,09 y 0,1 m³/persona/día. El promedio diario es el volumen anual dividido entre 365; el mensual es el anual dividido entre 12. Incluye perfiles provisionales: revise las fichas. No sustituye mediciones ni facturación.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Paragraph(
            "<b>Proyección:</b> Se aplica crecimiento anual compuesto a la demanda actual; "
            "la demanda real puede variar por políticas, infraestructura, clima y comportamiento.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        Paragraph(
            "<b>Mapas:</b> Son gráficos estáticos con las coordenadas del mapa web; no incluyen el mapa base de calles.",
            body,
        )
    )

    story.append(PageBreak())

    # --- Appendix ---
    story.append(Paragraph("9. Anexo y parámetros del informe", h1))
    ps = data.get("parcel_stats") or {}
    by_type = ps.get("by_type") or {}
    parts = [f"<b>{escape({"Residential":"Residencial","Commercial":"Comercial","Mixed-use":"Mixto","Industrial":"Industrial","Official":"Oficial","Multiuser":"Multiusuario"}.get(k,str(k)))}:</b> {int(v)}" for k, v in by_type.items()]
    line = f"<b>Total de predios:</b> {int(ps.get('total', 0))}"
    if parts:
        line += "<br/>" + " &nbsp;|&nbsp; ".join(parts)
    story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.06 * inch))
    story.append(
        Paragraph(
            f"<b>Parámetros utilizados:</b> escenario {scenario_label}; crecimiento {gr}%/año; horizonte {hy} años; "
            f"filtro {lu}.",
            body,
        )
    )

    def _foot(canvas, doc):
        _footer(canvas, doc, muted)

    doc.build(story, onFirstPage=_foot, onLaterPages=_foot)
    pdf = buf.getvalue()
    buf.close()
    return pdf
