import io
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"]
COLUMNS = {
    "T2M": "Temperatura media (°C)",
    "T2M_MAX": "Temperatura máxima (°C)",
    "T2M_MIN": "Temperatura mínima (°C)",
    "PRECTOTCORR": "Precipitación (mm)",
    "RH2M": "Humedad relativa (%)",
    "WS2M": "Viento 2 m (m/s)",
    "ALLSKY_SFC_SW_DWN": "Radiación solar (kWh/m²/día)",
}

st.set_page_config(page_title="Agroclima | Viticultura del Norte", page_icon="🍇", layout="wide")

# Paleta PROVISIONAL: sustituir por los colores oficiales una vez disponible el logotipo.
BRAND = {
    "wine": "#682F42",
    "wine_dark": "#432331",
    "olive": "#66764D",
    "cream": "#F7F4EC",
    "gold": "#C9A568",
    "ink": "#27322B",
}

st.markdown("""
<style>
    .stApp { background: #F7F4EC; color: #27322B; }
    .block-container { max-width: 1200px; padding-top: 2rem; }
    h1, h2, h3 { color: #432331 !important; letter-spacing: -.025em; }
    [data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E8E0D6;
        border-radius: 15px; padding: 18px 20px;
        box-shadow: 0 2px 12px rgba(67,35,49,.045);
    }
    [data-testid="stMetricLabel"] { color: #66764D; }
    [data-testid="stForm"] {
        background: #FFFFFF; border: 1px solid #E8E0D6;
        border-radius: 18px; padding: 22px;
    }
    div.stButton > button[kind="primary"],
    div.stFormSubmitButton > button[kind="primary"] {
        background-color: #682F42; border-color: #682F42;
        color: #FFFFFF; border-radius: 10px; font-weight: 650;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stFormSubmitButton > button[kind="primary"]:hover {
        background-color: #432331; border-color: #432331;
    }
    [data-testid="stDownloadButton"] button {
        border: 1px solid #66764D; color: #432331;
        background-color: #FFFFFF; border-radius: 10px;
    }
    [data-testid="stDownloadButton"] button:hover {
        border-color: #682F42; color: #682F42;
    }
    .brand-hero {
        background: linear-gradient(115deg, #432331 0%, #682F42 73%, #765444 100%);
        border-radius: 18px; padding: 30px 34px; margin-bottom: 20px;
        color: #fff;
    }
    .brand-hero .eyebrow { color: #E8D2AE; text-transform: uppercase;
        letter-spacing: .15em; font-size: .75rem; font-weight: 700; }
    .brand-hero h1 { color: #FFF !important; font-size: 2.2rem;
        margin: .25rem 0 .5rem; }
    .brand-hero p { color: #F1E7E0; margin-bottom: 0; }
    .brand-rule { width: 58px; height: 4px; background: #C9A568;
        border-radius: 8px; margin: 14px 0; }
    @media (max-width: 650px) {
        .brand-hero { padding: 22px; }
        .brand-hero h1 { font-size: 1.65rem; }
    }
</style>
""", unsafe_allow_html=True)


def brand_chart(fig):
    """Colores y tipografía consistentes en todas las gráficas Plotly."""
    fig.update_layout(
        template="plotly_white", paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(color=BRAND["ink"]), title_font=dict(color=BRAND["wine_dark"]),
        colorway=[BRAND["wine"], BRAND["olive"], BRAND["gold"]],
        margin=dict(l=20, r=20, t=65, b=30),
        legend=dict(title_text=""),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E8E0D6")
    fig.update_yaxes(gridcolor="#EEE9E1", zerolinecolor="#E8E0D6")
    return fig

@st.cache_data(ttl=24 * 3600, show_spinner=False)
def fetch_power(lat, lon, start_year, end_year):
    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": f"{start_year}0101",
        "end": f"{end_year}1231",
        "format": "JSON",
    }
    response = requests.get(API_URL, params=params, timeout=180)
    response.raise_for_status()
    payload = response.json()
    series = payload.get("properties", {}).get("parameter", {})
    if not series:
        raise ValueError("NASA POWER no devolvió datos para esta consulta.")
    df = pd.DataFrame(series)
    df.index = pd.to_datetime(df.index, format="%Y%m%d", errors="coerce")
    df = df.loc[df.index.notna()].sort_index()
    df.index.name = "Fecha"
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.replace([-999, -999.0, -99, -99.0], np.nan)
    # Some POWER responses provide a custom fill value in the header.
    fill = payload.get("header", {}).get("fill_value")
    if fill is not None:
        try:
            df = df.replace(float(fill), np.nan)
        except (TypeError, ValueError):
            pass
    return df


