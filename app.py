"""Analizador agroclimático · Viticultura del Norte."""
import html
import re
from datetime import date

import folium
import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

from agroclima import charts
from agroclima.api import fetch_power, last_available_day, merra2_cell
from agroclima.config import (
    BRAND, COOL_NIGHT_CLASSES, DRYNESS_CLASSES, FIRST_YEAR, GST_CLASSES, HUGLIN_CLASSES, MONTHS_ES,
    REQUIRED, SEASONS, VARIETY_GUIDE, WINKLER_CLASSES,
)
from agroclima.export import excel_report
from agroclima import indices as ix
from agroclima import theme

st.set_page_config(page_title="Agroclima · Viticultura del Norte", page_icon=theme.FAVICON, layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(theme.CSS, unsafe_allow_html=True)


# ------------------------------------------------------------- utilidades
def fmt(v, dec=0, unit=""):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    s = f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {unit}".strip()


def kpi(label, value, badge=None, sub=None):
    b = f'<div class="b">{html.escape(badge)}</div>' if badge else ""
    s = f'<div class="s">{html.escape(sub)}</div>' if sub else ""
    return f'<div class="kpi"><div class="l">{html.escape(label)}</div><div class="v">{value}</div>{b}{s}</div>'


def step(n, text):
    st.markdown(theme.section(f"{n:02d}", text), unsafe_allow_html=True)


DMS = re.compile(r"""(\d+(?:[.,]\d+)?)\s*[°º]\s*(?:(\d+(?:[.,]\d+)?)\s*['’′]\s*)?(?:(\d+(?:[.,]\d+)?)\s*(?:"|''|”|″)\s*)?([NSEOW])""", re.I)


def parse_coords(text: str):
    """Acepta '28.44, -106.18', '28,44; -106,18' o DMS 28°26'24"N 106°11'7"W."""
    text = text.strip()
    found = DMS.findall(text)
    if len(found) == 2:
        vals = []
        for d, m, s, h in found:
            v = float(d.replace(",", ".")) + float((m or "0").replace(",", ".")) / 60 + float((s or "0").replace(",", ".")) / 3600
            vals.append(-v if h.upper() in "SWO" else v)
        return vals[0], vals[1]
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(", ", " ").replace(";", " ")) if "." in text else \
        [n.replace(",", ".") for n in re.findall(r"-?\d+(?:,\d+)?", text.replace(";", " "))]
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    raise ValueError


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def cached_fetch(lat, lon, start, end):
    return fetch_power(lat, lon, start, end)


@st.cache_data(show_spinner=False)
def compute(raw, lat, elevation, base, frost, heat, cov, harvest):
    s = ix.Settings(base_temp=base, frost_temp=frost, heat_temp=heat, min_coverage=cov, harvest_months=harvest)
    daily = ix.enrich_daily(raw, lat, elevation, s)
    annual = ix.campaign_indices(daily, lat, s)
    monthly = ix.monthly_table(daily, cov)
    return daily, annual, monthly, ix.normals(monthly), ix.trends(annual), ix.cumulative_gdd(daily, lat)


# ------------------------------------------------------------------ estado
DEFAULTS = {"lat": 28.440148, "lon": -106.185296, "name": "Finca Aurora", "sites": {}, "result": None, "_click": None}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def apply_paste():
    try:
        lat, lon = parse_coords(st.session_state.paste)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError
        st.session_state.lat, st.session_state.lon = round(lat, 6), round(lon, 6)
        st.session_state.paste_error = None
    except ValueError:
        st.session_state.paste_error = "No se reconocieron las coordenadas. Ejemplos: 28.4401, -106.1853 · 28°26'24\"N 106°11'7\"W"


