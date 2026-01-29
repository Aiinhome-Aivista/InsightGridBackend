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

    # -------- COMPANY --------
    cursor.execute(
        "SELECT company_id FROM users WHERE session_id=%s LIMIT 1",
        (session_id,)
    )
    company_id = cursor.fetchone()["company_id"]

    master = get_master_db()
    mcur = master.cursor(dictionary=True)
    mcur.execute(
        "SELECT company_name, address, company_logo FROM companies WHERE id=%s",
        (company_id,)
    )
    company = mcur.fetchone()
    mcur.close()
    master.close()

    # -------- DATA --------
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
    title_style = ParagraphStyle("title", fontSize=18, fontName="Helvetica-Bold")
    th_style = ParagraphStyle("th", fontSize=9, fontName="Helvetica-Bold", alignment=1)

    elements = []
    # -------- LOGO --------
    logo_img = None
    logo_path = company.get("company_logo")

    if logo_path:
        logo_path = logo_path.lstrip("/")   # safety
        if os.path.exists(logo_path):
            try:
                img = PILImage.open(logo_path).convert("RGBA")

                # optional: white background remove
                new_data = []
                for item in img.getdata():
                    if item[0] > 240 and item[1] > 240 and item[2] > 240:
                        new_data.append((255, 255, 255, 0))
                    else:
                        new_data.append(item)
                img.putdata(new_data)

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)

                logo_img = Image(buf, width=1.2*inch, height=0.8*inch)
            except Exception as e:
                print("Logo load error:", e)
    # -------- HEADER --------
    # elements.append(Paragraph(company["company_name"], title_style))
    # elements.append(Paragraph(company["address"], styles["Normal"]))
    header_table = Table(
    [[
        logo_img if logo_img else "",
        Paragraph(company["company_name"], title_style)
    ]],
    colWidths=[1.5*inch, doc.width - 1.5*inch]
    )

    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))

    elements.append(header_table)
    elements.append(Paragraph(company["address"], styles["Normal"]))
    elements.append(Spacer(1, 15))

    # -------- CHARTS --------
    chart_list = []
    # support both keys: chart / charts
    if isinstance(payload.get("charts"), list):
        chart_list = payload.get("charts")
    elif isinstance(payload.get("chart"), list):
        chart_list = payload.get("chart")
    # for c in payload.get("charts", []):
    #     img = generate_backend_chart(c)
    #     if img:
    #         chart_width = doc.width / 2 - 10
    #         chart_height = chart_width * 0.6
    #         charts.append(Image(img, width=chart_width, height=chart_height))
    charts = []
    for c in sorted(chart_list, key=lambda x: x.get("order", 0)):
        img = generate_backend_chart(c)
        if img:
            chart_width = doc.width / 2 - 10
            chart_height = chart_width * 0.6
            charts.append(Image(img, width=chart_width, height=chart_height))

    for i in range(0, len(charts), 2):
        row = charts[i:i+2]
        if len(row) < 2:
            row.append("")
        elements.append(Table([row], colWidths=[doc.width/2]*2))
        elements.append(Spacer(1, 20))

    # -------- TABLE --------
    table_data = [[Paragraph(col.upper(), th_style) for col in columns]]
    for r in rows:
        table_data.append([str(r[col]) for col in columns])

    col_w = doc.width / len(columns)
    table = Table(table_data, colWidths=[col_w]*len(columns), repeatRows=1)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F3F4F6")),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("FONTSIZE", (0,1), (-1,-1), 8),
    ]))

    elements.append(table)

    # -------- FOOTER --------
    def footer(canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(doc.pagesize[0]/2, 20, f"Page {doc.page}")
        canvas.drawRightString(doc.pagesize[0]-40, 20, "Generated by Sahajinsight")

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)

    # -------- SAVE --------
    os.makedirs("uploads/reportpdf", exist_ok=True)
    filename = f"{payload.get('report_title','Report')}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    path = f"uploads/reportpdf/{filename}"

    with open(path, "wb") as f:
        f.write(buffer.getvalue())

    return filename