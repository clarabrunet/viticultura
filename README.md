# Analizador agroclimático - Viticultura del Norte

## Inicio local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicar en Streamlit Community Cloud

1. Crea un repositorio GitHub público.
2. Sube `app.py` y `requirements.txt` a la raíz.
3. Entra en https://share.streamlit.io/ y autoriza GitHub.
4. Elige el repositorio, la rama `main` y el archivo `app.py`.
5. Haz clic en Deploy y comparte el enlace de la aplicación.

## Indicadores

- NASA POWER Daily API, AG community.
- GDD diarios = max(temperatura media diaria - 10 °C, 0).
- Temporada Winkler: abril-octubre, hemisferio norte.
- Regiones Winkler orientativas por límites clásicos en °C·día.
- Los años con menos del 95% de datos diarios se consideran incompletos en los agregados GDD/precipitación.
- Las temperaturas extremas provienen de productos de cuadrícula, no de termómetros locales.

Nota: antes de usar las cifras para decisiones agronómicas de inversión, validar con registros meteorológicos locales.

## Identidad visual
El tema está definido en `.streamlit/config.toml` y la paleta de las gráficas/CSS en el diccionario `BRAND` dentro de `app.py`. Los tonos son provisionales hasta obtener el logotipo oficial de Viticultura del Norte.