# ----------------------------------------------------------------- sidebar
this_year = date.today().year
with st.sidebar:
    st.markdown(theme.side_brand_html(), unsafe_allow_html=True)
    st.markdown("### Parámetros de análisis")
    years = st.slider("Periodo (campañas)", FIRST_YEAR, this_year, (1991, this_year),
                      help="La campaña se nombra por el año de vendimia. Incluye el año en curso para seguir la campaña actual frente a la climatología.")
    st.caption("Normal climatológica OMM: 1991–2020.")
    with st.expander("Umbrales agronómicos", expanded=False):
        base = st.number_input("Temperatura base GDD (°C)", 0.0, 15.0, 10.0, 0.5)
        frost = st.number_input("Umbral de helada (Tmín, °C)", -5.0, 3.0, 0.0, 0.5,
                                help="Tmín de rejilla a 2 m. En fondos de valle la helada real suele ser más intensa; prueba +1 o +2 °C para ser conservador.")
        heat = st.number_input("Umbral de calor (Tmáx, °C)", 30.0, 42.0, 35.0, 0.5)
        hem = "N" if st.session_state.lat >= 0 else "S"
        harvest = st.multiselect("Meses de vendimia", list(range(1, 13)), default=list(SEASONS[hem].harvest),
                                 format_func=lambda m: MONTHS_ES[m - 1], key=f"harvest_{hem}")
        cov = st.slider("Cobertura mínima de datos", 0.80, 1.0, 0.95, 0.01, format="%.2f")
    if st.session_state.sites:
        st.markdown("### Fincas guardadas")
        for nm, site in list(st.session_state.sites.items()):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{html.escape(nm)}**  \n<small>{site['lat']:.4f}, {site['lon']:.4f}</small>", unsafe_allow_html=True)
            if c2.button("✕", key=f"del_{nm}", help="Quitar de la comparación"):
                del st.session_state.sites[nm]
                st.rerun()
    st.markdown("---")
    st.caption("Datos: NASA POWER (MERRA-2, CERES). Reanálisis en rejilla: no sustituye a una estación local.")

# -------------------------------------------------------------------- hero
st.markdown(theme.hero_html(), unsafe_allow_html=True)

# ---------------------------------------------------------- 1. ubicación
step(1, "Ubica la finca")
map_col, form_col = st.columns([1.6, 1], gap="large")

with map_col:
    lat0, lon0 = st.session_state.lat, st.session_state.lon
    fmap = folium.Map(location=[lat0, lon0], zoom_start=14, tiles=None, control_scale=True,
                      attribution_control=True, prefer_canvas=True)
    folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Esri, Maxar", name="Satélite", max_zoom=19, show=True).add_to(fmap)
    folium.TileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap, OSM",
                     name="Topográfico", max_zoom=17, show=False).add_to(fmap)
    folium.TileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", attr="© OpenStreetMap",
                     name="Callejero", max_zoom=19, show=False).add_to(fmap)
    folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
                     attr="Esri", name="Etiquetas", overlay=True, control=True, show=True).add_to(fmap)
    fmap.get_root().html.add_child(folium.Element(
        "<style>.leaflet-control-attribution{font-size:9px!important;max-width:60%;white-space:nowrap;"
        "overflow:hidden;text-overflow:ellipsis}</style>"))
    sw, ne = merra2_cell(lat0, lon0)
    folium.Rectangle([sw, ne], color=BRAND["olive_light"], weight=2, fill=True, fill_opacity=0.05, dash_array="6 6",
                     tooltip="Celda de reanálisis MERRA-2 (~0,5° × 0,625°) que representa los datos").add_to(fmap)
    for nm, site in st.session_state.sites.items():
        folium.CircleMarker([site["lat"], site["lon"]], radius=6, color="#fff", weight=2, fill=True,
                            fill_color=BRAND["s3"], fill_opacity=1, tooltip=nm).add_to(fmap)
    pin = (f'<div style="width:38px;height:38px;border-radius:50%;background:#fff;padding:3px;'
           f'box-shadow:0 0 0 3px {BRAND["indigo"]},0 6px 14px rgba(0,0,0,.45)">{theme.LOGO_SVG}</div>')
    folium.Marker([lat0, lon0], tooltip=st.session_state.name,
                  icon=folium.DivIcon(html=pin, icon_size=(38, 38), icon_anchor=(19, 19))).add_to(fmap)
    folium.LayerControl(collapsed=True).add_to(fmap)
    out = st_folium(fmap, key="map", height=470, use_container_width=True, returned_objects=["last_clicked"])
    click = (out or {}).get("last_clicked")
    if click and (click["lat"], click["lng"]) != st.session_state._click:
        st.session_state._click = (click["lat"], click["lng"])
        st.session_state.lat = round(click["lat"], 6)
        st.session_state.lon = round(((click["lng"] + 180) % 360) - 180, 6)
        st.rerun()
    st.caption("Haz clic en el mapa para situar la finca. El recuadro discontinuo muestra la celda de reanálisis que representa los datos (~50 km).")

