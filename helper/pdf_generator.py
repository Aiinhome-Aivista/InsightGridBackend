import os
import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from io import BytesIO
from PIL import Image as PILImage
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Image, Spacer
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from database.dbConnection import get_master_db

matplotlib.use('Agg')

def extract_select_query(sql_text):
    upper_sql = sql_text.upper()
    if "BEGIN" in upper_sql and "END" in upper_sql:
        try:
            body = sql_text.split("BEGIN", 1)[1]
            body = body.rsplit("END", 1)[0]
            lines = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().upper().startswith("DELIMITER")]
            return " ".join(lines).rstrip(";")
        except:
            return sql_text
    return sql_text

# def generate_backend_chart(chart_item):
#     try:
#         plt.clf() 
#         plt.figure(figsize=(6, 4))
#         chart_type = chart_item.get("chart_type", "Bar").lower()
#         chart_title = chart_item.get("chart_title", "Data Chart")
#         cols = chart_item.get("chart_column_details", [])

#         if not cols: return None

#         if len(cols) == 1:
#             data = pd.Series(cols[0].get("column_data", [])).value_counts()
#             labels, values = [str(x) for x in data.index], data.values.tolist()
#         else:
#             labels = [str(x) for x in cols[0].get("column_data", [])]
#             raw_vals = cols[1].get("column_data", [])
#             values = [float(str(v).replace(',', '')) if str(v).replace('.','',1).isdigit() else 0.0 for v in raw_vals]

#         if chart_type == "pie":
#             plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
#         elif chart_type == "line":
#             plt.plot(labels, values, marker='o', color='#1f77b4')
#         else:
#             plt.bar(labels, values, color='#3498db')

#         plt.title(chart_title, fontsize=10, fontweight='bold')
#         plt.xticks(rotation=45, ha='right', fontsize=8)
#         plt.tight_layout()
#         buf = io.BytesIO()
#         plt.savefig(buf, format='png', dpi=120)
#         plt.close()
#         buf.seek(0)
#         return buf
#     except: return None


# def generate_backend_chart(chart_item):
#     try:
#         plt.clf()
#         plt.figure(figsize=(6, 4))

#         chart_type = chart_item.get("type", "bar").lower()
#         chart_title = chart_item.get("customTitle", "Data Chart")
#         style = chart_item.get("style", {})

#         cols = chart_item.get("chart_column_details", [])
#         if len(cols) < 2:
#             return None

#         labels = [str(x) for x in cols[0]["column_data"][:25]]
#         values = [float(v) for v in cols[1]["column_data"][:25]]

#         if chart_type == "pie":
#             plt.pie(values, labels=labels, autopct='%1.1f%%')
#         elif chart_type == "line":
#             plt.plot(labels, values, marker='o',
#                      color=style.get("lineColor", "#1f77b4"))
#         else:
#             plt.bar(labels, values,
#                     color=style.get("barColor", "#3498db"))

#         plt.title(chart_title, fontsize=10, fontweight='bold')
#         plt.xticks(rotation=45, ha='right', fontsize=7)
#         plt.tight_layout()

#         buf = io.BytesIO()
#         plt.savefig(buf, format="png", dpi=120)
#         plt.close()
#         buf.seek(0)
#         return buf

#     except Exception as e:
#         print("Chart error:", e)
#         return None

