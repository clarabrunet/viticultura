"""Prueba de humo: la app arranca, analiza una finca real y renderiza sin excepciones."""
import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("lat,lon", [(42.58, -2.85), (-33.0, -68.85)])
def test_app_runs(lat, lon):
    at = AppTest.from_file("../app.py", default_timeout=300)
    at.run()
    assert not at.exception
    at.session_state["lat"], at.session_state["lon"] = lat, lon
    at.slider[0].set_value((2005, 2026))
    [b for b in at.button if b.label == "Analizar finca"][0].click().run()
    assert not at.exception, at.exception
    assert any("Resultados" in m.value for m in at.markdown)
    # Guardar para comparar
    [b for b in at.button if b.label.startswith("Guardar")][0].click().run()
    assert not at.exception, at.exception
