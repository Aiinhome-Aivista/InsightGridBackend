import plotly.express as px
import pandas as pd
import plotly.io as pio
from io import BytesIO
from reportlab.lib.pagesizes import A4, A3, landscape


# kaleido = image exporter (pure pip)
pio.kaleido.scope.default_format = "png"
pio.kaleido.scope.default_width = 720
pio.kaleido.scope.default_height = 420

import plotly.graph_objects as go
import pandas as pd
from io import BytesIO
import plotly.io as pio

pio.kaleido.scope.default_format = "png"
pio.kaleido.scope.default_width = 900
pio.kaleido.scope.default_height = 480


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

        # ================= DATA =================
        if agg == "count":
            s = pd.Series(cols[0]["column_data"]).value_counts().sort_index()
            labels = s.index.astype(str).tolist()
            values = s.values.tolist()
        else:
            labels = [str(x) for x in cols[0]["column_data"]]
            values = cols[1]["column_data"]

        max_val = max(values) if values else 1

        # ================= TITLE (single line) =================
        full_title = title
        if subtitle:
            full_title = f"{title} · {subtitle}"

        # ================= BAR =================
        if chart_type == "bar":
            fig = go.Figure()

            fig.add_bar(
                x=labels,
                y=values,
                marker=dict(color=style.get("barColor", "#93C5FD")),
                width=0.45,
                text=values,
                textposition="outside",
                cliponaxis=False
            )

            fig.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white",
                height=480,
                margin=dict(l=50, r=30, t=70, b=55),

                title=dict(
                    text=full_title,
                    x=0,
                    xanchor="left",
                    font=dict(size=15, color="#111827")
                ),

                xaxis=dict(
                    title=chart_item.get("xAxis", "").upper(),
                    showgrid=False,
                    tickfont=dict(size=11)
                ),

                yaxis=dict(
                    range=[0, max_val + 1],
                    dtick=1,
                    gridcolor="#E5E7EB",
                    griddash="dot",
                    zeroline=False
                ),
            )

        # ================= PIE =================
        elif chart_type == "pie":
            fig = go.Figure(
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.58,
                    marker=dict(
                        colors=style.get("colors"),
                        line=dict(color="white", width=2)
                    ),
                    textinfo="percent",
                    textfont=dict(size=12)
                )
            )

            fig.update_layout(
                paper_bgcolor="white",
                height=480,
                margin=dict(l=40, r=40, t=70, b=40),

                title=dict(
                    text=full_title,
                    x=0,
                    xanchor="left",
                    font=dict(size=15)
                ),

                # 👇 legend INSIDE card
                legend=dict(
                    x=0.78,
                    y=0.5,
                    font=dict(size=11),
                    bgcolor="rgba(255,255,255,0)"
                )
            )

        # ================= LINE =================
        else:
            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=labels,
                    y=values,
                    mode="lines+markers",
                    line=dict(
                        color=style.get("lineColor", "#6366F1"),
                        width=3,
                        shape="spline"
                    ),
                    marker=dict(size=7)
                )
            )

            fig.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white",
                height=480,
                margin=dict(l=50, r=30, t=70, b=55),

                title=dict(
                    text=full_title,
                    x=0,
                    xanchor="left",
                    font=dict(size=15)
                ),

                xaxis=dict(
                    title=chart_item.get("xAxis", "").upper(),
                    showgrid=False
                ),

                #  LINE chart starts from 0
                yaxis=dict(
                    range=[0, max_val * 1.15],
                    gridcolor="#E5E7EB",
                    griddash="dot",
                    zeroline=False
                )
            )

        # ================= CARD BORDER =================
        fig.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0, y0=0, x1=1, y1=1,
            line=dict(color="#E5E7EB", width=1)
        )

        return BytesIO(fig.to_image(scale=2))

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
            lines = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().upper().startswith("DELIMITER")]
            return " ".join(lines).rstrip(";")
        except:
            return sql_text
    return sql_text
        