def generate_backend_chart(chart_item):
    try:
        plt.close('all')

        chart_type = chart_item.get("type", "bar").lower()
        title = chart_item.get("customTitle", "Chart")
        subtitle = chart_item.get("subtitle", "")
        style = chart_item.get("style", {})
        agg = chart_item.get("agg", "").lower()

        cols = chart_item.get("chart_column_details", [])
        if not cols:
            return None

        # ---------------- DATA ----------------
        if agg == "count":
            data = pd.Series(cols[0]["column_data"]).value_counts()
            labels = data.index.tolist()
            values = data.values.tolist()
        else:
            if len(cols) < 2:
                return None
            labels = cols[0]["column_data"]
            values = [float(v) for v in cols[1]["column_data"]]

        # ---------------- FIG / AX ----------------
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor("white")

        # ================= PIE =================
        if chart_type == "pie":
            colors_list = style.get("colors")

            wedges, texts, autotexts = ax.pie(
                values,
                startangle=140,
                colors=colors_list,
                autopct='%1.0f%%',
                pctdistance=1.08,        # ✅ outside but inside card
                wedgeprops=dict(
                    width=0.45,
                    edgecolor="white"
                )
            )

            # percentage color = slice color
            for i, t in enumerate(autotexts):
                t.set_color(wedges[i].get_facecolor())
                t.set_fontsize(9)
                t.set_weight("bold")

            # legend INSIDE right
            ax.legend(
                wedges,
                labels,
                loc="center right",
                bbox_to_anchor=(0.95, 0.5),
                frameon=False,
                fontsize=9,
                handlelength=1
            )

            ax.axis("equal")

        # ================= BAR =================
        elif chart_type == "bar":
            bars = ax.bar(
                labels,
                values,
                color=style.get("barColor", "#93C5FD"),
                width=0.45
            )

            # 👉 bars একটু center এ আনতে
            ax.margins(x=0.1)

            # 👉 dynamic max (safe)
            max_val = max([v for v in values if v > 0], default=1)

            # 👉 top এ space রাখার জন্য
            upper = max_val * 1.3

            # 👉 nice rounded Y limit
            def round_up(n):
                if n <= 5:
                    return int(n) + 1
                magnitude = 10 ** int(len(str(int(n))) - 1)
                return int(((n + magnitude - 1) // magnitude) * magnitude)

            y_max = round_up(upper)
            ax.set_ylim(0, y_max)

            # 👉 dynamic ticks
            ax.yaxis.set_major_locator(
                matplotlib.ticker.MaxNLocator(nbins=5, integer=True)
            )

            # 👉 light dotted grid (UI like)
            ax.yaxis.grid(
                True,
                linestyle=(0, (2, 4)),
                linewidth=0.6,
                alpha=0.35
            )
            ax.set_axisbelow(True)

            # 👉 label styling
            ax.tick_params(axis='x', rotation=20, labelsize=8)
            ax.tick_params(axis='y', labelsize=8)

            # 👉 X axis title
            if chart_item.get("xAxis"):
                ax.set_xlabel(
                    chart_item["xAxis"].upper(),
                    fontsize=8,
                    color="#6B7280",
                    labelpad=6
                )
        
        # ================= LINE =================
        elif chart_type == "line":
            ax.plot(
                labels,
                values,
                marker='o',
                linewidth=2,
                color=style.get("lineColor", "#2563EB")
            )
            ax.tick_params(axis='x', rotation=20, labelsize=8)
            ax.tick_params(axis='y', labelsize=8)

        # ---------------- TITLE ----------------
        ax.set_title(
            title,
            loc="left",
            fontsize=11,
            fontweight="bold",
            pad=8
        )

        # ---------------- SUBTITLE ----------------
        if subtitle:
            ax.text(
                0.0, 0.93,
                subtitle,
                transform=ax.transAxes,
                fontsize=9,
                color="#6B7280",
                ha="left"
            )

        # ---------------- CARD BORDER ----------------
        ax.set_frame_on(True)
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_edgecolor("#E5E7EB")
            spine.set_linewidth(1)

        # ---------------- SAVE ----------------
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=120,
            bbox_inches="tight",
            pad_inches=0.2
        )
        plt.close(fig)
        buf.seek(0)
        return buf

    except Exception as e:
        print("Chart error:", e)
        return None


def generate_report_pdf(session_id, payload, company_db):
    try:
        cursor = company_db.cursor(dictionary=True)
        cursor.execute("SELECT company_id FROM users WHERE session_id = %s LIMIT 1", (session_id,))
        user_row = cursor.fetchone()
        company_id = user_row["company_id"] if user_row else None

        master_db = get_master_db()
        mcur = master_db.cursor(dictionary=True)
        mcur.execute("SELECT company_name, address, company_logo FROM companies WHERE id=%s", (company_id,))
        company_info = mcur.fetchone() or {}
        mcur.close()
        master_db.close()

        raw_query = payload.get("query", "")
        clean_query = extract_select_query(raw_query)
        cursor.execute(clean_query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        buffer = BytesIO()
        col_count = len(columns)
        pagesize = portrait(A4) if col_count <= 8 else landscape(A4)
        doc = SimpleDocTemplate(buffer, pagesize=pagesize, leftMargin=40, rightMargin=40, topMargin=30, bottomMargin=40)
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="CustomCompanyName", fontSize=18, fontName="Helvetica-Bold"))
        styles.add(ParagraphStyle(name="CustomAddress", fontSize=11, textColor=colors.grey))
        
        elements = []

        # --- Header Section ---
        logo_img = None
        logo_path = company_info.get("company_logo", "").lstrip("/")
        if logo_path and os.path.exists(logo_path):
            try:
                img = PILImage.open(logo_path).convert("RGBA")
                newData = [(255, 255, 255, 0) if item[0] > 240 and item[1] > 240 and item[2] > 240 else item for item in img.getdata()]
                img.putdata(newData)
                bbox = img.getbbox()
                if bbox: img = img.crop(bbox)
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="PNG")
                logo_img = Image(img_buffer, width=0.8 * inch, height=0.6 * inch)
            except:
                logo_img = None

        h_table = Table([[logo_img, Paragraph(company_info.get("company_name", ""), styles["CustomCompanyName"])]], colWidths=[1*inch, doc.width-1*inch])
        h_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        elements.extend([h_table, Paragraph(company_info.get("address", ""), styles["CustomAddress"]), Spacer(1, 10)])

        # --- Horizontal Line ---
        line_table = Table([[""]], colWidths=[doc.width])
        line_table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, colors.black)]))
        elements.extend([line_table, Spacer(1, 20)])

        # --- Charts ---
        # chart_list = payload.get("chart", [])
        chart_list = []


        if isinstance(payload.get("charts"), list) and payload.get("charts"):
           chart_list = payload.get("charts")
        elif isinstance(payload.get("chart"), list) and payload.get("chart"):
           chart_list = payload.get("chart")
        chart_images = []
        for c in chart_list:
            c_buf = generate_backend_chart(c)
            if c_buf:
                chart_images.append(Image(c_buf, width=doc.width/2.2, height=doc.width/2.2*0.7))
        
        if chart_images:
            grid = [chart_images[i:i+2] for i in range(0, len(chart_images), 2)]
            for r in grid: 
                if len(r) < 2: r.append("")
            t = Table(grid, colWidths=[doc.width/2]*2)
            t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('BOTTOMPADDING', (0,0), (-1,-1), 15)]))
            elements.append(t)

        t_font = 8 if col_count < 10 else 7
        c_style = ParagraphStyle("cell", fontSize=t_font)
        t_data = [[Paragraph(f"<b>{c.upper()}</b>", c_style) for c in columns]]
        for r in rows:
            t_data.append([Paragraph(str(r.get(c, "") or ""), c_style) for c in columns])

        data_t = Table(t_data, colWidths=[(doc.width-10)/col_count]*col_count, repeatRows=1)
        data_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F3F4F6")), 
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightskyblue),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        elements.append(data_t)

        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            page_number_text = f"Page {doc.page}"
            canvas.drawCentredString(pagesize[0]/2, 20, page_number_text)
            canvas.restoreState()

        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
        
        save_dir = os.path.join("uploads", "reportpdf")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_title = payload.get('report_title', 'Report').replace(' ', '_')
        filename = f"{report_title}_{timestamp}.pdf"
        file_path = os.path.join(save_dir, filename)

        with open(file_path, "wb") as f:
            f.write(buffer.getvalue())

        buffer.seek(0)
        return filename 

    except Exception as e:
        raise Exception(f"Error: {str(e)}")