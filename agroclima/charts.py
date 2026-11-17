"""Gráficas Plotly con la identidad visual de Viticultura del Norte.

Reglas: un único eje Y por gráfica (dos medidas → subgráficas), paleta categórica
fija (vino → cielo → oro; validada para daltonismo), divergentes centradas en 0.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import BRAND, MONTHS_ES

TMAX, TMEAN, TMIN = BRAND["s3"], BRAND["s2"], BRAND["s1"]
RAIN, ET0 = BRAND["s1_light"], BRAND["s3"]
BAND_FILLS = ["rgba(59,47,134,.07)", "rgba(31,122,74,.08)", "rgba(179,165,50,.12)", "rgba(33,24,69,.04)"]
TEMP_SCALE = [[0, "#2A2165"], [0.25, "#8F87C9"], [0.5, "#F4F3F0"], [0.75, "#D9C77A"], [1, "#7A5F0E"]]
WET_SCALE = [[0, "#7A5F0E"], [0.25, "#D9C77A"], [0.5, "#F4F3F0"], [0.75, "#7FB596"], [1, "#0F4D2B"]]
TITLE_FONT = "Cormorant Garamond, Georgia, serif"


def style(fig, height=420, title=None, unified=True):
    fig.update_layout(
        template="plotly_white", height=height, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, system-ui, sans-serif", color=BRAND["ink"], size=12.5),
        title=dict(text=title, font=dict(family=TITLE_FONT, size=21, color=BRAND["indigo"], weight=600), x=0.005, xanchor="left") if title else None,
        margin=dict(l=10, r=10, t=56 if title else 20, b=10),
        legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="left", x=0, title_text=""),
        hovermode="x unified" if unified else "closest",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BRAND["line"], font_color=BRAND["ink"]),
    )
    fig.update_xaxes(showgrid=False, linecolor=BRAND["line"], ticks="outside", tickcolor=BRAND["line"])
    fig.update_yaxes(gridcolor="#EFEDF2", zerolinecolor=BRAND["line"])
    return fig


def spanish_month_axis(fig, start, end, **kw):
    """Ticks de mes en español para ejes de fecha (Plotly no localiza los nombres)."""
    ticks = pd.date_range(pd.Timestamp(start).to_period("M").to_timestamp(), end, freq="MS")
    fig.update_xaxes(tickvals=ticks, ticktext=[MONTHS_ES[t.month - 1] for t in ticks], title=None, **kw)
    return fig


def climograph(norm: pd.DataFrame) -> go.Figure:
    x = [MONTHS_ES[m - 1] for m in norm.index]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.55, 0.45],
                        subplot_titles=("Temperatura (°C)", "Precipitación y ET0 (mm/mes)"))
    fig.add_trace(go.Scatter(x=x, y=norm["T máx media (°C)"], name="T máx", line=dict(color=TMAX, width=2),
                             mode="lines+markers", marker=dict(size=8)), 1, 1)
    fig.add_trace(go.Scatter(x=x, y=norm["T mín media (°C)"], name="T mín", line=dict(color=TMIN, width=2),
                             mode="lines+markers", marker=dict(size=8), fill="tonexty",
                             fillcolor="rgba(179,165,50,.08)"), 1, 1)
    fig.add_trace(go.Scatter(x=x, y=norm["T media (°C)"], name="T media", line=dict(color=BRAND["muted"], width=1.5, dash="dot"),
                             mode="lines"), 1, 1)
    fig.add_trace(go.Bar(x=x, y=norm["Precipitación (mm)"], name="Precipitación", marker_color=RAIN,
                         marker_line_width=0), 2, 1)
    fig.add_trace(go.Scatter(x=x, y=norm["ET0 (mm)"], name="ET0", line=dict(color=BRAND["s2"], width=2),
                             mode="lines+markers", marker=dict(size=8)), 2, 1)
    fig.update_traces(hovertemplate="%{y:.1f}")
    fig.update_layout(bargap=0.35)
    for a in fig.layout.annotations:
        a.update(x=0, xanchor="left", font=dict(size=12, color=BRAND["muted"]))
    return style(fig, height=560, title="Climograma: normales mensuales del periodo")


def index_series(annual: pd.DataFrame, col: str, classes=None, unit="", trend_row=None) -> go.Figure:
    d = annual[["Campaña", col]].dropna()
    fig = go.Figure()
    if classes and not d.empty:
        lo, hi = d[col].min(), d[col].max()
        pad = (hi - lo) * 0.15 or abs(hi) * 0.1 or 1
        ymin, ymax = lo - pad, hi + pad
        prev = -np.inf
        for i, (upper, label) in enumerate(classes):
            top = np.inf if upper is None else upper
            y0, y1 = max(prev, ymin), min(top, ymax)
            if y1 > y0:
                fig.add_hrect(y0=y0, y1=y1, fillcolor=BAND_FILLS[i % len(BAND_FILLS)], line_width=0, layer="below",
                              annotation_text=label, annotation_position="top left",
                              annotation_font=dict(size=11, color=BRAND["muted"]))
            prev = top
        fig.update_yaxes(range=[ymin, ymax])
    fig.add_trace(go.Scatter(x=d["Campaña"], y=d[col], mode="lines+markers", name=col,
                             line=dict(color=BRAND["s1"], width=2), marker=dict(size=8, line=dict(color="#fff", width=2)),
                             hovertemplate=f"%{{x}}: %{{y:,.1f}} {unit}<extra></extra>"))
    if not d.empty:
        fig.add_hline(y=d[col].mean(), line=dict(color=BRAND["muted"], width=1, dash="dash"),
                      annotation_text=f"media {d[col].mean():,.0f} {unit}" if abs(d[col].mean()) >= 100
                      else f"media {d[col].mean():,.1f} {unit}",
                      annotation_position="bottom right", annotation_font=dict(color=BRAND["muted"], size=11))
    if trend_row is not None and len(d) >= 8:
        from scipy import stats
        sen = stats.theilslopes(d[col], d["Campaña"])
        xs = np.array([d["Campaña"].min(), d["Campaña"].max()])
        fig.add_trace(go.Scatter(x=xs, y=sen.intercept + sen.slope * xs, mode="lines", name="Tendencia (Sen)",
                                 line=dict(color=BRAND["s2"], width=2), hoverinfo="skip"))
    fig.update_xaxes(dtick=5 if len(d) > 25 else 2 if len(d) > 12 else 1, tickangle=0, title=None)
    return style(fig, height=420, title=col, unified=False)


def cumulative_chart(cum: pd.DataFrame, highlight: int, base_temp: float) -> go.Figure:
    complete = cum[cum["Completa"]]
    band = complete.groupby("Día").agg(
        ref=("Fecha ref", "first"), p10=("GDD acumulado", lambda s: s.quantile(.1)),
        p50=("GDD acumulado", "median"), p90=("GDD acumulado", lambda s: s.quantile(.9)))
    fig = go.Figure()
    for yr, part in cum.groupby("Campaña"):
        if yr == highlight:
            continue
        fig.add_trace(go.Scatter(x=part["Fecha ref"], y=part["GDD acumulado"], mode="lines", showlegend=False,
                                 line=dict(color="rgba(107,104,120,.16)", width=1), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=band["ref"], y=band["p90"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=band["ref"], y=band["p10"], fill="tonexty", fillcolor="rgba(179,165,50,.22)",
                             line=dict(width=0), name="Rango P10–P90", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=band["ref"], y=band["p50"], name="Mediana", line=dict(color=BRAND["olive"], width=2),
                             hovertemplate="Mediana: %{y:,.0f}<extra></extra>"))
    h = cum[cum["Campaña"] == highlight]
    fig.add_trace(go.Scatter(x=h["Fecha ref"], y=h["GDD acumulado"], name=f"Campaña {highlight}",
                             line=dict(color=BRAND["s1"], width=3),
                             hovertemplate=f"{highlight}: %{{y:,.0f}}<extra></extra>"))
    spanish_month_axis(fig, cum["Fecha ref"].min(), cum["Fecha ref"].max())
    fig.update_yaxes(title=f"GDD acumulado (base {base_temp:g} °C)")
    return style(fig, height=460, title="Acumulación de grados-día en la temporada")


def anomaly_heatmap(matrix: pd.DataFrame, title: str, unit: str, scale: str) -> go.Figure:
    lim = np.nanpercentile(np.abs(matrix.to_numpy()), 98) if matrix.size else 1
    fig = go.Figure(go.Heatmap(
        z=matrix.to_numpy(), x=[MONTHS_ES[m - 1] for m in matrix.columns], y=matrix.index.astype(str),
        colorscale=scale, zmid=0, zmin=-lim, zmax=lim, xgap=2, ygap=2,
        colorbar=dict(title=unit, thickness=12, outlinewidth=0),
        hovertemplate="%{y} · %{x}: %{z:+.1f} " + unit + "<extra></extra>"))
    fig.update_yaxes(autorange="reversed", dtick=2 if len(matrix) > 20 else 1)
    return style(fig, height=max(360, 22 * len(matrix) + 120), title=title, unified=False)


def monthly_box(monthly: pd.DataFrame, col: str, color: str) -> go.Figure:
    d = monthly[[col]].dropna().copy()
    d["mes"] = [MONTHS_ES[m - 1] for m in d.index.month]
    d["año"] = d.index.year
    fig = go.Figure(go.Box(x=d["mes"], y=d[col], marker_color=color, line_width=1.5, boxpoints="outliers",
                           customdata=d["año"], hovertemplate="%{x} %{customdata}: %{y:.1f}<extra></extra>",
                           name=col, showlegend=False))
    return style(fig, height=380, title=f"Variabilidad interanual · {col}", unified=False)


def water_bars(annual: pd.DataFrame) -> go.Figure:
    d = annual[["Campaña", "Balance P − ET0 temporada (mm)"]].dropna()
    col = "Balance P − ET0 temporada (mm)"
    colors = [BRAND["s2"] if v >= 0 else BRAND["s3"] for v in d[col]]
    fig = go.Figure(go.Bar(x=d["Campaña"], y=d[col], marker_color=colors, marker_line_width=0,
                           hovertemplate="%{x}: %{y:,.0f} mm<extra></extra>", showlegend=False))
    fig.add_hline(y=0, line=dict(color=BRAND["muted"], width=1))
    fig.update_xaxes(dtick=5 if len(d) > 25 else 2, tickangle=0)
    return style(fig, height=380, title="Balance hídrico climático de la temporada (P − ET0)", unified=False)


def frost_dots(annual: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, color, name in [("Última helada primaveral", TMIN, "Última helada primaveral"),
                             ("Primera helada otoñal", TMAX, "Primera helada otoñal")]:
        s = pd.to_datetime(annual[col])
        ok = s.notna()
        if not ok.any():
            continue
        ref = pd.to_datetime("2001-01-01") + pd.to_timedelta(s[ok].dt.day_of_year - 1, unit="D")
        fig.add_trace(go.Scatter(x=ref, y=annual.loc[ok, "Campaña"], mode="markers", name=name,
                                 marker=dict(size=10, color=color, line=dict(color="#fff", width=2)),
                                 customdata=s[ok].dt.strftime("%d/%m/%Y"),
                                 hovertemplate="%{customdata}<extra>" + name + "</extra>"))
    spanish_month_axis(fig, "2001-01-01", "2001-12-31", range=["2001-01-01", "2001-12-31"])
    fig.update_yaxes(autorange="reversed", title="Campaña", dtick=5 if len(annual) > 25 else 2)
    return style(fig, height=max(360, 16 * len(annual) + 120), title="Fechas de helada (Tmin ≤ umbral)", unified=False)


def small_bars(df: pd.DataFrame, col: str, unit: str) -> go.Figure:
    d = df[["Campaña", col]].dropna()
    fig = go.Figure(go.Bar(x=d["Campaña"], y=d[col], marker_color=BRAND["s1"], marker_line_width=0,
                           hovertemplate=f"%{{x}}: %{{y:,.0f}} {unit}<extra></extra>", showlegend=False))
    fig.update_yaxes(rangemode="tozero", tickformat=",.0f", **({"dtick": 1} if d[col].max() <= 5 else {}))
    fig.update_xaxes(dtick=5 if len(d) > 25 else 2, tickangle=0)
    return style(fig, height=300, title=col, unified=False)


def compare_sites(table: pd.DataFrame, col: str) -> go.Figure:
    d = table.sort_values(col)
    fig = go.Figure(go.Bar(x=d[col], y=d["Finca"], orientation="h", marker_color=BRAND["s1"],
                           marker_line_width=0, text=d[col].map(lambda v: f"{v:,.1f}" if abs(v) < 100 else f"{v:,.0f}"),
                           textposition="outside", hovertemplate="%{y}: %{x:,.1f}<extra></extra>", showlegend=False))
    return style(fig, height=110 + 42 * len(d), title=col, unified=False)
