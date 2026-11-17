"""Identidad visual: hoja de estilos, logotipo y cabecera."""
import base64
from pathlib import Path

from .config import BRAND as B

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO_SVG = (ASSETS / "logo.svg").read_text(encoding="utf-8")
FAVICON = str(ASSETS / "favicon.png")

# Si se deja una foto en assets/hero.jpg (p. ej. un viñedo de la empresa) se usa de fondo de cabecera.
_HERO = next((p for p in (ASSETS / "hero.jpg", ASSETS / "hero.png", ASSETS / "hero.webp") if p.exists()), None)
HERO_BG = (
    f"linear-gradient(100deg, rgba(21,15,46,.94) 0%, rgba(33,24,69,.82) 48%, rgba(33,24,69,.35) 100%), "
    f"url('data:image/{_HERO.suffix[1:].replace('jpg', 'jpeg')};base64,{base64.b64encode(_HERO.read_bytes()).decode()}') center/cover"
    if _HERO else
    f"radial-gradient(circle at 88% 20%, rgba(31,122,74,.35) 0, transparent 34%), "
    f"radial-gradient(circle at 70% 120%, rgba(179,165,50,.22) 0, transparent 40%), "
    f"linear-gradient(110deg, {B['indigo_deep']} 0%, {B['indigo']} 60%, #2C2160 100%)"
)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600&family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {{ --indigo:{B['indigo']}; --green:{B['green']}; --olive:{B['olive']}; --ink:{B['ink']};
        --muted:{B['muted']}; --line:{B['line']}; --ivory:{B['ivory']}; }}
html, body, .stApp, [data-testid="stMarkdownContainer"], input, textarea, button, select {{
    font-family: 'Inter', system-ui, sans-serif; }}
.stApp {{ background: var(--ivory); color: var(--ink); }}
.block-container {{ max-width: 1280px; padding-top: 1.4rem; padding-bottom: 5rem; }}
h1, h2, h3, h4 {{ font-family: 'Cormorant Garamond', Georgia, serif !important; color: var(--indigo) !important;
    font-weight: 600 !important; letter-spacing: .005em; }}
h4 {{ font-size: 1.35rem !important; margin-top: .6rem !important; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: var(--muted) !important; }}
hr {{ border-color: var(--line) !important; }}

/* Barra lateral */
[data-testid="stSidebar"] {{ background: {B['paper']}; border-right: 1px solid var(--line); }}
[data-testid="stSidebar"] h3 {{ font-size: 1.3rem !important; }}
.side-brand {{ display:flex; align-items:center; gap:12px; padding: 4px 0 18px; margin-bottom: 14px;
    border-bottom: 1px solid var(--line); }}
.side-brand svg {{ width: 46px; height: 46px; filter: drop-shadow(0 1px 2px rgba(33,24,69,.15)); }}
.side-brand .n {{ font-family: 'Cinzel', serif; color: var(--indigo); font-weight: 600; font-size: .98rem;
    line-height: 1.15; letter-spacing: .04em; }}
.side-brand .t {{ font-size: .7rem; color: var(--olive); letter-spacing: .14em; text-transform: uppercase; margin-top: 3px; }}

/* Cabecera */
.hero {{ background: {HERO_BG}; border-radius: 4px; padding: 38px 44px; color: #fff; margin: 0 0 30px;
    display: flex; align-items: center; gap: 30px; position: relative; overflow: hidden;
    box-shadow: 0 18px 40px -24px rgba(21,15,46,.55); }}
.hero:before {{ content:""; position:absolute; left:44px; right:44px; bottom:0; height:3px;
    background: linear-gradient(90deg, {B['olive_light']}, {B['s3']} 40%, transparent); }}
.hero .logo {{ flex: 0 0 auto; width: 104px; height: 104px; border-radius: 50%;
    box-shadow: 0 0 0 6px rgba(255,255,255,.08), 0 10px 30px rgba(0,0,0,.35); }}
.hero .logo svg {{ width: 104px; height: 104px; display: block; }}
.hero .eyebrow {{ font-family: 'Cinzel', serif; color: {B['olive_light']}; letter-spacing: .28em; font-size: .74rem;
    font-weight: 600; text-transform: uppercase; }}
.hero h1 {{ color: #fff !important; font-size: 2.65rem; line-height: 1.05; margin: .35rem 0 .55rem; padding: 0; font-weight: 600 !important; }}
.hero p {{ color: rgba(255,255,255,.78); margin: 0; max-width: 720px; font-size: .95rem; line-height: 1.6; }}
.hero .badges {{ margin-top: 14px; display:flex; flex-wrap: wrap; gap: 8px; }}
.hero .badges span {{ border: 1px solid rgba(255,255,255,.22); border-radius: 2px; padding: 3px 10px;
    font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; color: rgba(255,255,255,.85); }}

/* Encabezados de sección */
.section {{ display:flex; align-items: baseline; gap: 14px; margin: 8px 0 14px; padding-bottom: 8px;
    border-bottom: 1px solid var(--line); }}
.section .num {{ font-family: 'Cinzel', serif; color: var(--olive); font-size: .85rem; letter-spacing: .12em; }}
.section .tt {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.85rem; color: var(--indigo); font-weight: 600; }}

/* Indicadores */
.kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; margin: 6px 0 26px;
    background: var(--line); border: 1px solid var(--line); border-radius: 4px; overflow: hidden; }}
