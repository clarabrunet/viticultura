"""Cliente de la API diaria de NASA POWER."""
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

from .config import API_URL, PARAMETERS

try:  # Usa el almacén de certificados del sistema (redes con inspección TLS).
    import truststore

    truststore.inject_into_ssl()
except Exception:  # pragma: no cover - opcional
    pass


def last_available_day() -> date:
    """NASA POWER publica con unos días de retraso."""
    return date.today() - timedelta(days=4)


def fetch_power(lat: float, lon: float, start: date, end: date) -> tuple[pd.DataFrame, dict]:
    """Descarga la serie diaria y devuelve (DataFrame, metadatos)."""
    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "longitude": round(lon, 4),
        "latitude": round(lat, 4),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    response = requests.get(API_URL, params=params, timeout=240)
    if response.status_code >= 400:
        detail = ""
        try:
            detail = "; ".join(map(str, response.json().get("messages", []))) or response.text[:300]
        except ValueError:
            detail = response.text[:300]
        raise ValueError(f"NASA POWER respondió {response.status_code}: {detail}")
    payload = response.json()
    series = payload.get("properties", {}).get("parameter", {})
    if not series:
        raise ValueError("NASA POWER no devolvió datos para esta consulta.")

    df = pd.DataFrame(series)
    df.index = pd.to_datetime(df.index, format="%Y%m%d", errors="coerce")
    df = df.loc[df.index.notna()].sort_index()
    df.index.name = "Fecha"
    df = df.apply(pd.to_numeric, errors="coerce")
    fill = payload.get("header", {}).get("fill_value", -999)
    df = df.mask(df.isin([fill, -999, -99]))
    # Recorta días finales sin datos (retraso de publicación).
    valid = df.dropna(how="all")
    if not valid.empty:
        df = df.loc[: valid.index.max()]

    coords = payload.get("geometry", {}).get("coordinates", [lon, lat, np.nan])
    meta = {
        "elevation": float(coords[2]) if len(coords) > 2 and coords[2] is not None else np.nan,
        "sources": ", ".join(payload.get("header", {}).get("sources", [])),
        "api_version": payload.get("header", {}).get("api", {}).get("version", ""),
        "units": {k: v.get("units", "") for k, v in payload.get("parameters", {}).items()},
    }
    return df, meta


def merra2_cell(lat: float, lon: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Límites de la celda MERRA-2 (0,5° × 0,625°) que contiene el punto."""
    clat = round(lat / 0.5) * 0.5
    clon = round(lon / 0.625) * 0.625
    return (clat - 0.25, clon - 0.3125), (clat + 0.25, clon + 0.3125)