def winkler_region(gdd):
    if pd.isna(gdd):
        return "Sin datos suficientes"
    if gdd < 1390:
        return "Región I"
    if gdd < 1670:
        return "Región II"
    if gdd < 1940:
        return "Región III"
    if gdd < 2220:
        return "Región IV"
    return "Región V"


def calculate(df):
    df = df.copy()
    df["Año"] = df.index.year
    df["Mes"] = df.index.month
    df["GDD diario (°C·día)"] = (df["T2M"] - 10).clip(lower=0)
    # Winkler growing season in the Northern Hemisphere, April 1–October 31.
    df["Temporada Winkler"] = df["Mes"].between(4, 10)
    df["GDD Winkler diario"] = df["GDD diario (°C·día)"].where(df["Temporada Winkler"])

    years = []
    for year, part in df.groupby("Año"):
        season = part.loc[part["Temporada Winkler"]]
        days_expected = len(pd.date_range(f"{year}-04-01", f"{year}-10-31"))
        valid = int(season["GDD Winkler diario"].notna().sum())
        completeness = valid / days_expected if days_expected else 0
        # Do not publish a misleading full-season GDD for incomplete years.
        gdd = float(season["GDD Winkler diario"].sum()) if completeness >= 0.95 else np.nan
        precip_valid = int(part["PRECTOTCORR"].notna().sum())
        days_year = 366 if pd.Timestamp(year, 12, 31).is_leap_year else 365
        precip = float(part["PRECTOTCORR"].sum()) if precip_valid / days_year >= 0.95 else np.nan
        years.append({
            "Año": int(year),
            "GDD Winkler (°C·día)": gdd,
            "Región Winkler": winkler_region(gdd),
            "Cobertura temporada (%)": round(completeness * 100, 1),
            "Precipitación anual (mm)": precip,
            "Cobertura precipitación (%)": round(100 * precip_valid / days_year, 1),
            "Temperatura media anual (°C)": part["T2M"].mean(),
            "Temperatura máxima registrada (°C)": part["T2M_MAX"].max(),
            "Temperatura mínima registrada (°C)": part["T2M_MIN"].min(),
            "Días con Tmin ≤ 0 °C": int((part["T2M_MIN"] <= 0).sum()),
            "Días con Tmax ≥ 35 °C": int((part["T2M_MAX"] >= 35).sum()),
        })

    annual = pd.DataFrame(years)
    monthly = df.resample("MS").agg({
        "T2M": "mean",
        "T2M_MAX": "mean",
        "T2M_MIN": "mean",
        "PRECTOTCORR": lambda s: s.sum(min_count=1),
        "GDD diario (°C·día)": lambda s: s.sum(min_count=1),
    })
    monthly.index.name = "Mes"
    return df, annual, monthly