.kpi {{ background: {B['paper']}; padding: 18px 20px 16px; }}
.kpi .l {{ font-family: 'Cinzel', serif; color: var(--muted); font-size: .72rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; }}
.kpi .v {{ font-family: 'Cormorant Garamond', Georgia, serif; font-size: 2.35rem; font-weight: 600; color: var(--indigo);
    margin-top: 4px; line-height: 1.05; font-variant-numeric: lining-nums; }}
.kpi .v small {{ font-family: 'Inter', sans-serif; font-size: .78rem; font-weight: 500; color: var(--muted); margin-left: 2px; }}
.kpi .b {{ display: inline-block; margin-top: 8px; padding: 2px 9px; border-radius: 2px; font-size: .72rem; font-weight: 600;
    background: {B['indigo_soft']}; color: var(--indigo); letter-spacing: .02em; }}
.kpi .s {{ color: var(--muted); font-size: .74rem; margin-top: 8px; line-height: 1.4; }}

.site-meta {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 2px 0 14px; }}
.chip {{ background: {B['paper']}; border: 1px solid var(--line); border-radius: 2px; padding: 3px 10px;
    font-size: .78rem; color: var(--ink); }}
.chip b {{ color: var(--olive); font-weight: 600; margin-right: 4px; font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; }}
.reading {{ background: {B['paper']}; border: 1px solid var(--line); border-left: 3px solid var(--green);
    padding: 18px 22px; margin: 6px 0 22px; line-height: 1.7; font-size: .96rem; }}
.reading b {{ color: var(--indigo); }}

[data-testid="stMetric"] {{ background: {B['paper']}; border: 1px solid var(--line); border-radius: 4px; padding: 14px 18px; }}
[data-testid="stMetricLabel"] p {{ color: var(--muted); font-size: .8rem; }}
[data-testid="stMetricValue"] {{ font-family: 'Cormorant Garamond', Georgia, serif; color: var(--indigo); }}

/* Pestañas */
.stTabs [data-baseweb="tab-list"] {{ gap: 0; border-bottom: 1px solid var(--line); flex-wrap: wrap; }}
.stTabs [data-baseweb="tab"] {{ background: transparent; padding: 10px 16px; border-radius: 0; }}
.stTabs [data-baseweb="tab"] p {{ font-size: .86rem; color: var(--muted); font-weight: 500; }}
.stTabs [aria-selected="true"] p {{ color: var(--indigo) !important; font-weight: 600; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--indigo) !important; height: 2px; }}

/* Botones */
div.stButton > button, div.stDownloadButton > button {{ border-radius: 3px; font-weight: 500; letter-spacing: .02em; }}
div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {{
    background: var(--indigo); border-color: var(--indigo); color: #fff; }}
div.stButton > button[kind="primary"]:hover, div.stDownloadButton > button[kind="primary"]:hover {{
    background: {B['indigo_deep']}; border-color: {B['indigo_deep']}; }}
div.stButton > button[kind="secondary"]:hover, div.stDownloadButton > button[kind="secondary"]:hover {{
    border-color: var(--indigo); color: var(--indigo); }}

/* Tablas y gráficas */
[data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {{ border: 1px solid var(--line); border-radius: 4px; background: #fff; }}
[data-testid="stPlotlyChart"] {{ overflow: hidden; }}
iframe[title="streamlit_folium.st_folium"] {{ border-radius: 4px; border: 1px solid var(--line); }}

.footer {{ margin-top: 48px; padding-top: 18px; border-top: 1px solid var(--line); display:flex; align-items:center;
    gap: 12px; color: var(--muted); font-size: .78rem; }}
.footer svg {{ width: 26px; height: 26px; }}

@media (max-width: 1000px) {{ .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
@media (max-width: 700px) {{
  .hero {{ padding: 24px 22px; flex-direction: column; align-items: flex-start; gap: 16px; }}
  .hero h1 {{ font-size: 1.9rem; }}
  .hero .logo, .hero .logo svg {{ width: 72px; height: 72px; }}
}}
</style>
"""


def hero_html() -> str:
    return f"""
<div class="hero">
  <div class="logo">{LOGO_SVG}</div>
  <div>
    <div class="eyebrow">Viticultura del Norte</div>
    <h1>Analizador agroclimático</h1>
    <p>Caracterización bioclimática de parcelas vitícolas a partir de datos diarios de la NASA desde 1981:
    índices de Winkler, Huglin y Jones, frescor nocturno, balance hídrico, riesgo de heladas y tendencias.</p>
    <div class="badges"><span>Plantas viníferas</span><span>Injertos</span><span>Portainjertos</span></div>
  </div>
</div>"""


def side_brand_html() -> str:
    return (f'<div class="side-brand">{LOGO_SVG}<div><div class="n">Viticultura<br>del Norte</div>'
            f'<div class="t">Agroclima</div></div></div>')


def section(num: str, title: str) -> str:
    return f'<div class="section"><span class="num">{num}</span><span class="tt">{title}</span></div>'


def footer_html() -> str:
    return (f'<div class="footer">{LOGO_SVG}<div>Viticultura del Norte · Vivero certificado IFV · COMTAT. '
            f'Datos: NASA POWER (MERRA-2, CERES). Herramienta orientativa: validar con registros locales.</div></div>')
