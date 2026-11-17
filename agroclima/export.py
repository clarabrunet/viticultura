"""Exportación a Excel con hoja de metadatos y metodología."""
import io

import pandas as pd
from openpyxl.styles import Font, PatternFill

from .config import BRAND, LABELS

METHODS = [
    ("Fuente", "NASA POWER Daily API v2 (comunidad AG). Meteorología MERRA-2 (~0,5° × 0,625°), radiación CERES/SYN1deg (~1°)."),
    ("Campaña", "Se nombra por el año de vendimia. Hemisferio sur: julio del año anterior a junio."),
    ("GDD Winkler", "Σ max(Tmedia − base, 0) en la temporada (N: 1 abr–31 oct; S: 1 oct–30 abr). Clases de Winkler ampliadas (Jones et al., 2010)."),
    ("Índice de Huglin", "Σ [(Tmedia − 10) + (Tmáx − 10)] / 2 × k (N: abr–sep; S: oct–mar); k según latitud (1,00–1,06)."),
    ("GST", "Temperatura media de la temporada de crecimiento (Jones, 2006)."),
    ("BEDD", "Grados-día biológicamente efectivos simplificados: Σ min(max(Tmedia − 10, 0), 9). Sin corrección de amplitud térmica ni latitud."),
    ("Índice de frescor nocturno", "Tmín media del mes previo a vendimia (N: septiembre; S: marzo). Tonietto y Carbonneau (2004)."),
    ("Índice de sequía", "Balance hídrico de Riou (W0 = 200 mm, coeficientes k = 0,1/0,3/0,5); ET0 FAO-56 Penman-Monteith."),
    ("ET0", "FAO-56 Penman-Monteith diaria con T, punto de rocío, viento a 2 m, radiación y altitud; respaldo Hargreaves-Samani."),
    ("Mildiu (proxy)", "Días en temporada con Tmín ≥ 10 °C y lluvia ≥ 10 mm (variante diaria de la regla 3-10). No es un modelo epidemiológico."),
    ("Cobertura", "Los agregados de una ventana se publican solo si hay al menos la cobertura mínima de días válidos."),
    ("Tendencias", "Pendiente MCO y de Sen por década; significación por Mann-Kendall (sin corrección de autocorrelación)."),
    ("Advertencia", "Datos de reanálisis en rejilla: no sustituyen a una estación local. Validar antes de decisiones de inversión."),
]


def _format(writer):
    head_fill = PatternFill("solid", fgColor=BRAND["wine"].lstrip("#"))
    for sheet in writer.book.worksheets:
        sheet.freeze_panes = "A2"
        if sheet.max_row > 1:
            sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = head_fill
        for cells in sheet.columns:
            width = max(len(str(c.value or "")) for c in cells[:200]) + 2
            sheet.column_dimensions[cells[0].column_letter].width = min(max(width, 12), 60)


def excel_report(site: dict, settings_rows: list, annual, trends, monthly, norms, daily) -> bytes:
    out = io.BytesIO()
    info = pd.DataFrame(
        [("Finca", site["name"]), ("Latitud", site["lat"]), ("Longitud", site["lon"]),
         ("Altitud de la celda (m)", site.get("elevation")), ("Periodo", site["period"]),
         ("Fuentes", site.get("sources")), ("Versión API", site.get("api_version"))]
        + settings_rows + METHODS,
        columns=["Campo", "Valor"])
    ann = annual.copy()
    for c in ["Última helada primaveral", "Primera helada otoñal"]:
        ann[c] = pd.to_datetime(ann[c]).dt.date
    daily_out = daily.drop(columns=["Mes"]).rename(columns=LABELS).reset_index()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        info.to_excel(writer, sheet_name="Información", index=False)
        ann.round(2).to_excel(writer, sheet_name="Índices por campaña", index=False)
        trends.round(4).to_excel(writer, sheet_name="Tendencias", index=False)
        norms.round(2).reset_index().to_excel(writer, sheet_name="Normales mensuales", index=False)
        monthly.round(2).reset_index().to_excel(writer, sheet_name="Serie mensual", index=False)
        daily_out.round(3).to_excel(writer, sheet_name="Datos diarios", index=False)
        _format(writer)
    return out.getvalue()