def excel_bytes(daily, annual, monthly, rancho, lat, lon):
    output = io.BytesIO()
    metadata = pd.DataFrame({
        "Campo": ["Rancho", "Latitud", "Longitud", "Fuente", "Temporada Winkler", "Umbral GDD", "Cobertura mínima"],
        "Valor": [rancho, lat, lon, "NASA POWER, community AG", "1 abril–31 octubre (hemisferio norte)", "10 °C", "95% de días válidos"],
    })
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        metadata.to_excel(writer, sheet_name="Información", index=False)
        annual.to_excel(writer, sheet_name="Resumen anual", index=False)
        monthly.reset_index().to_excel(writer, sheet_name="Resumen mensual", index=False)
        daily.rename(columns=COLUMNS).reset_index().to_excel(writer, sheet_name="Datos diarios", index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for cells in sheet.columns:
                letter = cells[0].column_letter
                width = min(max(max(len(str(c.value or "")) for c in cells[:250]) + 2, 14), 38)
                sheet.column_dimensions[letter].width = width
    return output.getvalue()


st.markdown("""
<div class="brand-hero">
  <div class="eyebrow">Viticultura del Norte · Inteligencia agroclimática</div>
  <div class="brand-rule"></div>
  <h1>Analizador agroclimático</h1>
  <p>Datos meteorológicos y evaluación térmica para una mejor planificación vitícola.</p>
</div>
""", unsafe_allow_html=True)
st.write("Introduce las coordenadas del predio y el periodo de estudio. Analizaremos los datos diarios de NASA POWER de forma automática.")

with st.form("formulario"):
    name = st.text_input("Nombre del rancho", value="Finca Aurora")
    a, b = st.columns(2)
    lat = a.number_input("Latitud (decimal)", min_value=-90.0, max_value=90.0, value=28.440148, format="%.6f")
    lon = b.number_input("Longitud (decimal)", min_value=-180.0, max_value=180.0, value=-106.185296, format="%.6f")
    c, d = st.columns(2)
    first = c.number_input("Año inicial", min_value=1981, max_value=date.today().year - 1, value=1991, step=1)
    last = d.number_input("Año final", min_value=1981, max_value=date.today().year - 1, value=min(2025, date.today().year - 1), step=1)
    submitted = st.form_submit_button("Analizar rancho", type="primary", use_container_width=True)

if submitted:
    if first > last:
        st.error("El año inicial debe ser anterior o igual al año final.")
        st.stop()
    if lat < 0:
        st.error("Esta versión calcula Winkler solo para el hemisferio norte.")
        st.stop()
    try:
        with st.spinner("Consultando NASA POWER y calculando indicadores…"):
            raw = fetch_power(lat, lon, int(first), int(last))
            missing = [p for p in ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"] if p not in raw.columns]
            if missing:
                raise ValueError(f"Faltan parámetros en la respuesta: {', '.join(missing)}")
            daily, annual, monthly = calculate(raw)
    except requests.RequestException as exc:
        st.error(f"No se pudo consultar NASA POWER: {exc}")
        st.stop()
    except (ValueError, KeyError) as exc:
        st.error(f"No fue posible analizar los datos: {exc}")
        st.stop()

    st.subheader(f"Resultados · {name}")
    usable = annual.dropna(subset=["GDD Winkler (°C·día)"])
    avg_gdd = usable["GDD Winkler (°C·día)"].mean() if not usable.empty else np.nan
    avg_precip = annual["Precipitación anual (mm)"].mean()
    m1, m2, m3 = st.columns(3)
    m1.metric("GDD Winkler promedio", f"{avg_gdd:,.0f} °C·día" if pd.notna(avg_gdd) else "Sin datos")
    m2.metric("Región Winkler orientativa", winkler_region(avg_gdd))
    m3.metric("Precipitación anual media", f"{avg_precip:,.0f} mm" if pd.notna(avg_precip) else "Sin datos")

    st.info("Winkler: suma de max(T media diaria − 10 °C, 0) entre el 1 de abril y el 31 de octubre. Años con cobertura inferior al 95% se excluyen del promedio de GDD. La región se asigna al GDD promedio de los años válidos.")
    st.plotly_chart(brand_chart(px.line(annual, x="Año", y="GDD Winkler (°C·día)", markers=True, title="GDD Winkler por año", color_discrete_sequence=[BRAND["wine"]])), use_container_width=True)
    st.plotly_chart(brand_chart(px.bar(annual, x="Año", y="Precipitación anual (mm)", title="Precipitación anual", color_discrete_sequence=[BRAND["olive"]])), use_container_width=True)
    st.plotly_chart(brand_chart(px.line(monthly.reset_index(), x="Mes", y=["T2M", "T2M_MAX", "T2M_MIN"], labels={"value": "Temperatura (°C)", "variable": "Serie"}, title="Evolución mensual de temperaturas")), use_container_width=True)

    st.subheader("Resumen anual")
    st.dataframe(annual.round(2), use_container_width=True, hide_index=True)
    st.subheader("Datos mensuales")
    st.dataframe(monthly.round(2), use_container_width=True)
    st.download_button(
        "📥 Descargar Excel completo",
        data=excel_bytes(daily, annual, monthly, name, lat, lon),
        file_name=f"agroclima_{''.join(c if c.isalnum() else '_' for c in name.lower())}_{first}_{last}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.caption("Los días con mínima ≤ 0 °C son un indicador térmico, no una predicción de heladas en el viñedo. NASA POWER utiliza datos de cuadrícula; no sustituye una estación meteorológica local.")
