import os
from io import BytesIO
from datetime import datetime
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Image, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from helper.chart_builder_and_sql_helper_and_page_size import generate_backend_chart,get_pagesize_by_columns,extract_select_query
from database.dbConnection import get_master_db
from reportlab.lib.units import inch
from PIL import Image as PILImage
import io

def generate_report_pdf(session_id, payload, company_db):
    cursor = company_db.cursor(dictionary=True)

    # ================= COMPANY =================
    cursor.execute(
        "SELECT company_id FROM users WHERE session_id=%s LIMIT 1",
        (session_id,)
    )
    company_id = cursor.fetchone()["company_id"]

    master = get_master_db()
    mcur = master.cursor(dictionary=True)
    mcur.execute(
        """
        SELECT
            c.company_name,
            c.company_logo,
            c.address,
            c.city,
            c.pin_code,
            co.country_name
        FROM companies c
        LEFT JOIN countries co ON c.country = co.country_code
        WHERE c.id = %s
        """,
        (company_id,)
    )
    company = mcur.fetchone()
    mcur.close()
    master.close()

    # ================= DATA =================
    cursor.execute(extract_select_query(payload["query"]))
    rows = cursor.fetchall()
    columns = [c[0] for c in cursor.description]

    pagesize = get_pagesize_by_columns(len(columns))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title",
        fontSize=18,
        fontName="Helvetica-Bold"
    )

    # th_style = ParagraphStyle(
    #     "th",
    #     fontSize=9,
    #     fontName="Helvetica-Bold",
    #     alignment=1
    # )
    th_style = ParagraphStyle(
    "th",
    fontSize=9,
    fontName="Helvetica-Bold",
    alignment=1,
    textColor=colors.HexColor("#061F65"),  #  bluish (clean professional)
    underline=False                        #  ensure no underline
    )

    cell_style = ParagraphStyle(
        "cell",
        fontSize=8,
        leading=10,
        wordWrap="CJK"   # text wrap fix
    )

    elements = []

    # ================= LOGO =================
    logo_img = None
    if company.get("company_logo") and os.path.exists(company["company_logo"].lstrip("/")):
        img = PILImage.open(company["company_logo"].lstrip("/")).convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        logo_img = Image(buf, width=1.2 * inch, height=0.8 * inch)

    # ================= HEADER =================
    header = Table(
        [[logo_img or "", Paragraph(company["company_name"], title_style)]],
        colWidths=[1.5 * inch, doc.width - 1.5 * inch]
    )

    header.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))

    elements.append(header)

    # ================= ADDRESS =================
    address_parts = []
    if company.get("address"):
        address_parts.append(company["address"])

    city_pin = []
    if company.get("city"):
        city_pin.append(company["city"])
    if company.get("pin_code"):
        city_pin.append(company["pin_code"])

    if city_pin:
        address_parts.append(" – ".join(city_pin))

    if company.get("country_name"):
        address_parts.append(company["country_name"])

    elements.append(Paragraph(", ".join(address_parts), styles["Normal"]))
    elements.append(Spacer(1, 16))
    

    # ---------- DIVIDER ----------
    divider = Table(
        [[""]],
        colWidths=[doc.width],
        rowHeights=[1]
    )

    divider.setStyle(TableStyle([
    ("LINEBELOW", (0, 0), (-1, -1), 1.6, colors.HexColor("#CBD5E1")),
    ]))

    elements.append(divider)
    elements.append(Spacer(1, 18))
    # ================= CHARTS (UI-LIKE BOX) =================
    CHART_BOX_WIDTH = (doc.width / 2) - 20
    CHART_BOX_HEIGHT = 190   #  same visual density as UI

    def chart_box(chart_img):
        return Table(
            [[chart_img]],
            colWidths=[CHART_BOX_WIDTH],
            rowHeights=[CHART_BOX_HEIGHT],
            style=TableStyle([
                ("BOX", (0,0), (-1,-1), 0.6, colors.HexColor("#E5E7EB")),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("LEFTPADDING", (0,0), (-1,-1), 8),
                ("RIGHTPADDING", (0,0), (-1,-1), 8),
                ("TOPPADDING", (0,0), (-1,-1), 8),
                ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ])
        )

    chart_list = payload.get("charts") or payload.get("chart") or []
    charts = []

    for c in sorted(chart_list, key=lambda x: x.get("order", 0)):
        img = generate_backend_chart(c)
        if img:
            charts.append(
                Image(
                    img,
                    width=CHART_BOX_WIDTH - 16,
                    height=CHART_BOX_HEIGHT - 16,
                    kind="proportional",   #  THIS LINE FIXES STRETCHING
                    hAlign="CENTER"
                )
            )

    for i in range(0, len(charts), 2):
        left = chart_box(charts[i])
        right = chart_box(charts[i + 1]) if i + 1 < len(charts) else ""

        row_table = Table(
            [[left, right]],
            colWidths=[CHART_BOX_WIDTH, CHART_BOX_WIDTH],
            style=TableStyle([
                # column gap create
                ("LEFTPADDING", (0,0), (0,0), 0),
                ("RIGHTPADDING", (0,0), (0,0), 10),  # gap on right of left card

                ("LEFTPADDING", (1,0), (1,0), 10),   # gap on left of right card
                ("RIGHTPADDING", (1,0), (1,0), 0),

                ("VALIGN", (0,0), (-1,-1), "TOP"),
            ])
        )

        elements.append(row_table)
        elements.append(Spacer(1, 20))


    # ================= TABLE (NO OVERFLOW) =================
    table_data = [[
    Paragraph(col.replace("_", " ").upper(), th_style)
    for col in columns
   ]]
    for r in rows:
        table_data.append([
            Paragraph(str(r.get(col, "")), cell_style)
            for col in columns
        ])

    col_w = max(70, doc.width / len(columns))

    table = Table(
        table_data,
        colWidths=[col_w]*len(columns),
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F3F4F6")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    elements.append(table)

    # ================= FOOTER =================
    def footer(canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(doc.pagesize[0]/2, 20, f"Page {doc.page}")
        canvas.drawRightString(doc.pagesize[0]-40, 20, "Generated by Sahajinsight")

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)

    # ================= SAVE =================
    os.makedirs("uploads/reportpdf", exist_ok=True)
    filename = f"{payload.get('report_title','Report')}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    path = f"uploads/reportpdf/{filename}"

    with open(path, "wb") as f:
        f.write(buffer.getvalue())

    return filename