# Analizador agroclimático vitícola · Viticultura del Norte

Aplicación Streamlit que descarga datos diarios de **NASA POWER** (desde 1981) para cualquier punto
del mundo y calcula los índices bioclimáticos que usa un especialista en viticultura.

## Funcionalidades

- **Mapa interactivo** (satélite, topográfico y callejero): clic para situar la finca, pegar coordenadas
  decimales o en grados/minutos/segundos, y recuadro con la celda de reanálisis que representa los datos.
- **Índices por campaña**: GDD Winkler (clases ampliadas de Jones 2010), Huglin, GST, BEDD, índice de
  frescor nocturno, índice de sequía de Riou, ET0 FAO-56 Penman-Monteith y balance P − ET0.
- **Ambos hemisferios**: en el hemisferio sur la campaña se nombra por el año de vendimia (oct–abr).
- **Campaña en curso**: GDD acumulados frente a la mediana y la banda P10–P90 histórica.
- **Clima mensual**: climograma, mapa de calor de anomalías y variabilidad interanual por mes.
- **Riesgos**: fechas de última/primera helada, heladas en brotación, días de calor, lluvia en vendimia y
  un proxy de presión de mildiu.
- **Tendencias**: pendiente MCO y de Sen por década con test de Mann-Kendall.
- **Comparación de fincas** guardadas en la sesión.
- **Exportación**: Excel con metadatos, metodología, índices, tendencias, normales, serie mensual y diaria; CSV.
- Umbrales configurables (temperatura base, helada, calor, meses de vendimia, cobertura mínima).

## Inicio local

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

Pruebas: `pip install pytest && pytest -q`

## Estructura

```
app.py                 interfaz Streamlit
agroclima/config.py    parámetros, paleta, temporadas por hemisferio y clases
agroclima/api.py       cliente NASA POWER
agroclima/indices.py   cálculo de índices, ET0, tendencias, normales
agroclima/charts.py    gráficas Plotly con la identidad visual
agroclima/export.py    informe Excel
tests/                 pruebas de índices y prueba de humo de la app
```

## Publicar en Streamlit Community Cloud

1. Sube el repositorio a GitHub.
2. En https://share.streamlit.io/ elige el repositorio, la rama `main` y el archivo `app.py`.

## Advertencias

- Los datos son de reanálisis en rejilla (MERRA-2 ≈ 50 km; radiación ≈ 1°): no sustituyen a una estación
  local. En relieve complejo, corregir la temperatura por la diferencia de altitud con la celda.
- La orientación varietal por GST es una agrupación amplia y orientativa.

## Identidad visual
Tema en `.streamlit/config.toml`; paleta de la marca en `BRAND` (`agroclima/config.py`). Los tonos son
provisionales hasta disponer del logotipo oficial.
