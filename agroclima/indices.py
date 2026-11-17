"""Cálculo de índices bioclimáticos vitícolas a partir de datos diarios de NASA POWER.

Todas las agregaciones por campaña exigen una cobertura mínima de días válidos
dentro de la ventana correspondiente; si no se alcanza, el valor queda en NaN.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .config import (
    COOL_NIGHT_CLASSES, DRYNESS_CLASSES, GST_CLASSES, HUGLIN_CLASSES, SEASONS,
    WINKLER_CLASSES, Seasons,
)


@dataclass
class Settings:
    base_temp: float = 10.0
    frost_temp: float = 0.0
    heat_temp: float = 35.0
    min_coverage: float = 0.95
    harvest_months: tuple = field(default_factory=tuple)  # vacío → por defecto del hemisferio


# ---------------------------------------------------------------- utilidades
def classify(value, classes) -> str:
    if value is None or pd.isna(value):
        return "Sin datos"
    for upper, label in classes:
        if upper is None or value < upper:
            return label
    return classes[-1][1]


def season_year(index: pd.DatetimeIndex, hemisphere: str) -> np.ndarray:
    """Campaña = año de vendimia. Hemisferio sur: julio–junio se asigna al año siguiente."""
    years = index.year.to_numpy()
    if hemisphere == "S":
        years = years + (index.month.to_numpy() >= 7)
    return years


def window_dates(year: int, months, hemisphere: str) -> pd.DatetimeIndex:
    """Fechas esperadas de una ventana (meses) para una campaña."""
    parts = []
    for m in months:
        cal_year = year - 1 if (hemisphere == "S" and m >= 7) else year
        start = pd.Timestamp(cal_year, m, 1)
        parts.append(pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="D"))
    return parts[0].append(parts[1:]).sort_values() if parts else pd.DatetimeIndex([])


def huglin_k(lat: float) -> float:
    """Coeficiente de longitud del día de Huglin (Tonietto y Carbonneau, 2004)."""
    a = abs(lat)
    if a <= 40:
        return 1.00
    if a <= 42:
        return 1.02
    if a <= 44:
        return 1.03
    if a <= 46:
        return 1.04
    if a <= 48:
        return 1.05
    return 1.06


# ------------------------------------------------------------ ET0 FAO-56
def extraterrestrial_radiation(index: pd.DatetimeIndex, lat: float) -> np.ndarray:
    j = index.day_of_year.to_numpy()
    phi = np.radians(lat)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    dec = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))
    return 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))


def et0_fao56(df: pd.DataFrame, lat: float, elevation: float) -> pd.Series:
    """ET0 Penman-Monteith FAO-56 diaria (mm). Hargreaves-Samani como respaldo."""
    z = 0.0 if pd.isna(elevation) else float(elevation)
    t, tx, tn = df["T2M"], df["T2M_MAX"], df["T2M_MIN"]
    ra = pd.Series(extraterrestrial_radiation(df.index, lat), index=df.index)

    def sat(temp):
        return 0.6108 * np.exp(17.27 * temp / (temp + 237.3))

    pressure = 101.3 * ((293 - 0.0065 * z) / 293) ** 5.26
    gamma = 0.000665 * pressure
    es = (sat(tx) + sat(tn)) / 2
    if "T2MDEW" in df:
        ea = sat(df["T2MDEW"])
    else:
        ea = pd.Series(np.nan, index=df.index)
    if "RH2M" in df:
        ea = ea.fillna(df["RH2M"] / 100 * es)
    delta = 4098 * sat(t) / (t + 237.3) ** 2

    rs = df.get("ALLSKY_SFC_SW_DWN", pd.Series(np.nan, index=df.index))
    u2 = df.get("WS2M", pd.Series(np.nan, index=df.index))
    rso = (0.75 + 2e-5 * z) * ra
    ratio = (rs / rso).clip(0.25, 1.0)
    rnl = 4.903e-9 * ((tx + 273.16) ** 4 + (tn + 273.16) ** 4) / 2 * (0.34 - 0.14 * np.sqrt(ea.clip(lower=0))) * (1.35 * ratio - 0.35)
    rn = 0.77 * rs - rnl
    pm = (0.408 * delta * rn + gamma * 900 / (t + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))
    hs = 0.0023 * 0.408 * ra * (t + 17.8) * np.sqrt((tx - tn).clip(lower=0))
    return pm.fillna(hs).clip(lower=0)


# --------------------------------------------------------------- diario
def enrich_daily(raw: pd.DataFrame, lat: float, elevation: float, s: Settings) -> pd.DataFrame:
    hemisphere = "N" if lat >= 0 else "S"
    df = raw.copy()
    df = df.asfreq("D")
    df["ET0"] = et0_fao56(df, lat, elevation)
    df["GDD"] = (df["T2M"] - s.base_temp).clip(lower=0)
    df["Campaña"] = season_year(df.index, hemisphere)
    df["Mes"] = df.index.month
    return df


# -------------------------------------------------------------- campaña
def _cov(part: pd.Series, expected: int) -> float:
    return part.notna().sum() / expected if expected else 0.0


def _riou(df_w: pd.DataFrame, months, year, hemisphere, min_cov) -> float:
    """Índice de sequía (Riou; Tonietto y Carbonneau, 2004), reserva inicial 200 mm."""
    w = 200.0
    for i, m in enumerate(months):
        cal_year = year - 1 if (hemisphere == "S" and m >= 7) else year
        sel = df_w[(df_w.index.month == m) & (df_w.index.year == cal_year)]
        n = pd.Timestamp(cal_year, m, 1).days_in_month
        if _cov(sel["PRECTOTCORR"], n) < min_cov or _cov(sel["ET0"], n) < min_cov:
            return np.nan
        p, etp = sel["PRECTOTCORR"].sum(), sel["ET0"].sum()
        k = 0.1 if i == 0 else 0.3 if i == 1 else 0.5
        tv = etp * k
        jpm = min(p / 5, n)
        es = etp / n * (1 - k) * jpm
        w = min(w + p - tv - es, 200.0)
    return w


def _doy_label(doy: float) -> str:
    if pd.isna(doy):
        return "—"
    d = pd.Timestamp(2001, 1, 1) + pd.Timedelta(days=int(round(doy)) - 1)
    from .config import MONTHS_ES
    return f"{d.day} {MONTHS_ES[d.month - 1]}"


def campaign_indices(daily: pd.DataFrame, lat: float, s: Settings) -> pd.DataFrame:
    hemisphere = "N" if lat >= 0 else "S"
    se: Seasons = SEASONS[hemisphere]
    harvest = tuple(s.harvest_months) or se.harvest
    k = huglin_k(lat)
    rows = []
    for year, part in daily.groupby("Campaña"):
        def win(months):
            dates = window_dates(year, months, hemisphere)
            return part.reindex(dates), len(dates)

        g, n_g = win(se.winkler)
        h, n_h = win(se.huglin)
        cn, n_cn = win((se.cool_night,))
        bb, n_bb = win(se.budbreak)
        hv, n_hv = win(harvest)
        full_dates = window_dates(year, (7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6), hemisphere) if hemisphere == "S" \
            else pd.date_range(f"{year}-01-01", f"{year}-12-31")
        full = part.reindex(full_dates)

        cov_g = _cov(g["T2M"], n_g)
        ok_g = cov_g >= s.min_coverage
        ok_h = _cov(h["T2M_MAX"], n_h) >= s.min_coverage and _cov(h["T2M"], n_h) >= s.min_coverage
        ok_cn = _cov(cn["T2M_MIN"], n_cn) >= s.min_coverage
        ok_bb = _cov(bb["T2M_MIN"], n_bb) >= s.min_coverage
        ok_hv = _cov(hv["PRECTOTCORR"], n_hv) >= s.min_coverage
        ok_pg = _cov(g["PRECTOTCORR"], n_g) >= s.min_coverage
        ok_full_p = _cov(full["PRECTOTCORR"], len(full)) >= s.min_coverage
        ok_full_t = _cov(full["T2M_MIN"], len(full)) >= s.min_coverage

        gdd = g["GDD"].sum() if ok_g else np.nan
        hi = (((h["T2M"] - 10).clip(lower=0) + (h["T2M_MAX"] - 10).clip(lower=0)) / 2).sum() * k if ok_h else np.nan
        gst = g["T2M"].mean() if ok_g else np.nan
        bedd = (g["T2M"] - 10).clip(lower=0, upper=9).sum() if ok_g else np.nan
        ci = cn["T2M_MIN"].mean() if ok_cn else np.nan
        di = _riou(h, se.huglin, year, hemisphere, s.min_coverage) if ok_h else np.nan
        p_g = g["PRECTOTCORR"].sum() if ok_pg else np.nan
        et0_g = g["ET0"].sum() if ok_g and _cov(g["ET0"], n_g) >= s.min_coverage else np.nan

        # Heladas: última primaveral y primera otoñal (por fecha real).
        frost = full["T2M_MIN"] <= s.frost_temp
        spring_dates = full.index[frost & full.index.month.isin(se.spring)]
        autumn_dates = full.index[frost & full.index.month.isin(se.autumn)]
        last_spring = spring_dates.max() if ok_full_t and len(spring_dates) else pd.NaT
        first_autumn = autumn_dates.min() if ok_full_t and len(autumn_dates) else pd.NaT
        if ok_full_t:
            start = last_spring if pd.notna(last_spring) else full.index[full.index.month.isin(se.spring)].min() - pd.Timedelta(days=1)
            end = first_autumn if pd.notna(first_autumn) else full.index[full.index.month.isin(se.autumn)].max() + pd.Timedelta(days=1)
            frost_free = (end - start).days - 1
        else:
            frost_free = np.nan

        rows.append({
            "Campaña": int(year),
            "Cobertura temporada (%)": round(100 * cov_g, 1),
            "GDD Winkler (°C·día)": gdd,
            "Región Winkler": classify(gdd, WINKLER_CLASSES),
            "Índice de Huglin": hi,
            "Clase Huglin": classify(hi, HUGLIN_CLASSES),
            "GST (°C)": gst,
            "Clase GST": classify(gst, GST_CLASSES),
            "BEDD (°C·día)": bedd,
            "Índice de frescor nocturno (°C)": ci,
            "Clase frescor nocturno": classify(ci, COOL_NIGHT_CLASSES),
            "Índice de sequía (mm)": di,
            "Clase sequía": classify(di, DRYNESS_CLASSES),
            "Precipitación campaña (mm)": full["PRECTOTCORR"].sum() if ok_full_p else np.nan,
            "Precipitación temporada (mm)": p_g,
            "ET0 temporada (mm)": et0_g,
            "Balance P − ET0 temporada (mm)": p_g - et0_g,
            "Última helada primaveral": last_spring,
            "Primera helada otoñal": first_autumn,
            "Periodo libre de heladas (días)": frost_free,
            "Heladas en brotación (días)": int((bb["T2M_MIN"] <= s.frost_temp).sum()) if ok_bb else np.nan,
            "Días de calor en temporada": int((g["T2M_MAX"] >= s.heat_temp).sum()) if ok_g else np.nan,
            "Lluvia en vendimia (mm)": hv["PRECTOTCORR"].sum() if ok_hv else np.nan,
            "Días de lluvia en vendimia (≥1 mm)": int((hv["PRECTOTCORR"] >= 1).sum()) if ok_hv else np.nan,
            "Amplitud térmica en vendimia (°C)": (hv["T2M_MAX"] - hv["T2M_MIN"]).mean() if ok_hv else np.nan,
            "Días favorables a mildiu (proxy)": int(((g["T2M_MIN"] >= 10) & (g["PRECTOTCORR"] >= 10)).sum()) if ok_g and ok_pg else np.nan,
            "Tmin absoluta campaña (°C)": full["T2M_MIN"].min() if ok_full_t else np.nan,
            "Tmax absoluta campaña (°C)": full["T2M_MAX"].max() if ok_full_t else np.nan,
        })
    return pd.DataFrame(rows)


NUMERIC_INDICES = [
    "GDD Winkler (°C·día)", "Índice de Huglin", "GST (°C)", "BEDD (°C·día)",
    "Índice de frescor nocturno (°C)", "Índice de sequía (mm)", "Precipitación campaña (mm)",
    "Precipitación temporada (mm)", "ET0 temporada (mm)", "Balance P − ET0 temporada (mm)",
    "Periodo libre de heladas (días)", "Heladas en brotación (días)", "Días de calor en temporada",
    "Lluvia en vendimia (mm)", "Días de lluvia en vendimia (≥1 mm)", "Amplitud térmica en vendimia (°C)",
    "Días favorables a mildiu (proxy)", "Tmin absoluta campaña (°C)", "Tmax absoluta campaña (°C)",
]


# ------------------------------------------------------------ tendencias
def trends(annual: pd.DataFrame, min_years: int = 8) -> pd.DataFrame:
    """Tendencia lineal (MCO), pendiente de Sen y test de Mann-Kendall por índice."""
    rows = []
    for col in NUMERIC_INDICES:
        sub = annual[["Campaña", col]].dropna()
        if len(sub) < min_years or sub[col].nunique() < 2:
            continue
        x, y = sub["Campaña"].to_numpy(float), sub[col].to_numpy(float)
        ols = stats.linregress(x, y)
        sen = stats.theilslopes(y, x)
        tau, p_mk = stats.kendalltau(x, y)
        rows.append({
            "Indicador": col,
            "Años": len(sub),
            "Media": y.mean(),
            "Desv. típica": y.std(ddof=1),
            "CV (%)": 100 * y.std(ddof=1) / abs(y.mean()) if y.mean() else np.nan,
            "Pendiente MCO / década": ols.slope * 10,
            "Pendiente de Sen / década": sen.slope * 10,
            "R²": ols.rvalue ** 2,
            "τ de Kendall": tau,
            "p (Mann-Kendall)": p_mk,
            "Significativa (p<0,05)": "Sí" if p_mk < 0.05 else "No",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------- mensual / normales
def monthly_table(daily: pd.DataFrame, min_coverage: float) -> pd.DataFrame:
    g = daily.resample("MS")
    counts = g["T2M"].count()
    days = pd.Series(daily.index.days_in_month, index=daily.index).resample("MS").first()
    monthly = pd.DataFrame({
        "T media (°C)": g["T2M"].mean(),
        "T máx media (°C)": g["T2M_MAX"].mean(),
        "T mín media (°C)": g["T2M_MIN"].mean(),
        "Precipitación (mm)": g["PRECTOTCORR"].sum(min_count=1),
        "ET0 (mm)": g["ET0"].sum(min_count=1),
        "GDD (°C·día)": g["GDD"].sum(min_count=1),
        "HR media (%)": g["RH2M"].mean() if "RH2M" in daily else np.nan,
        "Viento medio (m/s)": g["WS2M"].mean() if "WS2M" in daily else np.nan,
        "Radiación media (MJ/m²/día)": g["ALLSKY_SFC_SW_DWN"].mean() if "ALLSKY_SFC_SW_DWN" in daily else np.nan,
        "Días con Tmin ≤ 0 °C": g["T2M_MIN"].apply(lambda x: (x <= 0).sum()),
        "Cobertura (%)": 100 * counts / days,
    })
    monthly.loc[monthly["Cobertura (%)"] < 100 * min_coverage, monthly.columns.drop("Cobertura (%)")] = np.nan
    monthly.index.name = "Mes"
    return monthly


def normals(monthly: pd.DataFrame) -> pd.DataFrame:
    norm = monthly.drop(columns="Cobertura (%)").groupby(monthly.index.month).mean()
    norm.index.name = "Mes"
    return norm


def anomaly_matrix(monthly: pd.DataFrame, column: str, relative: bool = False) -> pd.DataFrame:
    m = monthly[[column]].reset_index(drop=True)
    m["Año"], m["Mes"] = monthly.index.year, monthly.index.month
    pivot = m.pivot_table(index="Año", columns="Mes", values=column)
    clim = pivot.mean()
    return (pivot / clim - 1) * 100 if relative else pivot - clim


def cumulative_gdd(daily: pd.DataFrame, lat: float) -> pd.DataFrame:
    """GDD acumulados día a día dentro de la temporada Winkler, por campaña."""
    hemisphere = "N" if lat >= 0 else "S"
    se = SEASONS[hemisphere]
    out = []
    for year in sorted(daily["Campaña"].unique()):
        dates = window_dates(int(year), se.winkler, hemisphere)
        part = daily.reindex(dates)
        if part["GDD"].notna().sum() == 0:
            continue
        ref_start = pd.Timestamp(2001 if hemisphere == "N" else 2000, se.winkler[0], 1)
        out.append(pd.DataFrame({
            "Campaña": int(year),
            "Día": np.arange(len(dates)),
            "Fecha ref": ref_start + pd.to_timedelta(np.arange(len(dates)), unit="D"),
            "Fecha": dates,
            "GDD acumulado": part["GDD"].cumsum().where(part["GDD"].notna()).to_numpy(),
            "Completa": part["GDD"].notna().mean() >= 0.95,
        }))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def frost_doy_summary(annual: pd.DataFrame) -> dict:
    ls = pd.to_datetime(annual["Última helada primaveral"]).dropna()
    fa = pd.to_datetime(annual["Primera helada otoñal"]).dropna()
    return {
        "Última helada primaveral (mediana)": _doy_label(ls.dt.day_of_year.median()) if len(ls) else "—",
        "Última helada primaveral (más tardía)": _doy_label(ls.dt.day_of_year.max()) if len(ls) else "—",
        "Primera helada otoñal (mediana)": _doy_label(fa.dt.day_of_year.median()) if len(fa) else "—",
        "Primera helada otoñal (más temprana)": _doy_label(fa.dt.day_of_year.min()) if len(fa) else "—",
    }
