import plotly.graph_objects as go
import pandas as pd
from io import BytesIO
import plotly.io as pio
from reportlab.lib.pagesizes import A4, A3, landscape
import math

# REMOVE all default_width / height
pio.kaleido.scope.default_format = "png"

def get_nice_yaxis(max_val):
    """
    Always starts from 0
    Small → 0,2,4,6…
    Large → 0,200,400…
    """
    if max_val <= 5:
        step = 2
    elif max_val <= 10:
        step = 2
    elif max_val <= 50:
        step = 10
    elif max_val <= 100:
        step = 20
    elif max_val <= 500:
        step = 100
    elif max_val <= 1000:
        step = 200
    elif max_val <= 5000:
        step = 500
    else:
        step = 1000

    # nearest clean block ABOVE max_val
    base_max = math.ceil(max_val / step) * step

    #FORCE one extra block for visual height
    visual_max = base_max + step

    return visual_max, step

def get_contrast_text_color(hex_color):
    if not hex_color:
        return "#111827"
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "#111827" if brightness > 160 else "#FFFFFF"


# ---------------- MAIN CHART BUILDER ----------------
def generate_backend_chart(chart_item):
    try:
        chart_type = chart_item.get("type", "bar").lower()
        title = chart_item.get("customTitle", "")
        subtitle = chart_item.get("subtitle", "")
        style = chart_item.get("style", {})
        agg = chart_item.get("agg", "").lower()

        cols = chart_item.get("chart_column_details", [])
        if not cols:
            return None

        # ---------- DATA ----------
        if agg == "count":
            s = pd.Series(cols[0]["column_data"]).value_counts().sort_index()
            labels = s.index.astype(str).tolist()
            values = s.values.tolist()
        else:
            labels = [str(x) for x in cols[0]["column_data"]]
            values = cols[1]["column_data"]

        max_val = max(values) if values else 1

        full_title = title
        if subtitle:
            full_title = f"{title} · {subtitle}"

        # ================= BAR =================
        if chart_type == "bar":
            bar_color = style.get("barColor", "#93C5FD")
            text_color = get_contrast_text_color(bar_color)
            y_max, y_step = get_nice_yaxis(max_val)
            
            visible_max = y_max - y_step
            top_padding = visible_max * 0.15
            final_range_max = visible_max + top_padding
            fig = go.Figure()
            fig.add_bar(
                x=labels,
                y=values,
                text=values,
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color=text_color, size=12),
                width=0.45,
                marker=dict(
                color=bar_color,
                line=dict(color="#7DAAFB", width=1),  # optional soft border
                cornerradius=6                          #  THIS IS THE KEY
            ),
                cliponaxis=False
            )

            fig.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(l=45, r=20, t=60, b=45),
                title=dict(text=full_title, x=0, xanchor="left", font=dict(size=14)),
                xaxis=dict(
                    title=chart_item.get("xAxis", "").upper(),
                    showgrid=False,
                    tickfont=dict(size=11)
                ),
                
                yaxis=dict(
                      range=[0, final_range_max],
                        dtick=y_step,

                        showgrid=True,
                        gridcolor="#9CA3AF",
                        gridwidth=1.4,
                        griddash="dot",

                        zeroline=True,
                        zerolinecolor="#6B7280",
                        zerolinewidth=1.6,

                        tickfont=dict(
                            size=11,
                            color="#111827",
                            weight="bold"
                        ),

                        autorange=False
                ),
                bargap=0.45
            )

        # ================= PIE =================
        elif chart_type == "pie":
            fig = go.Figure(
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.58,
                    sort=False,
                    textinfo="percent",
                    textfont=dict(size=11),
                    marker=dict(
                        colors=style.get("colors"),
                        line=dict(color="white", width=2)
                    ),
                    domain=dict(x=[0.05, 0.85], y=[0.05, 0.95])
                )
            )

            fig.update_layout(
                paper_bgcolor="white",
                margin=dict(l=30, r=30, t=60, b=30),
                title=dict(text=full_title, x=0, xanchor="left", font=dict(size=14)),
                legend=dict(
                    x=0.78,
                    y=0.5,
                    xanchor="left",
                    yanchor="middle",
                    font=dict(size=11),
                    bgcolor="rgba(255,255,255,0)"
                )
            )

        # ================= LINE =================
        # ================= LINE =================
        else:
            line_color = style.get("lineColor", "#6366F1")
            dot_colors = style.get("colors")   # ADD THIS

            y_max, y_step = get_nice_yaxis(max_val)
            visible_max = y_max - y_step
            top_padding = visible_max * 0.15
            final_range_max = visible_max + top_padding

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=labels,
                    y=values,
                    mode="lines+markers",
                    line=dict(
                        color=line_color,
                        width=3,
                        shape="spline"
                    ),
                    marker=dict(
                        size=7,
                        color=dot_colors if dot_colors and len(dot_colors) == len(values) else line_color
                    )
                )
            )

            fig.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(l=45, r=20, t=60, b=45),
                title=dict(text=full_title, x=0, xanchor="left", font=dict(size=14)),
                xaxis=dict(
                    title=chart_item.get("xAxis", "").upper(),
                    showgrid=False
                ),
                yaxis=dict(
                    range=[0, final_range_max],
                    dtick=y_step,
                    showgrid=True,
                    gridcolor="#9CA3AF",
                    gridwidth=1.4,
                    griddash="dot",
                    zeroline=True,
                    zerolinecolor="#6B7280",
                    zerolinewidth=1.6,
                    tickfont=dict(size=11, color="#111827", weight="bold"),
                    autorange=False
                )
            )


        # ---------- EXPORT ----------
        return BytesIO(
            fig.to_image(
                format="png",
                width=860,
                height=380,
                scale=1
            )
        )

    except Exception as e:
        print("Chart error:", e)
        return None




def get_pagesize_by_columns(col_count):
    if col_count <= 8:
        return A4
    elif col_count <= 14:
        return landscape(A4)
    else:
        return landscape(A3)


def extract_select_query(sql_text):
    upper_sql = sql_text.upper()
    if "BEGIN" in upper_sql and "END" in upper_sql:
        try:
            body = sql_text.split("BEGIN", 1)[1]
            body = body.rsplit("END", 1)[0]
            lines = [
                line.strip()
                for line in body.splitlines()
                if line.strip() and not line.strip().upper().startswith("DELIMITER")
            ]
            return " ".join(lines).rstrip(";")
        except:
            return sql_text
    return sql_text