with form_col:
    st.text_input("Nombre de la finca", key="name")
    st.text_input("Pegar coordenadas (Google Maps, GPS…)", key="paste", on_change=apply_paste,
                  placeholder="28.440148, -106.185296")
    if st.session_state.get("paste_error"):
        st.warning(st.session_state.paste_error)
    c1, c2 = st.columns(2)
    c1.number_input("Latitud", -90.0, 90.0, key="lat", format="%.6f", step=0.001)
    c2.number_input("Longitud", -180.0, 180.0, key="lon", format="%.6f", step=0.001)
    hem = "N" if st.session_state.lat >= 0 else "S"
    se = SEASONS[hem]
    st.markdown(
        f'<div class="site-meta"><span class="chip"><b>Hemisferio</b>{se.label.split()[-1]}</span>'
        f'<span class="chip"><b>Temporada</b>{MONTHS_ES[se.winkler[0]-1]}–{MONTHS_ES[se.winkler[-1]-1]}</span>'
        f'<span class="chip"><b>Periodo</b>{years[0]}–{years[1]}</span></div>', unsafe_allow_html=True)
    run = st.button("Analizar finca", type="primary", width="stretch", icon=":material/query_stats:")
    st.caption("La primera consulta de un periodo largo puede tardar 10–30 s; después queda en caché 24 h.")

if run:
    end = date(years[1], 12, 31)
    end = min(end, last_available_day())
    start = date(years[0] - 1, 7, 1) if hem == "S" else date(years[0], 1, 1)
    start = max(start, date(FIRST_YEAR, 1, 1))
    try:
        with st.spinner("Consultando NASA POWER…"):
            raw, meta = cached_fetch(round(st.session_state.lat, 4), round(st.session_state.lon, 4), start, end)
        missing = [p for p in REQUIRED if p not in raw.columns]
        if missing:
            raise ValueError(f"faltan parámetros: {', '.join(missing)}")
        st.session_state.result = {
            "raw": raw, "meta": meta, "name": st.session_state.name.strip() or "Finca",
            "lat": st.session_state.lat, "lon": st.session_state.lon, "years": years,
        }
    except requests.RequestException as exc:
        st.error(f"No se pudo conectar con NASA POWER: {exc}")
    except ValueError as exc:
        st.error(f"No fue posible obtener los datos: {exc}")

res = st.session_state.result
if res is None:
    st.info("Sitúa la finca en el mapa (o introduce coordenadas) y pulsa **Analizar finca**.", icon=":material/info:")
    st.markdown(theme.footer_html(), unsafe_allow_html=True)
    st.stop()

# --------------------------------------------------------------- cálculos
lat, lon, meta = res["lat"], res["lon"], res["meta"]
hem = "N" if lat >= 0 else "S"
daily, annual, monthly, norms, trend, cum = compute(
    res["raw"], lat, meta["elevation"], base, frost, heat, cov, tuple(sorted(harvest)))
annual = annual[annual["Campaña"].between(*res["years"])].reset_index(drop=True)
valid = annual.dropna(subset=["GDD Winkler (°C·día)"])
if valid.empty:
    st.warning("No hay ninguna campaña con cobertura suficiente en el periodo elegido.")
    st.stop()


def mean_of(col):
    return annual[col].mean()


def badge_of(col, classes):
    return ix.classify(mean_of(col), classes)


st.divider()
step(2, f"Resultados · {html.escape(res['name'])}")
if (res["lat"], res["lon"]) != (st.session_state.lat, st.session_state.lon):
    st.caption("Las coordenadas del formulario han cambiado; pulsa **Analizar finca** para actualizar los resultados.")
st.markdown(
    f'<div class="site-meta"><span class="chip"><b>Coordenadas</b>{lat:.5f}, {lon:.5f}</span>'
    f'<span class="chip"><b>Altitud celda</b>{fmt(meta["elevation"], 0, "m")}</span>'
    f'<span class="chip"><b>Campañas válidas</b>{len(valid)} ({int(valid["Campaña"].min())}–{int(valid["Campaña"].max())})</span>'
    f'<span class="chip"><b>Umbrales</b>base {fmt(base, 1)} °C · helada ≤ {fmt(frost, 1)} °C · calor ≥ {fmt(heat, 1)} °C</span></div>',
    unsafe_allow_html=True)

