"""Constantes: parámetros NASA POWER, paleta de marca, temporadas y clases de índices."""
from dataclasses import dataclass

API_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FIRST_YEAR = 1981

PARAMETERS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "T2MDEW"]
REQUIRED = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]

LABELS = {
    "T2M": "Temperatura media (°C)",
    "T2M_MAX": "Temperatura máxima (°C)",
    "T2M_MIN": "Temperatura mínima (°C)",
    "PRECTOTCORR": "Precipitación (mm)",
    "RH2M": "Humedad relativa (%)",
    "WS2M": "Viento a 2 m (m/s)",
    "ALLSKY_SFC_SW_DWN": "Radiación solar (MJ/m²/día)",
    "T2MDEW": "Punto de rocío (°C)",
    "ET0": "ET0 FAO-56 (mm)",
    "GDD": "GDD diario (°C·día)",
}

# Identidad de Viticultura del Norte, tomada del logotipo (racimo índigo con hoja verde) y de su
# material gráfico (oliva/chartreuse, tipografía serif de capitales).
BRAND = {
    "indigo": "#211845",       # uva del logotipo: color principal
    "indigo_deep": "#150F2E",
    "indigo_soft": "#EEEBF5",
    "green": "#145F36",        # hoja del logotipo
    "olive": "#8F8A25",        # acento del material gráfico (texto/acento sobre claro)
    "olive_light": "#C9C27A",
    "ivory": "#FAF9F6",        # fondo
    "paper": "#FFFFFF",
    "ink": "#1D1A2B",
    "muted": "#6B6878",
    "line": "#E6E2EA",
    # Serie categórica para gráficas (validada para daltonismo, ΔE ≥ 16 entre pares)
    "s1": "#3B2F86",           # índigo
    "s2": "#1F7A4A",           # verde
    "s3": "#B3A532",           # oliva
    "s1_light": "#7A70C2",
}

MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


@dataclass(frozen=True)
class Seasons:
    """Ventanas fenológicas por hemisferio (meses). La campaña se nombra por el año de vendimia."""
    hemisphere: str
    label: str
    winkler: tuple      # temporada de crecimiento (Winkler, GST, BEDD)
    huglin: tuple       # Huglin e índice de sequía de Riou
    cool_night: int     # mes previo a vendimia (índice de frescor nocturno)
    budbreak: tuple     # brotación (riesgo de helada tardía)
    harvest: tuple      # vendimia por defecto
    spring: tuple       # meses en los que se busca la última helada
    autumn: tuple       # meses en los que se busca la primera helada


SEASONS = {
    "N": Seasons("N", "Hemisferio norte", (4, 5, 6, 7, 8, 9, 10), (4, 5, 6, 7, 8, 9), 9,
                 (4, 5), (8, 9), (1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12)),
    "S": Seasons("S", "Hemisferio sur", (10, 11, 12, 1, 2, 3, 4), (10, 11, 12, 1, 2, 3), 3,
                 (9, 10), (2, 3), (7, 8, 9, 10, 11, 12), (1, 2, 3, 4, 5, 6)),
}

# Clases: lista de (límite superior exclusivo, etiqueta); el último límite es None (infinito).
WINKLER_CLASSES = [
    (850, "Demasiado fría"), (1111, "Región Ia"), (1389, "Región Ib"), (1667, "Región II"),
    (1944, "Región III"), (2222, "Región IV"), (2700, "Región V"), (None, "Demasiado cálida"),
]
HUGLIN_CLASSES = [
    (1500, "Muy fresco (HI-3)"), (1800, "Fresco (HI-2)"), (2100, "Templado (HI-1)"),
    (2400, "Templado cálido (HI+1)"), (3000, "Cálido (HI+2)"), (None, "Muy cálido (HI+3)"),
]
GST_CLASSES = [
    (13, "Demasiado fresco"), (15, "Fresco"), (17, "Intermedio"), (19, "Cálido"),
    (21, "Caluroso"), (24, "Muy caluroso"), (None, "Demasiado caluroso"),
]
COOL_NIGHT_CLASSES = [
    (12, "Noches muy frescas (CI+2)"), (14, "Noches frescas (CI+1)"),
    (18, "Noches templadas (CI-1)"), (None, "Noches cálidas (CI-2)"),
]
DRYNESS_CLASSES = [
    (-100, "Muy seco (IS+2)"), (50, "Moderadamente seco (IS+1)"),
    (150, "Subhúmedo (IS-1)"), (None, "Húmedo (IS-2)"),
]

# Orientación varietal por GST (agrupación amplia a partir de Jones, 2006). Solo orientativo.
VARIETY_GUIDE = {
    "Demasiado fresco": "Fuera del rango habitual para vinificación; solo híbridos muy precoces.",
    "Fresco": "Pinot noir, Chardonnay, Riesling, Gewürztraminer, Sauvignon blanc, espumosos.",
    "Intermedio": "Merlot, Tempranillo, Cabernet franc, Syrah, Malbec, Viognier.",
    "Cálido": "Cabernet Sauvignon, Sangiovese, Garnacha, Cariñena, Zinfandel, Nebbiolo.",
    "Caluroso": "Garnacha, Cariñena, Zinfandel, variedades mediterráneas tardías, uva de mesa.",
    "Muy caluroso": "Uva de mesa y pasa; vinificación limitada a variedades muy tolerantes al calor.",
    "Demasiado caluroso": "Fuera del rango habitual para viticultura de calidad.",
}