gst_cls = badge_of("GST (°C)", GST_CLASSES)
n = len(valid)
cards = [
    kpi("GDD Winkler", fmt(mean_of("GDD Winkler (°C·día)"), 0, "<small>°C·día</small>"), badge_of("GDD Winkler (°C·día)", WINKLER_CLASSES),
        f"σ {fmt(annual['GDD Winkler (°C·día)'].std())} · {n} campañas"),
    kpi("Índice de Huglin", fmt(mean_of("Índice de Huglin")), badge_of("Índice de Huglin", HUGLIN_CLASSES),
        f"k = {ix.huglin_k(lat):.2f} por latitud"),
    kpi("Temperatura temporada (GST)", fmt(mean_of("GST (°C)"), 1, "<small>°C</small>"), gst_cls, "Jones (2006)"),
    kpi("Frescor nocturno", fmt(mean_of("Índice de frescor nocturno (°C)"), 1, "<small>°C</small>"),
        badge_of("Índice de frescor nocturno (°C)", COOL_NIGHT_CLASSES), f"Tmín media de {MONTHS_ES[SEASONS[hem].cool_night-1]}"),
    kpi("Índice de sequía", fmt(mean_of("Índice de sequía (mm)"), 0, "<small>mm</small>"),
        badge_of("Índice de sequía (mm)", DRYNESS_CLASSES), "Riou · W₀ = 200 mm"),
    kpi("Precipitación campaña", fmt(mean_of("Precipitación campaña (mm)"), 0, "<small>mm</small>"), None,
        f"en temporada {fmt(mean_of('Precipitación temporada (mm)'))} mm · ET0 {fmt(mean_of('ET0 temporada (mm)'))} mm"),
    kpi("Periodo libre de heladas", fmt(annual["Periodo libre de heladas (días)"].median(), 0, "<small>días</small>"), None,
        f"helada en brotación: {fmt(100 * (annual['Heladas en brotación (días)'] > 0).mean())} % de campañas"),
    kpi("Días de calor", fmt(mean_of("Días de calor en temporada"), 1, "<small>días/temporada</small>"), None,
        f"Tmáx ≥ {fmt(heat, 0)} °C · máx. absoluta {fmt(annual['Tmax absoluta campaña (°C)'].max(), 1)} °C"),
]
st.markdown(f'<div class="kpis">{"".join(cards)}</div>', unsafe_allow_html=True)

tabs = st.tabs(["Resumen", "Índices", "Campaña en curso", "Clima mensual", "Agua",
                "Riesgos", "Tendencias", "Comparar fincas", "Datos", "Metodología"])

# ------------------------------------------------------------------ resumen
with tabs[0]:
    tr = trend.set_index("Indicador") if not trend.empty else pd.DataFrame()
    trend_txt = ""
    if "GST (°C)" in tr.index:
        r = tr.loc["GST (°C)"]
        pv = r["p (Mann-Kendall)"]
        p_txt = "p < 0,001" if pv < 0.001 else f"p = {fmt(pv, 3)}"
        trend_txt = (f" La GST muestra una tendencia de <b>{fmt(r['Pendiente de Sen / década'], 2)} °C por década</b> "
                     f"({'significativa' if pv < 0.05 else 'no significativa'}, {p_txt}).")
    frost_s = ix.frost_doy_summary(annual)
    reading = (
        f"Con una temperatura media de temporada de <b>{fmt(mean_of('GST (°C)'), 1)} °C</b> el sitio se clasifica como "
        f"<b>{gst_cls.lower()}</b> según Jones; en Winkler corresponde a <b>{badge_of('GDD Winkler (°C·día)', WINKLER_CLASSES)}</b> "
        f"y en Huglin a <b>{badge_of('Índice de Huglin', HUGLIN_CLASSES)}</b>. "
        f"Las noches previas a vendimia son <b>{badge_of('Índice de frescor nocturno (°C)', COOL_NIGHT_CLASSES).split(' (')[0].lower()}</b> "
        f"y el balance de Riou indica un régimen <b>{badge_of('Índice de sequía (mm)', DRYNESS_CLASSES).split(' (')[0].lower()}</b>."
        f"{trend_txt} La última helada primaveral se produce de mediana el <b>{frost_s['Última helada primaveral (mediana)']}</b> "
        f"(más tardía: {frost_s['Última helada primaveral (más tardía)']})."
    )
    st.markdown(f'<div class="reading">{reading}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.5, 1], gap="large")
    with c1:
        st.plotly_chart(charts.climograph(norms), width="stretch")
    with c2:
        st.markdown("#### Orientación varietal (GST)")
        st.markdown(f"**{gst_cls}** · {VARIETY_GUIDE.get(gst_cls, '')}")
        st.caption("Agrupación amplia basada en Jones (2006). Orientativa: el clon, el portainjerto, el suelo, "
                   "la orientación y el objetivo enológico modifican la idoneidad.")
        st.markdown("#### Frecuencia de clases por campaña")
        parts = []
        for label, col, classes in [("Winkler", "Región Winkler", WINKLER_CLASSES), ("Huglin", "Clase Huglin", HUGLIN_CLASSES),
                                    ("GST", "Clase GST", GST_CLASSES)]:
            vc = annual.loc[annual[col] != "Sin datos", col].value_counts()
            order = [c for _, c in classes if c in vc.index]
            parts.append(pd.DataFrame({"Índice": label, "Clase": order, "Campañas": vc[order].to_numpy(),
                                       "%": 100 * vc[order].to_numpy() / vc.sum()}))
        st.dataframe(pd.concat(parts), width="stretch", hide_index=True, column_config={
            "Índice": st.column_config.TextColumn(width="small"),
            "Campañas": st.column_config.NumberColumn(width="small"),
            "%": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f %%", width="medium")})
        st.markdown("#### Fechas de helada")
        st.dataframe(pd.Series(frost_s, name="Fecha"), width="stretch")

# ------------------------------------------------------------------ índices
INDEX_META = {
    "GDD Winkler (°C·día)": (WINKLER_CLASSES, "°C·día"),
    "Índice de Huglin": (HUGLIN_CLASSES, ""),
    "GST (°C)": (GST_CLASSES, "°C"),
    "BEDD (°C·día)": (None, "°C·día"),
    "Índice de frescor nocturno (°C)": (COOL_NIGHT_CLASSES, "°C"),
    "Índice de sequía (mm)": (DRYNESS_CLASSES, "mm"),
}
with tabs[1]:
    sel = st.segmented_control("Índice", list(INDEX_META), default="GDD Winkler (°C·día)", key="idx_sel")
    sel = sel or "GDD Winkler (°C·día)"
    classes, unit = INDEX_META[sel]
    st.plotly_chart(charts.index_series(annual, sel, classes, unit, trend_row=True), width="stretch")
    cols = ["Campaña", "Cobertura temporada (%)", "GDD Winkler (°C·día)", "Región Winkler", "Índice de Huglin",
            "Clase Huglin", "GST (°C)", "Clase GST", "BEDD (°C·día)", "Índice de frescor nocturno (°C)",
            "Clase frescor nocturno", "Índice de sequía (mm)", "Clase sequía"]
    st.dataframe(annual[cols], width="stretch", hide_index=True, column_config={
        "Campaña": st.column_config.NumberColumn(format="%d"),
        "Cobertura temporada (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f %%"),
        **{c: st.column_config.NumberColumn(format="%.1f") for c in cols if annual[c].dtype.kind == "f" and c != "Cobertura temporada (%)"},
    })

# ---------------------------------------------------------- campaña en curso
with tabs[2]:
    if cum.empty:
        st.info("Sin datos de temporada.")
    else:
        avail = sorted(cum["Campaña"].unique(), reverse=True)
        hl = st.selectbox("Campaña a destacar", avail, index=0)
        st.plotly_chart(charts.cumulative_chart(cum, hl, base), width="stretch")
        h = cum[(cum["Campaña"] == hl)].dropna(subset=["GDD acumulado"])
        if not h.empty:
            last = h.iloc[-1]
            ref = cum[(cum["Día"] == last["Día"]) & cum["Completa"] & (cum["Campaña"] != hl)]["GDD acumulado"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(f"GDD acumulados a {last['Fecha'].strftime('%d/%m/%Y')}", fmt(last["GDD acumulado"]))
            if len(ref):
                diff = last["GDD acumulado"] - ref.median()
                m2.metric("Frente a la mediana", fmt(ref.median()), f"{diff:+,.0f} °C·día".replace(",", "."))
                m3.metric("Percentil de la campaña", f"P{int(round(100 * (ref < last['GDD acumulado']).mean()))}")
                yrs_ahead = int((ref < last["GDD acumulado"]).sum())
                m4.metric("Campañas más frías a esta fecha", f"{yrs_ahead} de {len(ref)}")
        st.caption("Las líneas grises son el resto de campañas; la banda dorada cubre del percentil 10 al 90 de las campañas completas. "
                   "Útil para anticipar el adelanto o retraso de la maduración respecto a lo habitual.")

# ----------------------------------------------------------- clima mensual
VAR_OPTS = {
    "T media (°C)": ("°C", charts.TEMP_SCALE, False), "T máx media (°C)": ("°C", charts.TEMP_SCALE, False),
    "T mín media (°C)": ("°C", charts.TEMP_SCALE, False), "Precipitación (mm)": ("%", charts.WET_SCALE, True),
    "ET0 (mm)": ("%", charts.TEMP_SCALE, True), "GDD (°C·día)": ("°C·día", charts.TEMP_SCALE, False),
    "Radiación media (MJ/m²/día)": ("MJ/m²", charts.TEMP_SCALE, False), "HR media (%)": ("pp", charts.WET_SCALE, False),
}
with tabs[3]:
    var = st.selectbox("Variable", list(VAR_OPTS))
    u, scale, rel = VAR_OPTS[var]
    mat = ix.anomaly_matrix(monthly, var, relative=rel).loc[res["years"][0]:res["years"][1]]
    c1, c2 = st.columns([1.3, 1], gap="large")
    with c1:
        st.plotly_chart(charts.anomaly_heatmap(mat, f"Anomalías mensuales · {var}", u, scale), width="stretch")
    with c2:
        color = BRAND["s1_light"] if "Precip" in var else BRAND["s1"]
        st.plotly_chart(charts.monthly_box(monthly.loc[str(res["years"][0]):str(res["years"][1])], var, color),
                        width="stretch")
        st.markdown("#### Normales mensuales")
        nn = norms.copy()
        nn.index = [MONTHS_ES[m - 1] for m in nn.index]
        st.dataframe(nn.round(1), width="stretch")
    st.caption("Anomalía = valor del mes − media del mismo mes en el periodo (en % para precipitación y ET0).")

# -------------------------------------------------------------------- agua
with tabs[4]:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(charts.water_bars(annual), width="stretch")
    with c2:
        st.plotly_chart(charts.index_series(annual, "Índice de sequía (mm)", DRYNESS_CLASSES, "mm"), width="stretch")
    wb = norms[["Precipitación (mm)", "ET0 (mm)"]].copy()
    wb["P − ET0 (mm)"] = wb["Precipitación (mm)"] - wb["ET0 (mm)"]
    wb["P / ET0"] = wb["Precipitación (mm)"] / wb["ET0 (mm)"]
    wb.index = [MONTHS_ES[m - 1] for m in wb.index]
    st.markdown("#### Balance hídrico climático mensual (normales)")
    st.dataframe(wb.round(2).T, width="stretch")
    st.caption("ET0 FAO-56 Penman-Monteith de referencia (hierba). La demanda real del viñedo es ET0 × Kc (≈0,3–0,7 según "
               "cobertura y fase). El índice de sequía de Riou estima la reserva hídrica del suelo al final de la maduración.")

# ------------------------------------------------------------------ riesgos
with tabs[5]:
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.plotly_chart(charts.frost_dots(annual), width="stretch")
    with c2:
        for col, unit in [("Heladas en brotación (días)", "días"), ("Días de calor en temporada", "días"),
                          ("Lluvia en vendimia (mm)", "mm"), ("Días favorables a mildiu (proxy)", "días")]:
            st.plotly_chart(charts.small_bars(annual, col, unit), width="stretch")
    risk = pd.DataFrame({
        "Indicador": ["Campañas con helada en brotación", "Campañas con ≥ 5 días de calor",
                      "Lluvia media en vendimia", "Amplitud térmica media en vendimia", "Tmín absoluta del periodo"],
        "Valor": [f"{fmt(100 * (annual['Heladas en brotación (días)'] > 0).mean())} %",
                  f"{fmt(100 * (annual['Días de calor en temporada'] >= 5).mean())} %",
                  fmt(mean_of("Lluvia en vendimia (mm)"), 0, "mm"),
                  fmt(mean_of("Amplitud térmica en vendimia (°C)"), 1, "°C"),
                  fmt(annual["Tmin absoluta campaña (°C)"].min(), 1, "°C")],
    })
    st.dataframe(risk, width="stretch", hide_index=True)
    st.caption(f"Brotación: {', '.join(MONTHS_ES[m-1] for m in SEASONS[hem].budbreak)}. Vendimia: "
               f"{', '.join(MONTHS_ES[m-1] for m in sorted(harvest)) or '—'}. El proxy de mildiu cuenta días con Tmín ≥ 10 °C y lluvia ≥ 10 mm; "
               "no sustituye a un modelo epidemiológico.")

# --------------------------------------------------------------- tendencias
with tabs[6]:
    if trend.empty:
        st.info("Se necesitan al menos 8 campañas válidas para estimar tendencias.")
    else:
        st.dataframe(trend, width="stretch", hide_index=True, column_config={
            "Media": st.column_config.NumberColumn(format="%.1f"),
            "Desv. típica": st.column_config.NumberColumn(format="%.1f"),
            "CV (%)": st.column_config.NumberColumn(format="%.1f"),
            "Pendiente MCO / década": st.column_config.NumberColumn(format="%+.2f"),
            "Pendiente de Sen / década": st.column_config.NumberColumn(format="%+.2f"),
            "R²": st.column_config.NumberColumn(format="%.2f"),
            "τ de Kendall": st.column_config.NumberColumn(format="%+.2f"),
            "p (Mann-Kendall)": st.column_config.NumberColumn(format="%.3f"),
        })
        tsel = st.selectbox("Ver serie", trend["Indicador"].tolist())
        st.plotly_chart(charts.index_series(annual, tsel, INDEX_META.get(tsel, (None, ""))[0], trend_row=True),
                        width="stretch")
        st.caption("Pendiente de Sen y test de Mann-Kendall: robustos a valores extremos. Con series cortas (< 20 años) "
                   "las tendencias deben interpretarse con cautela.")

# ---------------------------------------------------------------- comparar
with tabs[7]:
    if st.button(f"Guardar «{res['name']}» para comparar", type="primary", icon=":material/add:"):
        st.session_state.sites[res["name"]] = {"lat": lat, "lon": lon, "elevation": meta["elevation"],
                                               "annual": annual.copy(), "years": res["years"]}
        st.rerun()
    sites = st.session_state.sites
    if len(sites) < 2:
        st.info("Guarda al menos dos fincas (analiza una, guárdala, cambia la ubicación y repite) para compararlas.")
    if sites:
        cmp_cols = ["GDD Winkler (°C·día)", "Índice de Huglin", "GST (°C)", "Índice de frescor nocturno (°C)",
                    "Índice de sequía (mm)", "Precipitación campaña (mm)", "Periodo libre de heladas (días)",
                    "Días de calor en temporada", "Lluvia en vendimia (mm)"]
        rows = []
        for nm, s in sites.items():
            a = s["annual"]
            r = {"Finca": nm, "Lat": s["lat"], "Lon": s["lon"], "Altitud (m)": s["elevation"],
                 "Periodo": f"{s['years'][0]}–{s['years'][1]}"}
            r.update({c: a[c].mean() for c in cmp_cols})
            r["Región Winkler"] = ix.classify(r["GDD Winkler (°C·día)"], WINKLER_CLASSES)
            r["Clase GST"] = ix.classify(r["GST (°C)"], GST_CLASSES)
            rows.append(r)
        table = pd.DataFrame(rows)
        st.dataframe(table.round(2), width="stretch", hide_index=True)
        if len(sites) >= 2:
            csel = st.segmented_control("Indicador", cmp_cols, default="GDD Winkler (°C·día)", key="cmp_sel") or cmp_cols[0]
            st.plotly_chart(charts.compare_sites(table, csel), width="stretch")
            periods = {s["years"] for s in sites.values()}
            if len(periods) > 1:
                st.warning("Las fincas se analizaron con periodos distintos; para comparar, usa el mismo periodo.")

# -------------------------------------------------------------------- datos
with tabs[8]:
    site = {"name": res["name"], "lat": lat, "lon": lon, "elevation": meta["elevation"],
            "period": f"{res['years'][0]}–{res['years'][1]}", "sources": meta["sources"], "api_version": meta["api_version"]}
    settings_rows = [("Temperatura base GDD (°C)", base), ("Umbral helada (°C)", frost), ("Umbral calor (°C)", heat),
                     ("Meses de vendimia", ", ".join(MONTHS_ES[m - 1] for m in sorted(harvest))),
                     ("Cobertura mínima", cov), ("Hemisferio", SEASONS[hem].label)]
    slug = re.sub(r"[^a-z0-9]+", "_", res["name"].lower()).strip("_") or "finca"
    c1, c2, c3 = st.columns(3)
    c1.download_button("Excel completo", icon=":material/table_view:", data=excel_report(site, settings_rows, annual, trend, monthly, norms, daily),
                       file_name=f"agroclima_{slug}_{res['years'][0]}_{res['years'][1]}.xlsx", type="primary",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    c2.download_button("Índices por campaña (CSV)", icon=":material/download:", data=annual.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"indices_{slug}.csv", mime="text/csv", width="stretch")
    c3.download_button("Datos diarios (CSV)", icon=":material/download:", data=daily.to_csv().encode("utf-8-sig"),
                       file_name=f"diario_{slug}.csv", mime="text/csv", width="stretch")
    view = st.radio("Tabla", ["Índices por campaña", "Serie mensual", "Datos diarios"], horizontal=True)
    if view == "Índices por campaña":
        st.dataframe(annual, width="stretch", hide_index=True)
    elif view == "Serie mensual":
        st.dataframe(monthly.round(2), width="stretch")
    else:
        st.dataframe(daily.drop(columns=["Mes"]).round(2), width="stretch")
    cov_m = monthly["Cobertura (%)"]
    st.caption(f"Calidad: {fmt(100 * (cov_m >= 100 * cov).mean(), 1)} % de los meses superan la cobertura mínima. "
               f"Último dato disponible: {daily.dropna(subset=['T2M']).index.max():%d/%m/%Y}. Fuentes: {meta['sources']}.")

# -------------------------------------------------------------- metodología
with tabs[9]:
    st.markdown(f"""
#### Datos
- **NASA POWER Daily API** (comunidad AG), resolución nativa: meteorología **MERRA-2** (~0,5° × 0,625°, ≈ 50 km) y radiación **CERES SYN1deg** (~1°).
  Los valores representan la media de la celda, no el microclima de la parcela: en relieve complejo conviene corregir la temperatura por altitud
  (≈ −0,65 °C cada 100 m respecto a la altitud de la celda, {fmt(meta['elevation'], 0, 'm')}).
- **Campaña** = año de vendimia. Hemisferio sur: de julio del año anterior a junio. Se exige una cobertura mínima de días válidos ({fmt(cov*100)} %) en cada ventana.

#### Índices
| Índice | Definición | Periodo ({SEASONS[hem].label.lower()}) |
|---|---|---|
| GDD Winkler | Σ max(Tmed − {fmt(base,1)}, 0) | {MONTHS_ES[SEASONS[hem].winkler[0]-1]}–{MONTHS_ES[SEASONS[hem].winkler[-1]-1]} |
| Huglin (HI) | Σ [(Tmed − 10) + (Tmáx − 10)]/2 · k, k = {ix.huglin_k(lat):.2f} | {MONTHS_ES[SEASONS[hem].huglin[0]-1]}–{MONTHS_ES[SEASONS[hem].huglin[-1]-1]} |
| GST | Temperatura media de la temporada | {MONTHS_ES[SEASONS[hem].winkler[0]-1]}–{MONTHS_ES[SEASONS[hem].winkler[-1]-1]} |
| BEDD (simplificado) | Σ min(max(Tmed − 10, 0), 9) | temporada |
| Frescor nocturno (CI) | Tmín media del mes previo a vendimia | {MONTHS_ES[SEASONS[hem].cool_night-1]} |
| Sequía (DI, Riou) | W = W₀ + P − Tv − Es, W₀ = 200 mm | {MONTHS_ES[SEASONS[hem].huglin[0]-1]}–{MONTHS_ES[SEASONS[hem].huglin[-1]-1]} |
| ET0 | FAO-56 Penman-Monteith (respaldo Hargreaves-Samani) | diario |

#### Clases
- **Winkler** (Jones et al., 2010): < 850 demasiado fría · Ia 850–1111 · Ib 1111–1389 · II 1389–1667 · III 1667–1944 · IV 1944–2222 · V 2222–2700 · > 2700 demasiado cálida.
- **Huglin** (Tonietto y Carbonneau, 2004): ≤ 1500 muy fresco · 1500–1800 fresco · 1800–2100 templado · 2100–2400 templado cálido · 2400–3000 cálido · > 3000 muy cálido.
- **GST** (Jones, 2006): 13–15 fresco · 15–17 intermedio · 17–19 cálido · 19–21 caluroso · 21–24 muy caluroso.
- **Frescor nocturno**: ≤ 12 muy frescas · 12–14 frescas · 14–18 templadas · > 18 cálidas.
- **Sequía**: ≤ −100 muy seco · −100–50 moderadamente seco · 50–150 subhúmedo · > 150 húmedo.

#### Tendencias
Pendiente MCO y estimador de Theil-Sen expresados por década; significación mediante Mann-Kendall (τ de Kendall), sin corrección por autocorrelación.

#### Referencias
- Winkler, A.J. et al. (1974). *General Viticulture*. University of California Press.
- Huglin, P. (1978). Nouveau mode d'évaluation des possibilités héliothermiques d'un milieu viticole. *C. R. Acad. Agric. France*.
- Tonietto, J. y Carbonneau, A. (2004). A multicriteria climatic classification system for grape-growing regions worldwide. *Agric. For. Meteorol.* 124.
- Jones, G.V. (2006). Climate and terroir: impacts of climate variability and change on wine. *Geoscience Canada*.
- Jones, G.V. et al. (2010). Spatial analysis of climate in winegrape growing regions in the western United States. *Am. J. Enol. Vitic.* 61.
- Allen, R.G. et al. (1998). *Crop evapotranspiration*. FAO Irrigation and Drainage Paper 56.
- Riou, C. et al. (1994). *Le déterminisme climatique de la maturation du raisin*. Comisión Europea.

> Los datos de reanálisis no sustituyen a una estación meteorológica local. Antes de decisiones de inversión, contrastar con registros in situ.
""")

st.markdown(theme.footer_html(), unsafe_allow_html=True)
